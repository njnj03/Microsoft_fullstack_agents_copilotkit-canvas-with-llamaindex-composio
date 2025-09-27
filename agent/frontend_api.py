#!/usr/bin/env python
"""
Frontend FastAPI Server for Task Distribution
Acts as an intermediary between frontend and MCP server
"""

import os
import logging
import aiohttp
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Task Distribution Frontend API",
    description="Frontend API for distributing tasks to team members via Slack",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
MCP_SERVER_URL = os.getenv('MCP_SERVER_URL', 'http://localhost:8000')


# Request Models
class TaskDistributionRequest(BaseModel):
    """Request model for task distribution"""
    email_ids: List[str] = Field(..., description="List of email IDs to assign tasks to")
    task_text: str = Field(..., description="The task description/command to distribute")
    title: Optional[str] = Field("Task Assignment", description="Task title")
    priority: str = Field("normal", description="Task priority (low, normal, high, urgent)")
    project: Optional[str] = Field(None, description="Project name")
    notify_channel: Optional[str] = Field(None, description="Slack channel to notify")


class QuickTaskRequest(BaseModel):
    """Quick task assignment request"""
    email: str = Field(..., description="Email ID of the assignee")
    task_description: str = Field(..., description="Task description")
    title: Optional[str] = Field("Quick Task", description="Task title")
    priority: str = Field("normal", description="Task priority")


# Response Models
class TaskDistributionResponse(BaseModel):
    """Response model for task distribution"""
    success: bool
    message: str
    total_tasks: int
    successful_assignments: int
    failed_assignments: int
    details: List[Dict[str, Any]]


class MCPClient:
    """Client to communicate with MCP server"""

    def __init__(self, mcp_url: str):
        self.mcp_url = mcp_url.rstrip('/')

    async def health_check(self) -> bool:
        """Check if MCP server is healthy"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.mcp_url}/health") as response:
                    if response.status == 200:
                        return True
                    return False
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def send_batch_tasks(self, tasks_data: List[Dict], notify_channel: str = None) -> Dict:
        """Send multiple tasks via MCP server"""
        batch_data = {
            "tasks": tasks_data
        }

        if notify_channel:
            batch_data["notify_channel"] = notify_channel

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.mcp_url}/tasks/batch", json=batch_data) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise Exception(f"MCP server error: {error_text}")
        except Exception as e:
            logger.error(f"Failed to send batch tasks: {e}")
            raise

    async def quick_assign(self, email: str, title: str, description: str, priority: str = "normal") -> Dict:
        """Quick task assignment via MCP server"""
        params = {
            "email": email,
            "title": title,
            "description": description,
            "priority": priority
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.mcp_url}/tasks/assign", params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise Exception(f"MCP server error: {error_text}")
        except Exception as e:
            logger.error(f"Failed to quick assign task to {email}: {e}")
            raise


# Initialize MCP client
mcp_client = MCPClient(MCP_SERVER_URL)


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Task Distribution Frontend API",
        "version": "1.0.0",
        "mcp_server": MCP_SERVER_URL,
        "endpoints": [
            "/health",
            "/distribute-tasks",
            "/quick-assign"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    mcp_healthy = await mcp_client.health_check()

    return {
        "status": "healthy" if mcp_healthy else "degraded",
        "mcp_server": "connected" if mcp_healthy else "disconnected",
        "mcp_url": MCP_SERVER_URL,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/distribute-tasks", response_model=TaskDistributionResponse)
async def distribute_tasks(request: TaskDistributionRequest, background_tasks: BackgroundTasks):
    """
    Distribute tasks to multiple team members equally

    Takes a list of email IDs and a task description,
    then distributes the same task to all team members via Slack.
    """
    try:
        # Check MCP server health
        if not await mcp_client.health_check():
            raise HTTPException(status_code=503, detail="MCP server is not available")

        if not request.email_ids:
            raise HTTPException(status_code=400, detail="No email IDs provided")

        if not request.task_text.strip():
            raise HTTPException(status_code=400, detail="Task description cannot be empty")

        # Prepare tasks for equal distribution
        tasks_data = []

        for email in request.email_ids:
            task_data = {
                "title": request.title,
                "description": request.task_text,
                "assignee_email": email.strip(),
                "priority": request.priority
            }

            if request.project:
                task_data["project"] = request.project

            tasks_data.append(task_data)

        logger.info(f"Distributing {len(tasks_data)} tasks to {len(request.email_ids)} team members")

        # Send tasks via MCP server
        result = await mcp_client.send_batch_tasks(tasks_data, request.notify_channel)

        # Format response
        if result.get("success"):
            mcp_results = result.get("results", {})
            return TaskDistributionResponse(
                success=True,
                message=f"Tasks distributed successfully to {len(request.email_ids)} team members",
                total_tasks=mcp_results.get("total", len(tasks_data)),
                successful_assignments=mcp_results.get("successful", 0),
                failed_assignments=mcp_results.get("failed", 0),
                details=mcp_results.get("details", [])
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to distribute tasks")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Task distribution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/quick-assign")
async def quick_assign_task(request: QuickTaskRequest):
    """
    Quick task assignment to a single user
    """
    try:
        # Check MCP server health
        if not await mcp_client.health_check():
            raise HTTPException(status_code=503, detail="MCP server is not available")

        if not request.task_description.strip():
            raise HTTPException(status_code=400, detail="Task description cannot be empty")

        result = await mcp_client.quick_assign(
            email=request.email.strip(),
            title=request.title,
            description=request.task_description,
            priority=request.priority
        )

        if result.get("success"):
            return {
                "success": True,
                "message": f"Task assigned to {request.email}",
                "details": result
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to assign task")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quick task assignment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mcp-status")
async def get_mcp_status():
    """Get MCP server status and health"""
    try:
        healthy = await mcp_client.health_check()
        return {
            "mcp_server_url": MCP_SERVER_URL,
            "status": "healthy" if healthy else "unhealthy",
            "last_checked": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "mcp_server_url": MCP_SERVER_URL,
            "status": "error",
            "error": str(e),
            "last_checked": datetime.now().isoformat()
        }


def run_frontend_server():
    """Run the frontend API server"""
    host = os.getenv('FRONTEND_API_HOST', '0.0.0.0')
    port = int(os.getenv('FRONTEND_API_PORT', '8001'))

    logger.info(f"Starting Frontend API Server on {host}:{port}")
    logger.info(f"MCP Server URL: {MCP_SERVER_URL}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=os.getenv('LOG_LEVEL', 'info').lower()
    )


if __name__ == "__main__":
    run_frontend_server()