import os
import aiosqlite
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

class Database:
    def __init__(self, db_path: str = "data/cinema_bot.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    async def get_connection(self) -> aiosqlite.Connection:
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row
        return conn

    async def init_db(self):
        async with await self.get_connection() as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    status TEXT DEFAULT 'user',
                    subscription_until TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS payment_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    full_name TEXT,
                    amount INTEGER,
                    receipt_file_id TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    async def get_or_create_user(self, user_id: int, username: Optional[str], full_name: str) -> Dict[str, Any]:
        async with await self.get_connection() as db:
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                user = await cursor.fetchone()
                if user:
                    # Update username/full_name if changed
                    await db.execute(
                        "UPDATE users SET username = ?, full_name = ? WHERE user_id = ?",
                        (username, full_name, user_id)
                    )
                    await db.commit()
                    return dict(user)

            now = datetime.now(timezone.utc).isoformat()
            await db.execute(
                "INSERT INTO users (user_id, username, full_name, status, created_at) VALUES (?, ?, ?, 'user', ?)",
                (user_id, username, full_name, now)
            )
            await db.commit()
            return {
                "user_id": user_id,
                "username": username,
                "full_name": full_name,
                "status": "user",
                "subscription_until": None,
                "created_at": now
            }

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        async with await self.get_connection() as db:
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                user = await cursor.fetchone()
                return dict(user) if user else None

    async def is_user_subscribed(self, user_id: int) -> bool:
        user = await self.get_user(user_id)
        if not user:
            return False
        
        sub_until = user.get("subscription_until")
        if not sub_until:
            return False
        
        try:
            if isinstance(sub_until, str):
                until_dt = datetime.fromisoformat(sub_until)
            else:
                until_dt = sub_until
            
            # Make timezone-aware comparison
            if until_dt.tzinfo is None:
                until_dt = until_dt.replace(tzinfo=timezone.utc)
            
            return until_dt > datetime.now(timezone.utc)
        except Exception:
            return False

    async def create_payment_request(self, user_id: int, username: Optional[str], full_name: str, amount: int, receipt_file_id: str) -> int:
        now = datetime.now(timezone.utc).isoformat()
        async with await self.get_connection() as db:
            cursor = await db.execute(
                """INSERT INTO payment_requests (user_id, username, full_name, amount, receipt_file_id, status, created_at)
                   VALUES (?, ?, ?, ?, ?, 'pending', ?)""",
                (user_id, username, full_name, amount, receipt_file_id, now)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_payment_request(self, req_id: int) -> Optional[Dict[str, Any]]:
        async with await self.get_connection() as db:
            async with db.execute("SELECT * FROM payment_requests WHERE id = ?", (req_id,)) as cursor:
                req = await cursor.fetchone()
                return dict(req) if req else None

    async def approve_payment_request(self, req_id: int, days: int = 30) -> Optional[Dict[str, Any]]:
        async with await self.get_connection() as db:
            async with db.execute("SELECT * FROM payment_requests WHERE id = ?", (req_id,)) as cursor:
                req = await cursor.fetchone()
                if not req or req["status"] != "pending":
                    return None

            user_id = req["user_id"]
            
            # Calculate new expiration date
            async with db.execute("SELECT subscription_until FROM users WHERE user_id = ?", (user_id,)) as cursor:
                user_row = await cursor.fetchone()
            
            now_dt = datetime.now(timezone.utc)
            base_dt = now_dt
            
            if user_row and user_row["subscription_until"]:
                try:
                    curr_sub = datetime.fromisoformat(user_row["subscription_until"])
                    if curr_sub.tzinfo is None:
                        curr_sub = curr_sub.replace(tzinfo=timezone.utc)
                    if curr_sub > now_dt:
                        base_dt = curr_sub
                except Exception:
                    base_dt = now_dt

            new_sub_dt = base_dt + timedelta(days=days)
            new_sub_str = new_sub_dt.isoformat()

            await db.execute(
                "UPDATE payment_requests SET status = 'approved' WHERE id = ?", (req_id,)
            )
            await db.execute(
                "UPDATE users SET status = 'subscribed', subscription_until = ? WHERE user_id = ?",
                (new_sub_str, user_id)
            )
            await db.commit()
            return {
                "user_id": user_id,
                "new_subscription_until": new_sub_dt,
                "amount": req["amount"],
                "days": days
            }

    async def reject_payment_request(self, req_id: int) -> Optional[int]:
        async with await self.get_connection() as db:
            async with db.execute("SELECT * FROM payment_requests WHERE id = ?", (req_id,)) as cursor:
                req = await cursor.fetchone()
                if not req or req["status"] != "pending":
                    return None

            await db.execute("UPDATE payment_requests SET status = 'rejected' WHERE id = ?", (req_id,))
            await db.commit()
            return req["user_id"]

    async def get_stats(self) -> Dict[str, int]:
        async with await self.get_connection() as db:
            async with db.execute("SELECT COUNT(*) as cnt FROM users") as c:
                total_users = (await c.fetchone())["cnt"]
            
            now_str = datetime.now(timezone.utc).isoformat()
            async with db.execute("SELECT COUNT(*) as cnt FROM users WHERE subscription_until > ?", (now_str,)) as c:
                active_subs = (await c.fetchone())["cnt"]
                
            async with db.execute("SELECT COUNT(*) as cnt FROM payment_requests WHERE status = 'pending'") as c:
                pending_payments = (await c.fetchone())["cnt"]
                
            async with db.execute("SELECT SUM(amount) as total FROM payment_requests WHERE status = 'approved'") as c:
                row = await c.fetchone()
                revenue = row["total"] if row and row["total"] else 0

            return {
                "total_users": total_users,
                "active_subs": active_subs,
                "pending_payments": pending_payments,
                "total_revenue": revenue
            }

    async def grant_manual_subscription(self, user_id: int, days: int = 30) -> datetime:
        now_dt = datetime.now(timezone.utc)
        sub_dt = now_dt + timedelta(days=days)
        sub_str = sub_dt.isoformat()
        
        async with await self.get_connection() as db:
            await db.execute(
                """INSERT INTO users (user_id, status, subscription_until, created_at)
                   VALUES (?, 'subscribed', ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                   status = 'subscribed', subscription_until = ?""",
                (user_id, sub_str, now_dt.isoformat(), sub_str)
            )
            await db.commit()
        return sub_dt
