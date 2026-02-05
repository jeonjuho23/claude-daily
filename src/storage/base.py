"""
Abstract base interface for content repository
Allows swapping storage implementations (SQLite → PostgreSQL, etc.)
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List

from src.domain.models import (
    ContentRecord,
    Schedule,
    ExecutionLog,
    TopicRequest,
)
from src.domain.enums import (
    Category,
    ExecutionStatus,
    ScheduleStatus,
)


class ContentRepository(ABC):
    """Abstract base class for content storage"""
    
    # ========== Content Records ==========
    
    @abstractmethod
    async def save_content(self, content: ContentRecord) -> ContentRecord:
        """Save a content record and return it with ID"""
        pass
    
    @abstractmethod
    async def get_content(self, content_id: int) -> Optional[ContentRecord]:
        """Get a content record by ID"""
        pass
    
    @abstractmethod
    async def get_content_by_title(self, title: str) -> Optional[ContentRecord]:
        """Get a content record by title"""
        pass
    
    @abstractmethod
    async def list_contents(
        self,
        category: Optional[Category] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ContentRecord]:
        """List content records with optional filters"""
        pass
    
    @abstractmethod
    async def get_content_count(
        self,
        category: Optional[Category] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """Get count of content records"""
        pass
    
    @abstractmethod
    async def get_category_distribution(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """Get distribution of content by category"""
        pass
    
    @abstractmethod
    async def get_used_topics(self) -> List[str]:
        """Get list of all used topic titles"""
        pass
    
    @abstractmethod
    async def update_content(self, content: ContentRecord) -> ContentRecord:
        """Update a content record"""
        pass
    
    # ========== Schedules ==========
    
    @abstractmethod
    async def save_schedule(self, schedule: Schedule) -> Schedule:
        """Save a schedule"""
        pass
    
    @abstractmethod
    async def get_schedule(self, schedule_id: int) -> Optional[Schedule]:
        """Get a schedule by ID"""
        pass
    
    @abstractmethod
    async def get_schedule_by_time(self, time: str) -> Optional[Schedule]:
        """Get a schedule by time"""
        pass
    
    @abstractmethod
    async def list_schedules(
        self,
        status: Optional[ScheduleStatus] = None,
    ) -> List[Schedule]:
        """List schedules with optional status filter"""
        pass
    
    @abstractmethod
    async def update_schedule(self, schedule: Schedule) -> Schedule:
        """Update a schedule"""
        pass
    
    @abstractmethod
    async def delete_schedule(self, schedule_id: int) -> bool:
        """Delete a schedule"""
        pass
    
    # ========== Execution Logs ==========
    
    @abstractmethod
    async def save_execution_log(self, log: ExecutionLog) -> ExecutionLog:
        """Save an execution log"""
        pass
    
    @abstractmethod
    async def get_execution_log(self, log_id: int) -> Optional[ExecutionLog]:
        """Get an execution log by ID"""
        pass
    
    @abstractmethod
    async def list_execution_logs(
        self,
        status: Optional[ExecutionStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[ExecutionLog]:
        """List execution logs with optional filters"""
        pass
    
    @abstractmethod
    async def get_execution_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """Get execution statistics"""
        pass
    
    @abstractmethod
    async def update_execution_log(self, log: ExecutionLog) -> ExecutionLog:
        """Update an execution log"""
        pass
    
    # ========== Topic Requests ==========
    
    @abstractmethod
    async def save_topic_request(self, request: TopicRequest) -> TopicRequest:
        """Save a topic request"""
        pass
    
    @abstractmethod
    async def get_pending_requests(self) -> List[TopicRequest]:
        """Get all pending topic requests"""
        pass
    
    @abstractmethod
    async def mark_request_processed(
        self,
        request_id: int,
        content_id: int,
    ) -> TopicRequest:
        """Mark a topic request as processed"""
        pass
    
    # ========== Lifecycle ==========
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the repository (create tables, etc.)"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the repository connection"""
        pass
