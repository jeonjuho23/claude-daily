"""
SQLite implementation of ContentRepository
Uses aiosqlite for async operations
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List

import aiosqlite

from src.storage.base import ContentRepository
from src.domain.models import (
    ContentRecord,
    Schedule,
    ExecutionLog,
    TopicRequest,
)
from src.domain.enums import (
    Category,
    Difficulty,
    ExecutionStatus,
    ScheduleStatus,
    ContentStatus,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SQLiteRepository(ContentRepository):
    """SQLite implementation of content repository"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._connection: Optional[aiosqlite.Connection] = None
        self._connection_lock = asyncio.Lock()

    async def _get_connection(self) -> aiosqlite.Connection:
        """Get or create database connection (thread-safe)"""
        if self._connection is not None:
            return self._connection

        async with self._connection_lock:
            if self._connection is None:  # Double-check
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
                self._connection = await aiosqlite.connect(str(self.db_path))
                self._connection.row_factory = aiosqlite.Row
            return self._connection
    
    async def initialize(self) -> None:
        """Initialize database schema"""
        conn = await self._get_connection()
        
        # Create tables
        await conn.executescript("""
            -- Content records table
            CREATE TABLE IF NOT EXISTS content_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                difficulty TEXT NOT NULL DEFAULT 'intermediate',
                summary TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                notion_page_id TEXT,
                notion_url TEXT,
                slack_ts TEXT,
                author TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            );
            
            -- Schedules table
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            );
            
            -- Execution logs table
            CREATE TABLE IF NOT EXISTS execution_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schedule_id INTEGER,
                content_id INTEGER,
                status TEXT NOT NULL DEFAULT 'pending',
                attempt_count INTEGER DEFAULT 0,
                error_message TEXT,
                started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                duration_ms INTEGER,
                FOREIGN KEY (schedule_id) REFERENCES schedules(id),
                FOREIGN KEY (content_id) REFERENCES content_records(id)
            );
            
            -- Topic requests table
            CREATE TABLE IF NOT EXISTS topic_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                requested_by TEXT NOT NULL,
                is_processed INTEGER DEFAULT 0,
                content_id INTEGER,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                FOREIGN KEY (content_id) REFERENCES content_records(id)
            );
            
            -- Indexes
            CREATE INDEX IF NOT EXISTS idx_content_created_at ON content_records(created_at);
            CREATE INDEX IF NOT EXISTS idx_content_category ON content_records(category);
            CREATE INDEX IF NOT EXISTS idx_execution_started_at ON execution_logs(started_at);
            CREATE INDEX IF NOT EXISTS idx_execution_status ON execution_logs(status);
        """)
        
        await conn.commit()
        logger.info("Database initialized", db_path=str(self.db_path))
    
    async def close(self) -> None:
        """Close database connection"""
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Database connection closed")
    
    # ========== Content Records ==========
    
    def _row_to_content(self, row: aiosqlite.Row) -> ContentRecord:
        """Convert database row to ContentRecord"""
        return ContentRecord(
            id=row["id"],
            title=row["title"],
            category=Category(row["category"]),
            difficulty=Difficulty(row["difficulty"]),
            summary=row["summary"],
            content=row["content"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            notion_page_id=row["notion_page_id"],
            notion_url=row["notion_url"],
            slack_ts=row["slack_ts"],
            author=row["author"],
            status=ContentStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
        )
    
    async def save_content(self, content: ContentRecord) -> ContentRecord:
        """Save a content record"""
        conn = await self._get_connection()
        
        cursor = await conn.execute(
            """
            INSERT INTO content_records 
            (title, category, difficulty, summary, content, tags, 
             notion_page_id, notion_url, slack_ts, author, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                content.title,
                content.category.value if isinstance(content.category, Category) else content.category,
                content.difficulty.value if isinstance(content.difficulty, Difficulty) else content.difficulty,
                content.summary,
                content.content,
                json.dumps(content.tags),
                content.notion_page_id,
                content.notion_url,
                content.slack_ts,
                content.author,
                content.status.value if isinstance(content.status, ContentStatus) else content.status,
                content.created_at.isoformat() if content.created_at else datetime.now().isoformat(),
            )
        )
        await conn.commit()
        
        content.id = cursor.lastrowid
        logger.info("Content saved", content_id=content.id, title=content.title)
        return content
    
    async def get_content(self, content_id: int) -> Optional[ContentRecord]:
        """Get content by ID"""
        conn = await self._get_connection()
        
        cursor = await conn.execute(
            "SELECT * FROM content_records WHERE id = ?",
            (content_id,)
        )
        row = await cursor.fetchone()
        
        return self._row_to_content(row) if row else None
    
    async def get_content_by_title(self, title: str) -> Optional[ContentRecord]:
        """Get content by title"""
        conn = await self._get_connection()
        
        cursor = await conn.execute(
            "SELECT * FROM content_records WHERE title = ?",
            (title,)
        )
        row = await cursor.fetchone()
        
        return self._row_to_content(row) if row else None
    
    async def list_contents(
        self,
        category: Optional[Category] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ContentRecord]:
        """List content records with filters"""
        conn = await self._get_connection()
        
        query = "SELECT * FROM content_records WHERE 1=1"
        params = []
        
        if category:
            query += " AND category = ?"
            params.append(category.value if isinstance(category, Category) else category)
        
        if start_date:
            query += " AND created_at >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND created_at <= ?"
            params.append(end_date.isoformat())
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
        
        return [self._row_to_content(row) for row in rows]
    
    async def get_content_count(
        self,
        category: Optional[Category] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """Get count of content records"""
        conn = await self._get_connection()
        
        query = "SELECT COUNT(*) as count FROM content_records WHERE 1=1"
        params = []
        
        if category:
            query += " AND category = ?"
            params.append(category.value if isinstance(category, Category) else category)
        
        if start_date:
            query += " AND created_at >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND created_at <= ?"
            params.append(end_date.isoformat())
        
        cursor = await conn.execute(query, params)
        row = await cursor.fetchone()
        
        return row["count"] if row else 0
    
    async def get_category_distribution(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """Get distribution of content by category"""
        conn = await self._get_connection()
        
        query = """
            SELECT category, COUNT(*) as count 
            FROM content_records 
            WHERE 1=1
        """
        params = []
        
        if start_date:
            query += " AND created_at >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND created_at <= ?"
            params.append(end_date.isoformat())
        
        query += " GROUP BY category"
        
        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
        
        return {row["category"]: row["count"] for row in rows}
    
    async def get_used_topics(self) -> List[str]:
        """Get list of all used topic titles"""
        conn = await self._get_connection()
        
        cursor = await conn.execute("SELECT title FROM content_records")
        rows = await cursor.fetchall()
        
        return [row["title"] for row in rows]
    
    async def update_content(self, content: ContentRecord) -> ContentRecord:
        """Update a content record"""
        conn = await self._get_connection()
        
        content.updated_at = datetime.now()
        
        await conn.execute(
            """
            UPDATE content_records SET
                title = ?,
                category = ?,
                difficulty = ?,
                summary = ?,
                content = ?,
                tags = ?,
                notion_page_id = ?,
                notion_url = ?,
                slack_ts = ?,
                status = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                content.title,
                content.category.value if isinstance(content.category, Category) else content.category,
                content.difficulty.value if isinstance(content.difficulty, Difficulty) else content.difficulty,
                content.summary,
                content.content,
                json.dumps(content.tags),
                content.notion_page_id,
                content.notion_url,
                content.slack_ts,
                content.status.value if isinstance(content.status, ContentStatus) else content.status,
                content.updated_at.isoformat(),
                content.id,
            )
        )
        await conn.commit()
        
        logger.info("Content updated", content_id=content.id)
        return content
    
    # ========== Schedules ==========
    
    def _row_to_schedule(self, row: aiosqlite.Row) -> Schedule:
        """Convert database row to Schedule"""
        return Schedule(
            id=row["id"],
            time=row["time"],
            status=ScheduleStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
        )
    
    async def save_schedule(self, schedule: Schedule) -> Schedule:
        """Save a schedule"""
        conn = await self._get_connection()
        
        cursor = await conn.execute(
            """
            INSERT INTO schedules (time, status, created_at)
            VALUES (?, ?, ?)
            """,
            (
                schedule.time,
                schedule.status.value if isinstance(schedule.status, ScheduleStatus) else schedule.status,
                schedule.created_at.isoformat() if schedule.created_at else datetime.now().isoformat(),
            )
        )
        await conn.commit()
        
        schedule.id = cursor.lastrowid
        logger.info("Schedule saved", schedule_id=schedule.id, time=schedule.time)
        return schedule
    
    async def get_schedule(self, schedule_id: int) -> Optional[Schedule]:
        """Get schedule by ID"""
        conn = await self._get_connection()
        
        cursor = await conn.execute(
            "SELECT * FROM schedules WHERE id = ?",
            (schedule_id,)
        )
        row = await cursor.fetchone()
        
        return self._row_to_schedule(row) if row else None
    
    async def get_schedule_by_time(self, time: str) -> Optional[Schedule]:
        """Get schedule by time"""
        conn = await self._get_connection()
        
        cursor = await conn.execute(
            "SELECT * FROM schedules WHERE time = ? AND status != 'deleted'",
            (time,)
        )
        row = await cursor.fetchone()
        
        return self._row_to_schedule(row) if row else None
    
    async def list_schedules(
        self,
        status: Optional[ScheduleStatus] = None,
    ) -> List[Schedule]:
        """List schedules with optional status filter"""
        conn = await self._get_connection()
        
        if status:
            cursor = await conn.execute(
                "SELECT * FROM schedules WHERE status = ? ORDER BY time",
                (status.value if isinstance(status, ScheduleStatus) else status,)
            )
        else:
            cursor = await conn.execute(
                "SELECT * FROM schedules WHERE status != 'deleted' ORDER BY time"
            )
        
        rows = await cursor.fetchall()
        return [self._row_to_schedule(row) for row in rows]
    
    async def update_schedule(self, schedule: Schedule) -> Schedule:
        """Update a schedule"""
        conn = await self._get_connection()
        
        schedule.updated_at = datetime.now()
        
        await conn.execute(
            """
            UPDATE schedules SET
                time = ?,
                status = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                schedule.time,
                schedule.status.value if isinstance(schedule.status, ScheduleStatus) else schedule.status,
                schedule.updated_at.isoformat(),
                schedule.id,
            )
        )
        await conn.commit()
        
        logger.info("Schedule updated", schedule_id=schedule.id)
        return schedule
    
    async def delete_schedule(self, schedule_id: int) -> bool:
        """Delete a schedule (soft delete)"""
        conn = await self._get_connection()
        
        await conn.execute(
            "UPDATE schedules SET status = 'deleted', updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(), schedule_id)
        )
        await conn.commit()
        
        logger.info("Schedule deleted", schedule_id=schedule_id)
        return True
    
    # ========== Execution Logs ==========
    
    def _row_to_execution_log(self, row: aiosqlite.Row) -> ExecutionLog:
        """Convert database row to ExecutionLog"""
        return ExecutionLog(
            id=row["id"],
            schedule_id=row["schedule_id"],
            content_id=row["content_id"],
            status=ExecutionStatus(row["status"]),
            attempt_count=row["attempt_count"],
            error_message=row["error_message"],
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            duration_ms=row["duration_ms"] if "duration_ms" in row.keys() else None,
        )
    
    async def save_execution_log(self, log: ExecutionLog) -> ExecutionLog:
        """Save an execution log"""
        conn = await self._get_connection()

        cursor = await conn.execute(
            """
            INSERT INTO execution_logs
            (schedule_id, content_id, status, attempt_count, error_message, started_at, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log.schedule_id,
                log.content_id,
                log.status.value if isinstance(log.status, ExecutionStatus) else log.status,
                log.attempt_count,
                log.error_message,
                log.started_at.isoformat() if log.started_at else datetime.now().isoformat(),
                log.duration_ms,
            )
        )
        await conn.commit()

        log.id = cursor.lastrowid
        return log
    
    async def get_execution_log(self, log_id: int) -> Optional[ExecutionLog]:
        """Get execution log by ID"""
        conn = await self._get_connection()
        
        cursor = await conn.execute(
            "SELECT * FROM execution_logs WHERE id = ?",
            (log_id,)
        )
        row = await cursor.fetchone()
        
        return self._row_to_execution_log(row) if row else None
    
    async def list_execution_logs(
        self,
        status: Optional[ExecutionStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[ExecutionLog]:
        """List execution logs with optional filters"""
        conn = await self._get_connection()
        
        query = "SELECT * FROM execution_logs WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status.value if isinstance(status, ExecutionStatus) else status)
        
        if start_date:
            query += " AND started_at >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND started_at <= ?"
            params.append(end_date.isoformat())
        
        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)
        
        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
        
        return [self._row_to_execution_log(row) for row in rows]
    
    async def get_execution_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """Get execution statistics"""
        conn = await self._get_connection()

        query = """
            SELECT
                status,
                COUNT(*) as count,
                SUM(attempt_count) as total_attempts,
                AVG(duration_ms) as avg_duration_ms,
                MIN(duration_ms) as min_duration_ms,
                MAX(duration_ms) as max_duration_ms
            FROM execution_logs
            WHERE 1=1
        """
        params = []

        if start_date:
            query += " AND started_at >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND started_at <= ?"
            params.append(end_date.isoformat())

        query += " GROUP BY status"

        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()

        return {
            row["status"]: {
                "count": row["count"],
                "total_attempts": row["total_attempts"] or 0,
                "avg_duration_ms": row["avg_duration_ms"],
                "min_duration_ms": row["min_duration_ms"],
                "max_duration_ms": row["max_duration_ms"],
            }
            for row in rows
        }
    
    async def update_execution_log(self, log: ExecutionLog) -> ExecutionLog:
        """Update an execution log"""
        conn = await self._get_connection()

        await conn.execute(
            """
            UPDATE execution_logs SET
                content_id = ?,
                status = ?,
                attempt_count = ?,
                error_message = ?,
                completed_at = ?,
                duration_ms = ?
            WHERE id = ?
            """,
            (
                log.content_id,
                log.status.value if isinstance(log.status, ExecutionStatus) else log.status,
                log.attempt_count,
                log.error_message,
                log.completed_at.isoformat() if log.completed_at else None,
                log.duration_ms,
                log.id,
            )
        )
        await conn.commit()

        return log
    
    # ========== Topic Requests ==========
    
    def _row_to_topic_request(self, row: aiosqlite.Row) -> TopicRequest:
        """Convert database row to TopicRequest"""
        return TopicRequest(
            id=row["id"],
            topic=row["topic"],
            requested_by=row["requested_by"],
            is_processed=bool(row["is_processed"]),
            content_id=row["content_id"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            processed_at=datetime.fromisoformat(row["processed_at"]) if row["processed_at"] else None,
        )
    
    async def save_topic_request(self, request: TopicRequest) -> TopicRequest:
        """Save a topic request"""
        conn = await self._get_connection()
        
        cursor = await conn.execute(
            """
            INSERT INTO topic_requests (topic, requested_by, is_processed, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                request.topic,
                request.requested_by,
                int(request.is_processed),
                request.created_at.isoformat() if request.created_at else datetime.now().isoformat(),
            )
        )
        await conn.commit()
        
        request.id = cursor.lastrowid
        logger.info("Topic request saved", request_id=request.id, topic=request.topic)
        return request
    
    async def get_pending_requests(self) -> List[TopicRequest]:
        """Get all pending topic requests"""
        conn = await self._get_connection()
        
        cursor = await conn.execute(
            "SELECT * FROM topic_requests WHERE is_processed = 0 ORDER BY created_at"
        )
        rows = await cursor.fetchall()
        
        return [self._row_to_topic_request(row) for row in rows]
    
    async def mark_request_processed(
        self,
        request_id: int,
        content_id: int,
    ) -> TopicRequest:
        """Mark a topic request as processed"""
        conn = await self._get_connection()
        
        await conn.execute(
            """
            UPDATE topic_requests SET
                is_processed = 1,
                content_id = ?,
                processed_at = ?
            WHERE id = ?
            """,
            (content_id, datetime.now().isoformat(), request_id)
        )
        await conn.commit()
        
        return await self._get_topic_request(request_id)
    
    async def _get_topic_request(self, request_id: int) -> Optional[TopicRequest]:
        """Get topic request by ID"""
        conn = await self._get_connection()
        
        cursor = await conn.execute(
            "SELECT * FROM topic_requests WHERE id = ?",
            (request_id,)
        )
        row = await cursor.fetchone()
        
        return self._row_to_topic_request(row) if row else None
