"""
Main production service for Slack MCP integration
Combines all components for a production-ready deployment
"""

import os
import sys
import logging
import signal
import asyncio
from typing import Optional
from datetime import datetime
import json

from dotenv import load_dotenv
from .mcp_server import run_server
from .slack_integration import SlackComposioIntegration

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.getenv('LOG_FILE', 'slack_bot.log'))
    ]
)
logger = logging.getLogger(__name__)


class SlackMCPService:
    """Main service orchestrator for Slack MCP integration"""

    def __init__(self):
        self.slack_integration: Optional[SlackComposioIntegration] = None
        self.is_running = False
        self.startup_time = None

    async def initialize(self):
        """Initialize all service components"""
        logger.info("Initializing Slack MCP Service...")

        # Initialize Slack integration
        self.slack_integration = SlackComposioIntegration(
            user_id=os.getenv('COMPOSIO_USER_ID', 'default'),
            enable_cache=os.getenv('REDIS_URL') is not None
        )

        # Check Slack connection status
        is_connected = await self.slack_integration.check_connection_status()
        if not is_connected:
            logger.warning("Slack is not connected. Starting authentication flow...")
            await self.setup_authentication()
        else:
            logger.info("Slack connection is active and ready")

        self.startup_time = datetime.now()
        self.is_running = True
        logger.info("Slack MCP Service initialized successfully")

    async def setup_authentication(self):
        """Setup Slack authentication if not connected"""
        try:
            auth_data = await self.slack_integration.initiate_connection()
            auth_url = auth_data.get('auth_url')

            logger.info("=" * 60)
            logger.info("AUTHENTICATION REQUIRED")
            logger.info("=" * 60)
            logger.info(f"Please visit the following URL to authenticate:")
            logger.info(f"{auth_url}")
            logger.info("=" * 60)

            # Wait for user to complete authentication
            max_attempts = 60  # 5 minutes timeout
            for attempt in range(max_attempts):
                await asyncio.sleep(5)
                is_connected = await self.slack_integration.check_connection_status()
                if is_connected:
                    logger.info("Authentication successful!")
                    break
            else:
                logger.error("Authentication timeout. Please restart the service and try again.")
                sys.exit(1)

        except Exception as e:
            logger.error(f"Authentication setup failed: {e}")
            raise

    async def health_monitor(self):
        """Periodic health monitoring"""
        while self.is_running:
            try:
                health = await self.slack_integration.healthcheck()
                if health['status'] != 'healthy':
                    logger.warning(f"Service degraded: {health}")

                # Process retry queue periodically
                await self.slack_integration.process_retry_queue()

            except Exception as e:
                logger.error(f"Health monitor error: {e}")

            await asyncio.sleep(60)  # Check every minute

    async def run(self):
        """Run the main service"""
        await self.initialize()

        # Start health monitoring
        health_task = asyncio.create_task(self.health_monitor())

        # Start MCP server in a separate thread
        import threading
        server_thread = threading.Thread(target=run_server)
        server_thread.daemon = True
        server_thread.start()

        logger.info("Service is running. Press Ctrl+C to stop.")

        try:
            # Keep the service running
            while self.is_running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutdown signal received...")
        finally:
            self.is_running = False
            health_task.cancel()
            logger.info("Service shutdown complete")

    def shutdown(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}")
        self.is_running = False


async def main():
    """Main entry point"""
    service = SlackMCPService()

    # Register signal handlers
    signal.signal(signal.SIGINT, service.shutdown)
    signal.signal(signal.SIGTERM, service.shutdown)

    try:
        await service.run()
    except Exception as e:
        logger.error(f"Service failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Check required environment variables
    required_vars = [
        'OPENAI_API_KEY',
        'COMPOSIO_API_KEY',
        'SLACK_BOT_TOKEN'
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error("Please check your .env file")
        sys.exit(1)

    # Run the service
    asyncio.run(main())