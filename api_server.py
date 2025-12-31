import asyncio
import os
import json
import logging
from typing import Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import core components from the main server
import server
from marketdata.store import TickerSnapshot
from observability import log_event, build_log_context

# Initial context
API_CTX = build_log_context(tool="api_server")

app = FastAPI(title="ReadyTrader-Crypto Modern API")

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your frontend domain
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active WebSocket connections
active_connections: Set[WebSocket] = set()

def broadcast_tick(snap: TickerSnapshot):
    """
    Callback for marketdata_ws_store updates.
    """
    if not active_connections:
        return
        
    payload = {
        "type": "TICKER_UPDATE",
        "data": snap.to_dict()
    }
    
    # We need to run this in the event loop of the FastAPI app
    # Since this callback might be triggered from a background thread
    # We use a global loop reference or call_soon_threadsafe
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(broadcast_all(payload))

async def broadcast_all(payload: dict):
    if not active_connections:
        return
    message = json.dumps(payload)
    disconnected = set()
    for websocket in active_connections:
        try:
            await websocket.send_text(message)
        except Exception:
            disconnected.add(websocket)
            
    for ws in disconnected:
        active_connections.remove(ws)

# Subscribe to ticker updates from the WebSocket store
server.marketdata_ws_store.subscribe(broadcast_tick)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    log_event("api_client_connected", ctx=API_CTX, data={"active_connections": len(active_connections)})
    try:
        while True:
            # Keep connection open
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        log_event("api_client_disconnected", ctx=API_CTX, data={"active_connections": len(active_connections)})

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "mode": "paper" if server.PAPER_MODE else "live"}

@app.get("/api/pending-approvals")
async def get_pending_approvals():
    """
    Return list of trades awaiting manual approval.
    """
    return server.execution_store.list_pending()

class ApprovalRequest(BaseModel):
    request_id: str
    confirm_token: str
    approve: bool

@app.post("/api/approve-trade")
async def approve_trade(req: ApprovalRequest):
    """
    Approve or cancel a pending trade proposal.
    """
    try:
        if req.approve:
            # This logic mimics confirm_execution tool in server.py
            prop = server.execution_store.get(req.request_id)
            if not prop:
                raise HTTPException(status_code=404, detail="Proposal not found")
            
            # Since server.py's confirm_execution is a tool, we can either call the tool 
            # or replicate the logic. Replicating the core execution logic:
            result_json = server._tool_confirm_execution(req.request_id, req.confirm_token)
            result = json.loads(result_json)
            if not result.get("ok"):
                raise HTTPException(status_code=400, detail=result.get("error", {}).get("message", "Approval failed"))
            return result
        else:
            success = server.execution_store.cancel(req.request_id)
            return {"ok": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolio")
async def get_portfolio():
    """
    Get current portfolio state (paper or live).
    """
    if server.PAPER_MODE:
        balances = server.paper_engine.get_balances("agent_zero")
        pnl = server.paper_engine.get_risk_metrics("agent_zero")
        return {"balances": balances, "metrics": pnl}
    else:
        # For live mode, we'd need to query the wallet/CEX
        return {"error": "Live portfolio view not yet implemented in API"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "127.0.0.1")
    log_event("api_server_started", ctx=API_CTX, data={"port": port, "host": host})
    uvicorn.run(app, host=host, port=port)
