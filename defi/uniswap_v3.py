from typing import Dict, Any, Optional
from web3 import Web3
import json
import time

# Minimal ABIs for Uniswap V3 Support
UNI_V3_MANAGER_ABI = json.loads('''[
    {"inputs":[{"components":[{"internalType":"address","name":"token0","type":"address"},{"internalType":"address","name":"token1","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"},{"internalType":"int24","name":"tickLower","type":"int24"},{"internalType":"int24","name":"tickUpper","type":"int24"},{"internalType":"uint256","name":"amount0Desired","type":"uint256"},{"internalType":"uint256","name":"amount1Desired","type":"uint256"},{"internalType":"uint256","name":"amount0Min","type":"uint256"},{"internalType":"uint256","name":"amount1Min","type":"uint256"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"internalType":"struct INonfungiblePositionManager.MintParams","name":"params","type":"tuple"}],"name":"mint","outputs":[{"internalType":"uint256","name":"tokenId","type":"uint256"},{"internalType":"uint128","name":"liquidity","type":"uint128"},{"internalType":"uint256","name":"amount0","type":"uint256"},{"internalType":"uint256","name":"amount1","type":"uint256"}],"stateMutability":"payable","type":"function"},
    {"inputs":[{"components":[{"internalType":"uint256","name":"tokenId","type":"uint256"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint128","name":"amount0Max","type":"uint128"},{"internalType":"uint128","name":"amount1Max","type":"uint128"}],"internalType":"struct INonfungiblePositionManager.CollectParams","name":"params","type":"tuple"}],"name":"collect","outputs":[{"internalType":"uint256","name":"amount0","type":"uint256"},{"internalType":"uint256","name":"amount1","type":"uint256"}],"stateMutability":"payable","type":"function"}
]''')

# Mapping of Chain ID -> Uniswap V3 NonfungiblePositionManager
UNI_V3_MANAGERS = {
    1: Web3.to_checksum_address("0xC36442b4a4522E871399CD717aBDD847Ab11FE88"),
    8453: Web3.to_checksum_address("0x03a520b32C04BF3b764D891E199c905212ad23aD"),
    11155111: Web3.to_checksum_address("0x1238536071E1c67f106BA4c023F01D927E238E1e"), # Sepolia example
    84532: Web3.to_checksum_address("0x27F971cbC3C623e7456499682266D77990150825") # Base Sepolia example
}

class UniswapV3Client:
    def __init__(self, w3: Web3, chain_id: int):
        self.w3 = w3
        self.chain_id = chain_id
        self.manager_address = UNI_V3_MANAGERS.get(chain_id)
        if not self.manager_address:
            raise ValueError(f"Uniswap V3 Manager address not found for chain ID {chain_id}")
        self.manager = self.w3.eth.contract(address=self.manager_address, abi=UNI_V3_MANAGER_ABI)

    def build_mint_tx(self, params: Dict[str, Any], from_address: str) -> Dict[str, Any]:
        # deadline defaults to 20 mins
        deadline = params.get("deadline", int(time.time()) + 1200)
        
        mint_params = (
            Web3.to_checksum_address(params["token0"]),
            Web3.to_checksum_address(params["token1"]),
            int(params["fee"]),
            int(params["tickLower"]),
            int(params["tickUpper"]),
            int(params["amount0Desired"]),
            int(params["amount1Desired"]),
            int(params["amount0Min"]),
            int(params["amount1Min"]),
            Web3.to_checksum_address(params.get("recipient", from_address)),
            deadline
        )
        
        return self.manager.functions.mint(mint_params).build_transaction({
            "from": Web3.to_checksum_address(from_address),
            "gas": 500000 # Stub gas limit
        })

    def build_collect_tx(self, token_id: int, recipient: str, from_address: str) -> Dict[str, Any]:
        collect_params = (
            int(token_id),
            Web3.to_checksum_address(recipient),
            2**127, # amount0Max (type uint128; using large value to collect all)
            2**127  # amount1Max
        )
        return self.manager.functions.collect(collect_params).build_transaction({
            "from": Web3.to_checksum_address(from_address),
            "gas": 300000
        })
