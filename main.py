#!/usr/bin/env python3
"""
Daily-Bot - Automated CS Knowledge Sharing Bot
Main entry point
"""

import asyncio
import signal
import sys
from pathlib import Path
from types import FrameType

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from src.core import CoreEngine
from src.generators import ClaudeCodeGenerator
from src.integrations.notion import NotionAdapter
from src.integrations.slack import CommandHandler, SlackAdapter
from src.storage import SQLiteRepository
from src.utils.async_utils import create_background_task
from src.utils.logger import cleanup_old_logs, get_logger, setup_logging


async def main() -> None:
    """Main entry point"""
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)

    logger.info("=" * 50)
    logger.info("Daily-Bot Starting")
    logger.info("=" * 50)

    # Cleanup old logs
    deleted = cleanup_old_logs()
    if deleted > 0:
        logger.info(f"Cleaned up {deleted} old log files")

    # Initialize components
    logger.info("Initializing components...")

    repository = SQLiteRepository(db_path=str(settings.get_db_full_path()))
    generator = ClaudeCodeGenerator()
    slack_adapter = SlackAdapter()
    notion_adapter = NotionAdapter() if settings.notion_enabled else None
    command_handler = CommandHandler()

    # Create engine
    engine = CoreEngine(
        repository=repository,
        generator=generator,
        slack_adapter=slack_adapter,
        notion_adapter=notion_adapter,
        command_handler=command_handler,
    )

    # Setup shutdown handler
    shutdown_event = asyncio.Event()

    def signal_handler(sig: int, frame: FrameType | None) -> None:
        logger.info(f"Received signal {sig}, initiating shutdown...")
        shutdown_event.set()

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Start engine
        await engine.start()

        # Health checks
        logger.info("Running health checks...")

        slack_healthy = await slack_adapter.health_check()
        logger.info(f"Slack API: {'OK' if slack_healthy else 'FAIL'}")

        if notion_adapter:
            notion_healthy = await notion_adapter.health_check()
            logger.info(f"Notion API: {'OK' if notion_healthy else 'FAIL'}")
        else:
            notion_healthy = True
            logger.info("Notion API: SKIPPED (not configured)")

        claude_healthy = await generator.health_check()
        logger.info(f"Claude Code CLI: {'OK' if claude_healthy else 'FAIL'}")

        if not all([slack_healthy, notion_healthy, claude_healthy]):
            logger.warning("Some health checks failed - bot may not function properly")

        logger.info("Daily-Bot is running. Press Ctrl+C to stop.")

        # Start command handler in background
        create_background_task(
            command_handler.start(),
            context="Slack command handler",
        )

        # Wait for shutdown signal
        await shutdown_event.wait()

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        # Cleanup
        logger.info("Shutting down...")
        await engine.stop()
        logger.info("Daily-Bot stopped")


def run() -> None:
    """Run the bot"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested...")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run()
