"""
Slack integration adapter
Handles all Slack API interactions
"""

from datetime import datetime, timedelta
from typing import Any

from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from config.settings import settings
from config.topics import get_category_name
from src.utils.rate_limiter import AsyncRateLimiter
from src.domain.enums import Category
from src.domain.models import BotStatus, ContentRecord, ReportData, SlackMessage
from src.utils.datetime_utils import format_datetime, humanize_timedelta
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SlackAdapter:
    """
    Adapter for Slack API interactions

    Handles message sending, block formatting, and error notifications.
    """

    def __init__(self, bot_token: str | None = None):
        """
        Initialize Slack adapter

        Args:
            bot_token: Override bot token from settings
        """
        self.client = AsyncWebClient(token=bot_token or settings.slack_bot_token)
        self._rate_limiter = AsyncRateLimiter(rate=settings.slack_rate_limit, period=60.0, burst=5)

    async def send_message(self, message: SlackMessage) -> str | None:
        """
        Send a message to Slack

        Args:
            message: SlackMessage to send

        Returns:
            Message timestamp if successful, None otherwise
        """
        try:
            async with self._rate_limiter:
                response = await self.client.chat_postMessage(
                    channel=message.channel,
                    text=message.text,
                    blocks=message.blocks,
                    thread_ts=message.thread_ts,
                )

            logger.info(
                "Slack message sent",
                channel=message.channel,
                ts=response.get("ts"),
            )

            return response.get("ts")

        except SlackApiError as e:
            logger.error(
                "Failed to send Slack message",
                channel=message.channel,
                error=str(e),
            )
            return None

    async def send_content_notification(
        self,
        content: ContentRecord,
        channel: str | None = None,
    ) -> str | None:
        """
        Send content notification to Slack channel

        Args:
            content: Content record to notify about
            channel: Override channel from settings

        Returns:
            Message timestamp if successful
        """
        target_channel = channel or settings.slack_channel_id

        # Get category display name
        category_name = get_category_name(
            content.category.value if isinstance(content.category, Category) else content.category,
            settings.language,
        )

        # Build blocks for rich formatting
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"📚 {content.title}", "emoji": True},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*카테고리:* {category_name}"},
                    {
                        "type": "mrkdwn",
                        "text": f"*난이도:* {content.difficulty.korean if hasattr(content.difficulty, 'korean') else content.difficulty}",
                    },
                ],
            },
            {"type": "section", "text": {"type": "mrkdwn", "text": content.summary}},
        ]

        # Add Notion link if available
        if content.notion_url:
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"📖 <{content.notion_url}|자세히 보기>"},
                }
            )

        # Add tags
        if content.tags:
            tags_text = " ".join([f"`{tag}`" for tag in content.tags])
            blocks.append(
                {"type": "context", "elements": [{"type": "mrkdwn", "text": f"🏷️ {tags_text}"}]}
            )

        # Add divider
        blocks.append({"type": "divider"})

        message = SlackMessage(
            channel=target_channel,
            text=f"📚 {content.title}\n\n{content.summary}",
            blocks=blocks,
        )

        return await self.send_message(message)

    async def send_error_notification(
        self,
        error_message: str,
        context: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> str | None:
        """
        Send error notification (DM to user or channel)

        Args:
            error_message: Error message to send
            context: Additional context information
            user_id: User ID for DM (if None, sends to channel)

        Returns:
            Message timestamp if successful
        """
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "⚠️ Daily-Bot 오류 알림", "emoji": True},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*오류 내용:*\n```{error_message}```"},
            },
        ]

        if context:
            context_text = "\n".join([f"• *{k}:* {v}" for k, v in context.items()])
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*상세 정보:*\n{context_text}"},
                }
            )

        blocks.append(
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"🕐 {format_datetime(datetime.now())}"}],
            }
        )

        # Determine channel (DM or default channel)
        if user_id:
            # Open DM conversation
            try:
                response = await self.client.conversations_open(users=[user_id])
                channel = response["channel"]["id"]
            except SlackApiError:
                channel = settings.slack_channel_id
        else:
            channel = settings.slack_channel_id

        message = SlackMessage(
            channel=channel,
            text=f"⚠️ Daily-Bot 오류: {error_message}",
            blocks=blocks,
        )

        return await self.send_message(message)

    async def send_status(
        self,
        status: BotStatus,
        channel: str,
    ) -> str | None:
        """
        Send bot status information

        Args:
            status: Current bot status
            channel: Channel to send to

        Returns:
            Message timestamp if successful
        """
        # Status emoji
        if status.is_paused:
            status_emoji = "⏸️"
            status_text = "일시정지"
        elif status.is_running:
            status_emoji = "✅"
            status_text = "실행 중"
        else:
            status_emoji = "❌"
            status_text = "중지됨"

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "📊 Daily-Bot 상태", "emoji": True},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*상태:* {status_emoji} {status_text}"},
                    {"type": "mrkdwn", "text": f"*총 생성 콘텐츠:* {status.total_generated}개"},
                ],
            },
        ]

        # Schedules
        if status.active_schedules:
            schedules_text = ", ".join(status.active_schedules)
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*활성 스케줄:* {schedules_text}"},
                }
            )

        # Next execution
        if status.next_execution:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*다음 실행:* {format_datetime(status.next_execution)}",
                    },
                }
            )

        # Last execution
        if status.last_execution:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*마지막 실행:* {format_datetime(status.last_execution)}",
                    },
                }
            )

        # Uptime
        if status.uptime_seconds > 0:
            uptime = humanize_timedelta(timedelta(seconds=status.uptime_seconds))
            blocks.append(
                {
                    "type": "context",
                    "elements": [{"type": "mrkdwn", "text": f"⏱️ 가동 시간: {uptime}"}],
                }
            )

        message = SlackMessage(
            channel=channel,
            text=f"📊 Daily-Bot 상태: {status_text}",
            blocks=blocks,
        )

        return await self.send_message(message)

    async def send_report_notification(
        self,
        report: ReportData,
        notion_url: str | None = None,
        channel: str | None = None,
    ) -> str | None:
        """
        Send report notification to Slack

        Args:
            report: Report data
            notion_url: Link to detailed Notion report
            channel: Override channel

        Returns:
            Message timestamp if successful
        """
        target_channel = channel or settings.report_channel

        report_type = "주간" if report.report_type == "weekly" else "월간"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📈 Daily-Bot {report_type} 리포트",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*기간:* {format_datetime(report.period_start, False)} ~ {format_datetime(report.period_end, False)}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*총 발송:* {report.total_count}건"},
                    {"type": "mrkdwn", "text": f"*성공:* {report.success_count}건"},
                    {"type": "mrkdwn", "text": f"*실패:* {report.failed_count}건"},
                    {"type": "mrkdwn", "text": f"*재시도:* {report.retry_count}건"},
                ],
            },
        ]

        # Category distribution
        if report.category_distribution:
            dist_text = "\n".join(
                [
                    f"• {get_category_name(cat, settings.language)}: {count}건"
                    for cat, count in sorted(
                        report.category_distribution.items(), key=lambda x: x[1], reverse=True
                    )[:5]
                ]
            )
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*카테고리 분포 (Top 5):*\n{dist_text}"},
                }
            )

        # Uncovered categories
        if report.uncovered_categories:
            uncovered_text = ", ".join(
                [get_category_name(cat, settings.language) for cat in report.uncovered_categories]
            )
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*미다룬 카테고리:* {uncovered_text}"},
                }
            )

        # Notion link
        if notion_url:
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"📖 <{notion_url}|상세 리포트 보기>"},
                }
            )

        message = SlackMessage(
            channel=target_channel,
            text=f"📈 Daily-Bot {report_type} 리포트가 생성되었습니다.",
            blocks=blocks,
        )

        return await self.send_message(message)

    async def send_help(self, channel: str) -> str | None:
        """
        Send help information

        Args:
            channel: Channel to send to

        Returns:
            Message timestamp if successful
        """
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "📖 Daily-Bot 명령어 도움말", "emoji": True},
            },
            {"type": "section", "text": {"type": "mrkdwn", "text": "*사용 가능한 명령어:*"}},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "`/daily-bot time <HH:MM>` - 스케줄 시간 변경\n"
                        "`/daily-bot add <HH:MM>` - 스케줄 추가\n"
                        "`/daily-bot remove <HH:MM>` - 스케줄 삭제\n"
                        "`/daily-bot list` - 스케줄 목록 보기\n"
                        "`/daily-bot pause` - 일시정지\n"
                        "`/daily-bot resume` - 재개\n"
                        "`/daily-bot now` - 즉시 실행\n"
                        '`/daily-bot request "<주제>"` - 주제 요청\n'
                        "`/daily-bot status` - 상태 확인\n"
                        "`/daily-bot help` - 이 도움말"
                    ),
                },
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": "💡 시간은 24시간 형식(HH:MM)으로 입력하세요."}
                ],
            },
        ]

        message = SlackMessage(
            channel=channel,
            text="📖 Daily-Bot 명령어 도움말",
            blocks=blocks,
        )

        return await self.send_message(message)

    async def health_check(self) -> bool:
        """
        Check Slack API connection

        Returns:
            True if healthy
        """
        try:
            response = await self.client.auth_test()
            return response.get("ok", False)
        except SlackApiError as e:
            logger.warning("Slack health check failed", error=str(e))
            return False
