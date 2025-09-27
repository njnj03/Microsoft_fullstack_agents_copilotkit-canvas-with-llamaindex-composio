#!/usr/bin/env python
"""
Startup script to run both MCP server and Frontend API
"""

import os
import sys
import subprocess
import time
import signal
import logging
from multiprocessing import Process

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_mcp_server():
    """Run the MCP server"""
    logger.info("Starting MCP Server on port 8000...")
    os.system("python -m agent.task_distribution_mcp")

def run_frontend_api():
    """Run the Frontend API"""
    logger.info("Starting Frontend API on port 8001...")
    os.system("python agent/frontend_api.py")

def main():
    """Run both servers"""
    print("🚀 Starting Task Distribution System")
    print("=" * 50)
    print("MCP Server: http://localhost:8000")
    print("Frontend API: http://localhost:8001")
    print("=" * 50)

    # Start MCP server
    mcp_process = Process(target=run_mcp_server)
    mcp_process.start()

    # Wait a bit for MCP server to start
    time.sleep(3)

    # Start Frontend API
    frontend_process = Process(target=run_frontend_api)
    frontend_process.start()

    try:
        logger.info("Both servers started successfully!")
        logger.info("Press Ctrl+C to stop both servers")

        # Keep the main process alive
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Shutting down servers...")

        # Terminate processes
        mcp_process.terminate()
        frontend_process.terminate()

        # Wait for clean shutdown
        mcp_process.join(timeout=5)
        frontend_process.join(timeout=5)

        # Force kill if still running
        if mcp_process.is_alive():
            mcp_process.kill()
        if frontend_process.is_alive():
            frontend_process.kill()

        logger.info("Servers stopped successfully!")

if __name__ == "__main__":
    main()