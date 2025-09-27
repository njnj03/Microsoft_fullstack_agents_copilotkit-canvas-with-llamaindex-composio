"""
Task Distribution Agent with Composio Slack Integration
"""

import uvicorn
from .server import app

def main():
    """Run the main server"""
    uvicorn.run(app, host="127.0.0.1", port=9000)

def run_task_mcp():
    """Run the task distribution MCP server"""
    from .task_distribution_mcp import run_server
    run_server()

if __name__ == "__main__":
    main()

__all__ = ["app", "main", "run_task_mcp"]
