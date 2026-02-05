"""
Report generator for Daily-Bot
Generates weekly and monthly reports
"""

from datetime import datetime
from typing import Optional, List

from src.domain.models import ReportData
from src.domain.enums import ReportType, ExecutionStatus, Category
from src.storage.base import ContentRepository
from src.integrations.slack import SlackAdapter
from src.integrations.notion import NotionAdapter
from src.utils.logger import get_logger
from src.utils.datetime_utils import (
    get_last_week_range,
    get_last_month_range,
    now,
)
from config.topics import CATEGORIES

logger = get_logger(__name__)


class ReportGenerator:
    """
    Generates periodic reports for Daily-Bot
    
    Reports include:
    - Total content count
    - Success/failure rates
    - Category distribution
    - Uncovered categories
    """
    
    def __init__(
        self,
        repository: ContentRepository,
        slack_adapter: SlackAdapter,
        notion_adapter: NotionAdapter,
    ):
        """
        Initialize report generator
        
        Args:
            repository: Content repository
            slack_adapter: Slack adapter for notifications
            notion_adapter: Notion adapter for detailed reports
        """
        self.repository = repository
        self.slack = slack_adapter
        self.notion = notion_adapter
    
    async def generate_weekly_report(self) -> ReportData:
        """
        Generate weekly report
        
        Returns:
            Generated report data
        """
        period_start, period_end = get_last_week_range()
        
        logger.info(
            "Generating weekly report",
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
        )
        
        report = await self._generate_report(
            report_type=ReportType.WEEKLY,
            period_start=period_start,
            period_end=period_end,
        )
        
        # Create Notion page
        try:
            page_id, page_url = await self.notion.create_report_page(report)
            
            # Send Slack notification
            await self.slack.send_report_notification(report, notion_url=page_url)
            
            logger.info("Weekly report generated", page_id=page_id)
            
        except Exception as e:
            logger.error("Failed to create weekly report", error=str(e))
            # Still send Slack notification without Notion link
            await self.slack.send_report_notification(report)
        
        return report
    
    async def generate_monthly_report(self) -> ReportData:
        """
        Generate monthly report
        
        Returns:
            Generated report data
        """
        period_start, period_end = get_last_month_range()
        
        logger.info(
            "Generating monthly report",
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
        )
        
        report = await self._generate_report(
            report_type=ReportType.MONTHLY,
            period_start=period_start,
            period_end=period_end,
        )
        
        # Create Notion page
        try:
            page_id, page_url = await self.notion.create_report_page(report)
            
            # Send Slack notification
            await self.slack.send_report_notification(report, notion_url=page_url)
            
            logger.info("Monthly report generated", page_id=page_id)
            
        except Exception as e:
            logger.error("Failed to create monthly report", error=str(e))
            # Still send Slack notification without Notion link
            await self.slack.send_report_notification(report)
        
        return report
    
    async def _generate_report(
        self,
        report_type: ReportType,
        period_start: datetime,
        period_end: datetime,
    ) -> ReportData:
        """
        Generate report data
        
        Args:
            report_type: Type of report
            period_start: Period start datetime
            period_end: Period end datetime
            
        Returns:
            Report data
        """
        # Get content count
        total_count = await self.repository.get_content_count(
            start_date=period_start,
            end_date=period_end,
        )
        
        # Get execution stats
        execution_stats = await self.repository.get_execution_stats(
            start_date=period_start,
            end_date=period_end,
        )
        
        success_stats = execution_stats.get(ExecutionStatus.SUCCESS.value, {})
        failed_stats = execution_stats.get(ExecutionStatus.FAILED.value, {})

        success_count = success_stats.get("count", 0)
        failed_count = failed_stats.get("count", 0)
        retry_count = sum(
            stats.get("total_attempts", 0) - stats.get("count", 0)
            for stats in execution_stats.values()
        )

        # Duration statistics from successful executions
        avg_duration_ms = success_stats.get("avg_duration_ms")
        min_duration_ms = success_stats.get("min_duration_ms")
        max_duration_ms = success_stats.get("max_duration_ms")
        
        # Get category distribution
        category_distribution = await self.repository.get_category_distribution(
            start_date=period_start,
            end_date=period_end,
        )
        
        # Find uncovered categories
        all_categories = set(CATEGORIES.keys())
        covered_categories = set(category_distribution.keys())
        uncovered_categories = list(all_categories - covered_categories)
        
        return ReportData(
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            total_count=total_count,
            success_count=success_count,
            failed_count=failed_count,
            retry_count=max(0, retry_count),
            category_distribution=category_distribution,
            uncovered_categories=uncovered_categories,
            avg_duration_ms=avg_duration_ms,
            min_duration_ms=min_duration_ms,
            max_duration_ms=max_duration_ms,
            generated_at=now(),
        )
