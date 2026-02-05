"""
Slack command handler
Handles slash commands from Slack
"""

import re
from typing import Optional, Callable, Awaitable, Dict, Any

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from src.domain.enums import SlackCommandType
from src.utils.logger import get_logger
from src.utils.datetime_utils import parse_time
from config.settings import settings

logger = get_logger(__name__)


class CommandHandler:
    """
    Handles Slack slash commands for Daily-Bot
    
    Supported commands:
    - /daily-bot time <HH:MM> - Change schedule time
    - /daily-bot add <HH:MM> - Add schedule
    - /daily-bot remove <HH:MM> - Remove schedule
    - /daily-bot list - List schedules
    - /daily-bot pause - Pause scheduling
    - /daily-bot resume - Resume scheduling
    - /daily-bot now - Execute immediately
    - /daily-bot request "<topic>" - Request specific topic
    - /daily-bot status - Check status
    - /daily-bot help - Show help
    """
    
    def __init__(self):
        """Initialize command handler"""
        self.app = AsyncApp(
            token=settings.slack_bot_token,
            signing_secret=settings.slack_signing_secret,
        )
        
        # Command callbacks (to be set by core engine)
        self._callbacks: Dict[SlackCommandType, Callable[..., Awaitable[str]]] = {}
        
        # Register command handler
        self._register_commands()
    
    def set_callback(
        self,
        command_type: SlackCommandType,
        callback: Callable[..., Awaitable[str]],
    ) -> None:
        """
        Set callback for a command type
        
        Args:
            command_type: Type of command
            callback: Async callback function that returns response text
        """
        self._callbacks[command_type] = callback
        logger.debug("Callback registered", command_type=command_type.value)
    
    def _register_commands(self) -> None:
        """Register slash command handler"""
        
        @self.app.command("/daily-bot")
        async def handle_command(ack, command, respond):
            """Handle /daily-bot command"""
            await ack()
            
            text = command.get("text", "").strip()
            user_id = command.get("user_id")
            channel_id = command.get("channel_id")
            
            logger.info(
                "Command received",
                text=text,
                user_id=user_id,
                channel_id=channel_id,
            )
            
            try:
                response = await self._process_command(text, user_id, channel_id)
                await respond(response)
            except Exception as e:
                logger.error("Command processing failed", error=str(e))
                await respond(f"❌ 명령 처리 중 오류가 발생했습니다: {str(e)}")
    
    async def _process_command(
        self,
        text: str,
        user_id: str,
        channel_id: str,
    ) -> str:
        """
        Process command text and return response
        
        Args:
            text: Command text (after /daily-bot)
            user_id: User who issued command
            channel_id: Channel where command was issued
            
        Returns:
            Response message
        """
        if not text:
            return await self._handle_help(channel_id)
        
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # Map command to handler
        handlers = {
            "time": self._handle_time,
            "add": self._handle_add,
            "remove": self._handle_remove,
            "list": self._handle_list,
            "pause": self._handle_pause,
            "resume": self._handle_resume,
            "now": self._handle_now,
            "request": self._handle_request,
            "status": self._handle_status,
            "help": self._handle_help,
        }
        
        handler = handlers.get(cmd)
        if handler:
            return await handler(args, user_id, channel_id)
        else:
            return f"❌ 알 수 없는 명령어입니다: `{cmd}`\n`/daily-bot help`로 사용 가능한 명령어를 확인하세요."
    
    async def _handle_time(self, args: str, user_id: str, channel_id: str) -> str:
        """Handle time command - change primary schedule time"""
        if not args:
            return "❌ 시간을 입력해주세요.\n사용법: `/daily-bot time 07:00`"
        
        try:
            parse_time(args.strip())
        except ValueError:
            return f"❌ 잘못된 시간 형식입니다: `{args}`\nHH:MM 형식으로 입력하세요. (예: 07:00)"
        
        callback = self._callbacks.get(SlackCommandType.TIME)
        if callback:
            return await callback(args.strip(), user_id, channel_id)
        return "❌ 명령어 핸들러가 설정되지 않았습니다."
    
    async def _handle_add(self, args: str, user_id: str, channel_id: str) -> str:
        """Handle add command - add new schedule"""
        if not args:
            return "❌ 추가할 시간을 입력해주세요.\n사용법: `/daily-bot add 19:00`"
        
        try:
            parse_time(args.strip())
        except ValueError:
            return f"❌ 잘못된 시간 형식입니다: `{args}`\nHH:MM 형식으로 입력하세요. (예: 19:00)"
        
        callback = self._callbacks.get(SlackCommandType.ADD)
        if callback:
            return await callback(args.strip(), user_id, channel_id)
        return "❌ 명령어 핸들러가 설정되지 않았습니다."
    
    async def _handle_remove(self, args: str, user_id: str, channel_id: str) -> str:
        """Handle remove command - remove schedule"""
        if not args:
            return "❌ 삭제할 시간을 입력해주세요.\n사용법: `/daily-bot remove 19:00`"
        
        callback = self._callbacks.get(SlackCommandType.REMOVE)
        if callback:
            return await callback(args.strip(), user_id, channel_id)
        return "❌ 명령어 핸들러가 설정되지 않았습니다."
    
    async def _handle_list(self, args: str, user_id: str, channel_id: str) -> str:
        """Handle list command - list all schedules"""
        callback = self._callbacks.get(SlackCommandType.LIST)
        if callback:
            return await callback(user_id, channel_id)
        return "❌ 명령어 핸들러가 설정되지 않았습니다."
    
    async def _handle_pause(self, args: str, user_id: str, channel_id: str) -> str:
        """Handle pause command"""
        callback = self._callbacks.get(SlackCommandType.PAUSE)
        if callback:
            return await callback(user_id, channel_id)
        return "❌ 명령어 핸들러가 설정되지 않았습니다."
    
    async def _handle_resume(self, args: str, user_id: str, channel_id: str) -> str:
        """Handle resume command"""
        callback = self._callbacks.get(SlackCommandType.RESUME)
        if callback:
            return await callback(user_id, channel_id)
        return "❌ 명령어 핸들러가 설정되지 않았습니다."
    
    async def _handle_now(self, args: str, user_id: str, channel_id: str) -> str:
        """Handle now command - execute immediately"""
        callback = self._callbacks.get(SlackCommandType.NOW)
        if callback:
            return await callback(user_id, channel_id)
        return "❌ 명령어 핸들러가 설정되지 않았습니다."
    
    async def _handle_request(self, args: str, user_id: str, channel_id: str) -> str:
        """Handle request command - request specific topic"""
        if not args:
            return "❌ 요청할 주제를 입력해주세요.\n사용법: `/daily-bot request \"TCP 3-way handshake\"`"
        
        # Extract topic from quotes if present
        match = re.match(r'^["\'](.+)["\']$', args.strip())
        topic = match.group(1) if match else args.strip()
        
        callback = self._callbacks.get(SlackCommandType.REQUEST)
        if callback:
            return await callback(topic, user_id, channel_id)
        return "❌ 명령어 핸들러가 설정되지 않았습니다."
    
    async def _handle_status(self, args: str, user_id: str, channel_id: str) -> str:
        """Handle status command"""
        callback = self._callbacks.get(SlackCommandType.STATUS)
        if callback:
            return await callback(user_id, channel_id)
        return "❌ 명령어 핸들러가 설정되지 않았습니다."
    
    async def _handle_help(self, *args) -> str:
        """Handle help command"""
        return (
            "📖 *Daily-Bot 명령어 도움말*\n\n"
            "*스케줄 관리:*\n"
            "• `/daily-bot time <HH:MM>` - 기본 스케줄 시간 변경\n"
            "• `/daily-bot add <HH:MM>` - 스케줄 추가\n"
            "• `/daily-bot remove <HH:MM>` - 스케줄 삭제\n"
            "• `/daily-bot list` - 스케줄 목록 보기\n\n"
            "*실행 제어:*\n"
            "• `/daily-bot pause` - 일시정지\n"
            "• `/daily-bot resume` - 재개\n"
            "• `/daily-bot now` - 즉시 실행\n\n"
            "*기타:*\n"
            "• `/daily-bot request \"<주제>\"` - 특정 주제 요청\n"
            "• `/daily-bot status` - 현재 상태 확인\n"
            "• `/daily-bot help` - 이 도움말\n\n"
            "💡 시간은 24시간 형식(HH:MM)으로 입력하세요."
        )
    
    async def start(self) -> None:
        """Start the command handler with Socket Mode"""
        handler = AsyncSocketModeHandler(self.app, settings.slack_app_token)
        logger.info("Starting Slack command handler (Socket Mode)")
        await handler.start_async()
    
    async def stop(self) -> None:
        """Stop the command handler"""
        logger.info("Stopping Slack command handler")
        # Socket Mode handler will be stopped when the event loop ends
