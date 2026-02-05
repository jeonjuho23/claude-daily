"""
Domain Enumerations for Daily-Bot
"""

from enum import Enum, auto


class Category(str, Enum):
    """CS Content Categories"""
    NETWORK = "network"
    OS = "os"
    ALGORITHM = "algorithm"
    DATA_STRUCTURE = "data_structure"
    DATABASE = "database"
    OOP = "oop"
    DDD = "ddd"
    TDD = "tdd"
    DESIGN_PATTERN = "design_pattern"
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    DEVOPS = "devops"


class Difficulty(str, Enum):
    """Content Difficulty Levels"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    
    @property
    def korean(self) -> str:
        """Get Korean display name"""
        mapping = {
            "beginner": "초급",
            "intermediate": "중급",
            "advanced": "고급",
        }
        return mapping[self.value]


class ExecutionStatus(str, Enum):
    """Execution Status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"
    CANCELLED = "cancelled"


class ScheduleStatus(str, Enum):
    """Schedule Status"""
    ACTIVE = "active"
    PAUSED = "paused"
    DELETED = "deleted"


class ReportType(str, Enum):
    """Report Types"""
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ContentStatus(str, Enum):
    """Content Status in Notion"""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class SlackCommandType(str, Enum):
    """Slack Command Types"""
    TIME = "time"
    ADD = "add"
    REMOVE = "remove"
    PAUSE = "pause"
    RESUME = "resume"
    NOW = "now"
    REQUEST = "request"
    STATUS = "status"
    HELP = "help"
    LIST = "list"
