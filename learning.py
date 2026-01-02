import sqlite3

import pandas as pd


class Learner:
    """
    Analyzes past trades to generate insights for the Agent.
    """

    def __init__(self, db_path: str = "paper.db"):
        self.db_path = db_path

    def analyze_performance(self, cur_symbol: str = None) -> str:
        """
        Review past trades and generate a summary of lessons.
        """
        conn = sqlite3.connect(self.db_path)

        # Fetch filled orders with rationale
        query = "SELECT symbol, side, amount, price, total_value, rationale, pnl_realized FROM orders WHERE status='filled'"
        if cur_symbol:
            query += f" AND symbol='{cur_symbol}'"

        try:
            df = pd.read_sql_query(query, conn)
            conn.close()

            if df.empty:
                return "No past trades to learn from yet."

            # Calculate basic stats
            # Note: pnl_realized needs to be populated when closing positions.
            # For now, we might not have it fully wired in paper_engine, so we rely on rationale review.

            # Simple Heuristic: Look for patterns in rationale of losing trades vs winning trades
            # For this MVP, we just summarize the last 5 trades to give context to the LLM.

            recent_trades = df.tail(5)
            summary = "Recent Trade History & Rationale:\n"

            for index, row in recent_trades.iterrows():
                pnl = row.get("pnl_realized")  # Might be None
                outcome = "Unknown"
                if pnl:
                    outcome = "PROFIT" if pnl > 0 else "LOSS"

                summary += f'- {row["side"]} {row["symbol"]} @ {row["price"]}: {outcome}. Rationale: "{row["rationale"]}"\n'

            return summary

        except Exception as e:
            return f"Error analyzing performance: {str(e)}"

    def save_lesson(self, lesson: str) -> str:
        """
        Save a trading lesson or insight to the database for future reference.

        Args:
            lesson: The lesson or insight to store

        Returns:
            Confirmation message
        """
        if not lesson or not lesson.strip():
            return "No lesson provided to save."

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Create lessons table if it doesn't exist
        c.execute("""CREATE TABLE IF NOT EXISTS lessons
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                      lesson TEXT NOT NULL)""")

        c.execute("INSERT INTO lessons (lesson) VALUES (?)", (lesson.strip(),))
        conn.commit()
        lesson_id = c.lastrowid
        conn.close()

        return f"Lesson #{lesson_id} saved successfully."

    def get_lessons(self, limit: int = 10) -> str:
        """
        Retrieve recent lessons from the database.

        Args:
            limit: Maximum number of lessons to retrieve

        Returns:
            Formatted string of recent lessons
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Check if lessons table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lessons'")
        if not c.fetchone():
            conn.close()
            return "No lessons saved yet."

        c.execute("SELECT id, timestamp, lesson FROM lessons ORDER BY id DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        conn.close()

        if not rows:
            return "No lessons saved yet."

        output = "Recent Trading Lessons:\n"
        for lesson_id, timestamp, lesson in rows:
            output += f"[{lesson_id}] {timestamp[:10]}: {lesson}\n"

        return output
