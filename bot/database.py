import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "data/cinema_bot.db", database_url: str = ""):
        self.database_url = database_url or os.getenv("DATABASE_URL", "")
        self.is_postgres = bool(self.database_url and ("postgres://" in self.database_url or "postgresql://" in self.database_url))
        self.pg_pool = None
        
        # Ensure SQLite path is absolute and directory exists
        self.db_path = os.path.abspath(db_path)
        dir_name = os.path.dirname(self.db_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        
        if self.is_postgres:
            # Fix postgres:// URL format for asyncpg if needed
            if self.database_url.startswith("postgres://"):
                self.database_url = self.database_url.replace("postgres://", "postgresql://", 1)

    async def init_db(self):
        if self.is_postgres:
            try:
                import asyncpg
                self.pg_pool = await asyncpg.create_pool(self.database_url)
                logger.info("Connected to Cloud PostgreSQL database pool.")
                async with self.pg_pool.acquire() as conn:
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS users (
                            user_id BIGINT PRIMARY KEY,
                            username TEXT,
                            full_name TEXT,
                            status TEXT DEFAULT 'user',
                            subscription_until TIMESTAMPTZ,
                            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                        );
                        CREATE TABLE IF NOT EXISTS payment_requests (
                            id SERIAL PRIMARY KEY,
                            user_id BIGINT,
                            username TEXT,
                            full_name TEXT,
                            amount BIGINT,
                            receipt_file_id TEXT,
                            status TEXT DEFAULT 'pending',
                            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                return
            except Exception as e:
                logger.error(f"PostgreSQL connection failed ({e}). Falling back to local SQLite database.")
                self.is_postgres = False

        # SQLite fallback
        dir_name = os.path.dirname(self.db_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
            
        async with self.get_sqlite_conn() as db:
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
            logger.info("SQLite database initialized at: %s", self.db_path)

    @asynccontextmanager
    async def get_sqlite_conn(self):
        import aiosqlite
        dir_name = os.path.dirname(self.db_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            yield conn

    async def get_or_create_user(self, user_id: int, username: Optional[str], full_name: str) -> Dict[str, Any]:
        now_dt = datetime.now(timezone.utc)
        if self.is_postgres and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
                if row:
                    await conn.execute(
                        "UPDATE users SET username = $1, full_name = $2 WHERE user_id = $3",
                        username, full_name, user_id
                    )
                    return dict(row)
                
                await conn.execute(
                    "INSERT INTO users (user_id, username, full_name, status, created_at) VALUES ($1, $2, $3, 'user', $4)",
                    user_id, username, full_name, now_dt
                )
                return {
                    "user_id": user_id,
                    "username": username,
                    "full_name": full_name,
                    "status": "user",
                    "subscription_until": None,
                    "created_at": now_dt.isoformat()
                }

        async with self.get_sqlite_conn() as db:
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                user = await cursor.fetchone()
                if user:
                    await db.execute(
                        "UPDATE users SET username = ?, full_name = ? WHERE user_id = ?",
                        (username, full_name, user_id)
                    )
                    await db.commit()
                    return dict(user)

            now_str = now_dt.isoformat()
            await db.execute(
                "INSERT INTO users (user_id, username, full_name, status, created_at) VALUES (?, ?, ?, 'user', ?)",
                (user_id, username, full_name, now_str)
            )
            await db.commit()
            return {
                "user_id": user_id,
                "username": username,
                "full_name": full_name,
                "status": "user",
                "subscription_until": None,
                "created_at": now_str
            }

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        if self.is_postgres and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
                return dict(row) if row else None

        async with self.get_sqlite_conn() as db:
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
            
            if until_dt.tzinfo is None:
                until_dt = until_dt.replace(tzinfo=timezone.utc)
            
            return until_dt > datetime.now(timezone.utc)
        except Exception:
            return False

    async def create_payment_request(self, user_id: int, username: Optional[str], full_name: str, amount: int, receipt_file_id: str) -> int:
        now_dt = datetime.now(timezone.utc)
        if self.is_postgres and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                req_id = await conn.fetchval(
                    """INSERT INTO payment_requests (user_id, username, full_name, amount, receipt_file_id, status, created_at)
                       VALUES ($1, $2, $3, $4, $5, 'pending', $6) RETURNING id""",
                    user_id, username, full_name, amount, receipt_file_id, now_dt
                )
                return req_id

        async with self.get_sqlite_conn() as db:
            cursor = await db.execute(
                """INSERT INTO payment_requests (user_id, username, full_name, amount, receipt_file_id, status, created_at)
                   VALUES (?, ?, ?, ?, ?, 'pending', ?)""",
                (user_id, username, full_name, amount, receipt_file_id, now_dt.isoformat())
            )
            await db.commit()
            return cursor.lastrowid

    async def get_payment_request(self, req_id: int) -> Optional[Dict[str, Any]]:
        if self.is_postgres and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM payment_requests WHERE id = $1", req_id)
                return dict(row) if row else None

        async with self.get_sqlite_conn() as db:
            async with db.execute("SELECT * FROM payment_requests WHERE id = ?", (req_id,)) as cursor:
                req = await cursor.fetchone()
                return dict(req) if req else None

    async def approve_payment_request(self, req_id: int, days: int = 30) -> Optional[Dict[str, Any]]:
        req = await self.get_payment_request(req_id)
        if not req or req["status"] != "pending":
            return None

        user_id = req["user_id"]
        user = await self.get_user(user_id)
        
        now_dt = datetime.now(timezone.utc)
        base_dt = now_dt
        
        if user and user.get("subscription_until"):
            try:
                sub_val = user["subscription_until"]
                curr_sub = datetime.fromisoformat(sub_val) if isinstance(sub_val, str) else sub_val
                if curr_sub.tzinfo is None:
                    curr_sub = curr_sub.replace(tzinfo=timezone.utc)
                if curr_sub > now_dt:
                    base_dt = curr_sub
            except Exception:
                base_dt = now_dt

        new_sub_dt = base_dt + timedelta(days=days)

        if self.is_postgres and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                await conn.execute("UPDATE payment_requests SET status = 'approved' WHERE id = $1", req_id)
                await conn.execute(
                    "UPDATE users SET status = 'subscribed', subscription_until = $1 WHERE user_id = $2",
                    new_sub_dt, user_id
                )
        else:
            async with self.get_sqlite_conn() as db:
                await db.execute("UPDATE payment_requests SET status = 'approved' WHERE id = ?", (req_id,))
                await db.execute(
                    "UPDATE users SET status = 'subscribed', subscription_until = ? WHERE user_id = ?",
                    (new_sub_dt.isoformat(), user_id)
                )
                await db.commit()

        return {
            "user_id": user_id,
            "new_subscription_until": new_sub_dt,
            "amount": req["amount"],
            "days": days
        }

    async def reject_payment_request(self, req_id: int) -> Optional[int]:
        req = await self.get_payment_request(req_id)
        if not req or req["status"] != "pending":
            return None

        if self.is_postgres and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                await conn.execute("UPDATE payment_requests SET status = 'rejected' WHERE id = $1", req_id)
        else:
            async with self.get_sqlite_conn() as db:
                await db.execute("UPDATE payment_requests SET status = 'rejected' WHERE id = ?", (req_id,))
                await db.commit()

        return req["user_id"]

    async def get_stats(self) -> Dict[str, Any]:
        now_dt = datetime.now(timezone.utc)
        if self.is_postgres and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                total_users = await conn.fetchval("SELECT COUNT(*) FROM users") or 0
                active_subs = await conn.fetchval("SELECT COUNT(*) FROM users WHERE subscription_until > $1", now_dt) or 0
                pending_payments = await conn.fetchval("SELECT COUNT(*) FROM payment_requests WHERE status = 'pending'") or 0
                revenue = await conn.fetchval("SELECT SUM(amount) FROM payment_requests WHERE status = 'approved'") or 0
                return {
                    "total_users": int(total_users),
                    "active_subs": int(active_subs),
                    "pending_payments": int(pending_payments),
                    "total_revenue": int(revenue)
                }

        async with self.get_sqlite_conn() as db:
            async with db.execute("SELECT COUNT(*) as cnt FROM users") as c:
                total_users = (await c.fetchone())["cnt"]
            
            async with db.execute("SELECT COUNT(*) as cnt FROM users WHERE subscription_until > ?", (now_dt.isoformat(),)) as c:
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
        
        if self.is_postgres and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO users (user_id, status, subscription_until, created_at)
                       VALUES ($1, 'subscribed', $2, $3)
                       ON CONFLICT(user_id) DO UPDATE SET
                       status = 'subscribed', subscription_until = $2""",
                    user_id, sub_dt, now_dt
                )
            return sub_dt

        sub_str = sub_dt.isoformat()
        async with self.get_sqlite_conn() as db:
            await db.execute(
                """INSERT INTO users (user_id, status, subscription_until, created_at)
                   VALUES (?, 'subscribed', ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                   status = 'subscribed', subscription_until = ?""",
                (user_id, sub_str, now_dt.isoformat(), sub_str)
            )
            await db.commit()
        return sub_dt

    async def get_all_users(self) -> List[Dict[str, Any]]:
        if self.is_postgres and self.pg_pool:
            async with self.pg_pool.acquire() as conn:
                rows = await conn.fetch("SELECT user_id, username, full_name, status, subscription_until FROM users")
                return [dict(r) for r in rows]

        async with self.get_sqlite_conn() as db:
            async with db.execute("SELECT user_id, username, full_name, status, subscription_until FROM users") as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]
