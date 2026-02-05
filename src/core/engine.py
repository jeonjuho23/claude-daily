"""
Core Engine - Main orchestrator for Daily-Bot
Coordinates all components and manages the bot lifecycle
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional, List

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.domain.models import (
    ContentRecord,
    Schedule,
    ExecutionLog,
    TopicRequest,
    BotStatus,
    GeneratedContent,
)
from src.domain.enums import (
    ExecutionStatus,
    ScheduleStatus,
    ContentStatus,
    SlackCommandType,
    Category,
    Difficulty,
)
from src.storage.base import ContentRepository
from src.generators.base import ContentGenerator
from src.integrations.slack import SlackAdapter, CommandHandler
from src.integrations.notion import NotionAdapter
from src.reports import ReportGenerator
from src.errors import ErrorHandler
from src.utils.logger import get_logger
from src.utils.datetime_utils import (
    now,
    parse_time,
    format_time,
    get_next_run_time,
    is_weekday,
    is_month_day,
)
from config.settings import settings
from config.topics import infer_category_from_topic

logger = get_logger(__name__)


class CoreEngine:
    """
    Central orchestrator for Daily-Bot
    
    Manages:
    - Content generation workflow
    - Scheduling
    - Command handling
    - Report generation
    """
    
    def __init__(
        self,
        repository: ContentRepository,
        generator: ContentGenerator,
        slack_adapter: SlackAdapter,
        notion_adapter: NotionAdapter,
        command_handler: Optional[CommandHandler] = None,
    ):
        """
        Initialize core engine
        
        Args:
            repository: Content repository
            generator: Content generator
            slack_adapter: Slack adapter
            notion_adapter: Notion adapter
            command_handler: Optional Slack command handler
        """
        self.repository = repository
        self.generator = generator
        self.slack = slack_adapter
        self.notion = notion_adapter
        self.command_handler = command_handler
        
        # Initialize scheduler
        self.scheduler = AsyncIOScheduler(timezone=settings.timezone)
        
        # Initialize error handler
        self.error_handler = ErrorHandler(
            on_error_callback=self._on_error,
        )
        
        # Initialize report generator
        self.report_generator = ReportGenerator(
            repository=repository,
            slack_adapter=slack_adapter,
            notion_adapter=notion_adapter,
        )
        
        # State
        self._is_running = False
        self._is_paused = False
        self._start_time: Optional[datetime] = None
        
        # Register command handlers
        if self.command_handler:
            self._register_command_handlers()
    
    def _register_command_handlers(self) -> None:
        """Register command handler callbacks"""
        self.command_handler.set_callback(
            SlackCommandType.TIME, self._handle_time_command
        )
        self.command_handler.set_callback(
            SlackCommandType.ADD, self._handle_add_command
        )
        self.command_handler.set_callback(
            SlackCommandType.REMOVE, self._handle_remove_command
        )
        self.command_handler.set_callback(
            SlackCommandType.LIST, self._handle_list_command
        )
        self.command_handler.set_callback(
            SlackCommandType.PAUSE, self._handle_pause_command
        )
        self.command_handler.set_callback(
            SlackCommandType.RESUME, self._handle_resume_command
        )
        self.command_handler.set_callback(
            SlackCommandType.NOW, self._handle_now_command
        )
        self.command_handler.set_callback(
            SlackCommandType.REQUEST, self._handle_request_command
        )
        self.command_handler.set_callback(
            SlackCommandType.STATUS, self._handle_status_command
        )
    
    async def start(self) -> None:
        """Start the bot engine"""
        logger.info("Starting Daily-Bot engine")
        
        # Initialize repository
        await self.repository.initialize()
        
        # Load schedules from database
        await self._load_schedules()
        
        # Schedule report jobs
        self._schedule_reports()
        
        # Start scheduler
        self.scheduler.start()
        
        # Update state
        self._is_running = True
        self._start_time = now()
        
        logger.info("Daily-Bot engine started")
    
    async def stop(self) -> None:
        """Stop the bot engine"""
        logger.info("Stopping Daily-Bot engine")
        
        # Stop scheduler
        self.scheduler.shutdown(wait=False)
        
        # Close repository
        await self.repository.close()
        
        # Update state
        self._is_running = False
        
        logger.info("Daily-Bot engine stopped")
    
    async def _load_schedules(self) -> None:
        """Load schedules from database and create jobs"""
        schedules = await self.repository.list_schedules(status=ScheduleStatus.ACTIVE)
        
        if not schedules:
            # Create default schedule
            default_schedule = Schedule(
                time=settings.default_schedule_time,
                status=ScheduleStatus.ACTIVE,
            )
            default_schedule = await self.repository.save_schedule(default_schedule)
            schedules = [default_schedule]
        
        for schedule in schedules:
            self._add_schedule_job(schedule)
        
        logger.info(f"Loaded {len(schedules)} schedules")
    
    def _add_schedule_job(self, schedule: Schedule) -> None:
        """Add a schedule job to the scheduler"""
        time_obj = parse_time(schedule.time)
        
        job_id = f"content_generation_{schedule.id}"
        
        # Remove existing job if any
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        
        # Add new job
        self.scheduler.add_job(
            self._execute_content_generation,
            CronTrigger(
                hour=time_obj.hour,
                minute=time_obj.minute,
                timezone=settings.timezone,
            ),
            id=job_id,
            args=[schedule.id],
            replace_existing=True,
        )
        
        logger.info(f"Scheduled content generation at {schedule.time}")
    
    def _schedule_reports(self) -> None:
        """Schedule report generation jobs"""
        # Weekly report
        weekly_time = parse_time(settings.weekly_report_time)
        self.scheduler.add_job(
            self._execute_weekly_report,
            CronTrigger(
                day_of_week=settings.weekly_report_day,
                hour=weekly_time.hour,
                minute=weekly_time.minute,
                timezone=settings.timezone,
            ),
            id="weekly_report",
            replace_existing=True,
        )
        
        # Monthly report
        monthly_time = parse_time(settings.monthly_report_time)
        self.scheduler.add_job(
            self._execute_monthly_report,
            CronTrigger(
                day=settings.monthly_report_day,
                hour=monthly_time.hour,
                minute=monthly_time.minute,
                timezone=settings.timezone,
            ),
            id="monthly_report",
            replace_existing=True,
        )
        
        logger.info("Report schedules configured")
    
    async def _execute_content_generation(
        self,
        schedule_id: Optional[int] = None,
        topic_request: Optional[TopicRequest] = None,
    ) -> Optional[ContentRecord]:
        """
        Execute content generation workflow

        Args:
            schedule_id: ID of the schedule that triggered this
            topic_request: Optional specific topic request

        Returns:
            Generated content record
        """
        if self._is_paused:
            logger.info("Skipping execution - bot is paused")
            return None

        # Create execution log
        execution_log = ExecutionLog(
            schedule_id=schedule_id,
            status=ExecutionStatus.PENDING,
        )
        execution_log = await self.repository.save_execution_log(execution_log)

        # Start timing
        start_time = time.perf_counter()

        try:
            # Execute with retry
            content = await self.error_handler.execute_with_retry(
                self._generate_and_publish,
                topic_request=topic_request,
                execution_log=execution_log,
                update_log_callback=self.repository.update_execution_log,
            )

            # Calculate duration
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            execution_log.duration_ms = duration_ms

            # Update execution log with content ID and duration
            execution_log.content_id = content.id
            await self.repository.update_execution_log(execution_log)

            logger.info(
                "Content generation completed",
                content_id=content.id,
                duration_ms=duration_ms,
            )

            # Mark topic request as processed if applicable
            if topic_request:
                await self.repository.mark_request_processed(
                    topic_request.id,
                    content.id,
                )

            return content

        except Exception as e:
            # Record duration even on failure
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            execution_log.duration_ms = duration_ms
            await self.repository.update_execution_log(execution_log)

            logger.error("Content generation failed", error=str(e), duration_ms=duration_ms)
            return None
    
    async def _generate_and_publish(
        self,
        topic_request: Optional[TopicRequest] = None,
    ) -> ContentRecord:
        """
        Generate content and publish to Slack/Notion
        
        Args:
            topic_request: Optional specific topic request
            
        Returns:
            Created content record
        """
        # Get used topics to avoid duplicates
        used_topics = await self.repository.get_used_topics()
        
        # Generate content
        if topic_request:
            # Infer category from topic
            inferred = infer_category_from_topic(topic_request.topic)
            category = Category(inferred) if inferred else Category.ARCHITECTURE
            if not inferred:
                logger.warning("Could not infer category", topic=topic_request.topic)

            generated = await self.generator.generate(
                topic=topic_request.topic,
                category=category,
                difficulty=Difficulty.INTERMEDIATE,
                language=settings.language,
            )
        else:
            # Generate random topic
            generated = await self.generator.generate_random(
                used_topics=used_topics,
                language=settings.language,
            )
        
        # Create content record
        content = ContentRecord(
            title=generated.title,
            category=generated.category,
            difficulty=generated.difficulty,
            summary=generated.summary,
            content=generated.summary,
            tags=generated.tags,
            author=settings.bot_owner_name,
            status=ContentStatus.DRAFT,
        )
        
        # Save to database
        content = await self.repository.save_content(content)
        
        # Create Notion page
        try:
            page_id, page_url = await self.notion.create_content_page(content)
            content.notion_page_id = page_id
            content.notion_url = page_url
        except Exception as e:
            logger.warning("Failed to create Notion page", error=str(e))
        
        # Send Slack notification
        try:
            slack_ts = await self.slack.send_content_notification(content)
            content.slack_ts = slack_ts
        except Exception as e:
            logger.warning("Failed to send Slack notification", error=str(e))
        
        # Update status and save
        content.status = ContentStatus.PUBLISHED
        content = await self.repository.update_content(content)
        
        logger.info("Content published", content_id=content.id, title=content.title)
        
        return content
    
    async def _execute_weekly_report(self) -> None:
        """Execute weekly report generation"""
        try:
            await self.report_generator.generate_weekly_report()
        except Exception as e:
            logger.error("Weekly report generation failed", error=str(e))
    
    async def _execute_monthly_report(self) -> None:
        """Execute monthly report generation"""
        try:
            await self.report_generator.generate_monthly_report()
        except Exception as e:
            logger.error("Monthly report generation failed", error=str(e))
    
    async def _on_error(self, error_message: str, context: dict) -> None:
        """Error callback for notifications"""
        await self.slack.send_error_notification(error_message, context)
    
    # ========== Command Handlers ==========
    
    async def _handle_time_command(
        self,
        time_str: str,
        user_id: str,
        channel_id: str,
    ) -> str:
        """Handle time command - change primary schedule"""
        # Get existing schedules
        schedules = await self.repository.list_schedules(status=ScheduleStatus.ACTIVE)
        
        if schedules:
            # Update first schedule
            schedule = schedules[0]
            old_time = schedule.time
            schedule.time = time_str
            await self.repository.update_schedule(schedule)
            self._add_schedule_job(schedule)
            return f"✅ 스케줄 시간이 변경되었습니다: `{old_time}` → `{time_str}`"
        else:
            # Create new schedule
            schedule = Schedule(time=time_str, status=ScheduleStatus.ACTIVE)
            schedule = await self.repository.save_schedule(schedule)
            self._add_schedule_job(schedule)
            return f"✅ 새 스케줄이 생성되었습니다: `{time_str}`"
    
    async def _handle_add_command(
        self,
        time_str: str,
        user_id: str,
        channel_id: str,
    ) -> str:
        """Handle add command - add new schedule"""
        # Check if schedule already exists
        existing = await self.repository.get_schedule_by_time(time_str)
        if existing:
            return f"❌ 이미 `{time_str}` 스케줄이 존재합니다."
        
        # Create schedule
        schedule = Schedule(time=time_str, status=ScheduleStatus.ACTIVE)
        schedule = await self.repository.save_schedule(schedule)
        self._add_schedule_job(schedule)
        
        return f"✅ 스케줄이 추가되었습니다: `{time_str}`"
    
    async def _handle_remove_command(
        self,
        time_str: str,
        user_id: str,
        channel_id: str,
    ) -> str:
        """Handle remove command - remove schedule"""
        schedule = await self.repository.get_schedule_by_time(time_str)
        
        if not schedule:
            return f"❌ `{time_str}` 스케줄을 찾을 수 없습니다."
        
        # Remove job
        job_id = f"content_generation_{schedule.id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        
        # Delete schedule
        await self.repository.delete_schedule(schedule.id)
        
        return f"✅ 스케줄이 삭제되었습니다: `{time_str}`"
    
    async def _handle_list_command(
        self,
        user_id: str,
        channel_id: str,
    ) -> str:
        """Handle list command - list all schedules"""
        schedules = await self.repository.list_schedules(status=ScheduleStatus.ACTIVE)
        
        if not schedules:
            return "📋 등록된 스케줄이 없습니다."
        
        lines = ["📋 *등록된 스케줄:*"]
        for schedule in schedules:
            next_run = get_next_run_time(schedule.time)
            lines.append(f"• `{schedule.time}` (다음 실행: {next_run.strftime('%m/%d %H:%M')})")
        
        return "\n".join(lines)
    
    async def _handle_pause_command(
        self,
        user_id: str,
        channel_id: str,
    ) -> str:
        """Handle pause command"""
        if self._is_paused:
            return "ℹ️ 이미 일시정지 상태입니다."
        
        self._is_paused = True
        return "⏸️ 콘텐츠 생성이 일시정지되었습니다. `/daily-bot resume`으로 재개하세요."
    
    async def _handle_resume_command(
        self,
        user_id: str,
        channel_id: str,
    ) -> str:
        """Handle resume command"""
        if not self._is_paused:
            return "ℹ️ 이미 실행 중입니다."
        
        self._is_paused = False
        return "▶️ 콘텐츠 생성이 재개되었습니다."
    
    async def _handle_now_command(
        self,
        user_id: str,
        channel_id: str,
    ) -> str:
        """Handle now command - execute immediately"""
        # Execute in background
        from src.utils.async_utils import create_background_task
        create_background_task(
            self._execute_content_generation(),
            context="Immediate content generation",
        )
        return "🚀 콘텐츠 생성을 시작합니다. 잠시 후 결과가 게시됩니다."
    
    async def _handle_request_command(
        self,
        topic: str,
        user_id: str,
        channel_id: str,
    ) -> str:
        """Handle request command - request specific topic"""
        # Save topic request
        request = TopicRequest(
            topic=topic,
            requested_by=user_id,
        )
        request = await self.repository.save_topic_request(request)

        # Execute immediately in background
        from src.utils.async_utils import create_background_task
        create_background_task(
            self._execute_content_generation(topic_request=request),
            context=f"Topic request: {request.topic}",
        )

        return f"📝 `{topic}` 주제가 요청되었습니다. 잠시 후 결과가 게시됩니다."
    
    async def _handle_status_command(
        self,
        user_id: str,
        channel_id: str,
    ) -> str:
        """Handle status command"""
        status = await self.get_status()
        await self.slack.send_status(status, channel_id)
        return ""  # Status is sent as rich message
    
    async def get_status(self) -> BotStatus:
        """Get current bot status"""
        # Get active schedules
        schedules = await self.repository.list_schedules(status=ScheduleStatus.ACTIVE)
        schedule_times = [s.time for s in schedules]
        
        # Get total generated count
        total_generated = await self.repository.get_content_count()
        
        # Get next execution time
        next_execution = None
        for schedule in schedules:
            next_run = get_next_run_time(schedule.time)
            if next_execution is None or next_run < next_execution:
                next_execution = next_run
        
        # Get last execution
        logs = await self.repository.list_execution_logs(limit=1)
        last_execution = logs[0].started_at if logs else None
        last_error = logs[0].error_message if logs and logs[0].error_message else None
        
        # Calculate uptime
        uptime = 0
        if self._start_time:
            uptime = int((now() - self._start_time).total_seconds())
        
        return BotStatus(
            is_running=self._is_running,
            is_paused=self._is_paused,
            active_schedules=schedule_times,
            next_execution=next_execution,
            total_generated=total_generated,
            last_execution=last_execution,
            last_error=last_error,
            uptime_seconds=uptime,
        )
