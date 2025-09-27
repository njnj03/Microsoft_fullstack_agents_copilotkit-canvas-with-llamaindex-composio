"""
MCP Server for Task Distribution via Slack using Composio
Handles task creation and distribution to team members based on email IDs
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from composio import Composio
from openai import OpenAI
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
    title="Task Distribution MCP Server",
    description="MCP server for distributing tasks via Slack using Composio",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Composio and OpenAI
composio = Composio(api_key=os.getenv('COMPOSIO_API_KEY'))
openai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Configuration
USER_ID = os.getenv('COMPOSIO_USER_ID', 'default')
AUTH_CONFIG_ID = os.getenv('COMPOSIO_SLACKBOT_AUTH_CONFIG_ID', 'ac_PifaCardbZwt')

# Email to Slack user mapping (can be stored in database)
EMAIL_TO_SLACK_MAP = {
    # Add your team's email to Slack user mapping here
    # "john@example.com": "@john.doe",
    # "jane@example.com": "@jane.smith",
}


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(Enum):
    """Task status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class Task(BaseModel):
    """Task model"""
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Detailed task description")
    assignee_email: str = Field(..., description="Assignee's email address")
    priority: TaskPriority = Field(TaskPriority.NORMAL, description="Task priority")
    due_date: Optional[datetime] = Field(None, description="Task due date")
    project: Optional[str] = Field(None, description="Project name")
    tags: Optional[List[str]] = Field(None, description="Task tags")


class TaskBatch(BaseModel):
    """Batch of tasks to distribute"""
    tasks: List[Task] = Field(..., description="List of tasks to distribute")
    notify_channel: Optional[str] = Field(None, description="Channel to notify about task distribution")


class SlackTaskDistributor:
    """Handles task distribution via Slack"""

    def __init__(self):
        self.composio = composio
        self.openai = openai
        self.user_id = USER_ID
        self._ensure_connection()

    def _ensure_connection(self):
        """Ensure Slack is connected"""
        tools = self.composio.tools.get(user_id=self.user_id, toolkits=["SLACKBOT"])
        if not tools:
            logger.warning("Slack not connected. Please authenticate.")
            return False
        logger.info(f"Slack connected with {len(tools)} tools available")
        return True

    def get_slack_user(self, email: str) -> str:
        """Convert email to Slack user handle"""
        # Check mapping
        if email in EMAIL_TO_SLACK_MAP:
            return EMAIL_TO_SLACK_MAP[email]

        # Try to find user by email in Slack
        # For now, return email as username
        username = email.split('@')[0].replace('.', '_')
        return f"@{username}"

    def format_task_message(self, task: Task) -> Dict[str, Any]:
        """Format task as Slack message with blocks"""

        # Priority emoji mapping
        priority_emoji = {
            TaskPriority.LOW: "🟢",
            TaskPriority.NORMAL: "🔵",
            TaskPriority.HIGH: "🟡",
            TaskPriority.URGENT: "🔴"
        }

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📋 New Task: {task.title}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Description:*\n{task.description}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Priority:* {priority_emoji[task.priority]} {task.priority.value.capitalize()}"
                    }
                ]
            }
        ]

        # Add project if specified
        if task.project:
            blocks[2]["fields"].append({
                "type": "mrkdwn",
                "text": f"*Project:* {task.project}"
            })

        # Add due date if specified
        if task.due_date:
            blocks[2]["fields"].append({
                "type": "mrkdwn",
                "text": f"*Due Date:* {task.due_date.strftime('%Y-%m-%d %H:%M')}"
            })

        # Add tags if specified
        if task.tags:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Tags:* {', '.join(task.tags)}"
                }
            })

        # Add action buttons
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Accept Task"
                    },
                    "style": "primary",
                    "action_id": "accept_task"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View Details"
                    },
                    "action_id": "view_details"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Mark Complete"
                    },
                    "style": "primary",
                    "action_id": "complete_task"
                }
            ]
        })

        return {
            "text": f"New task assigned: {task.title}",
            "blocks": blocks
        }

    async def send_task_to_user(self, task: Task) -> bool:
        """Send task to a specific user via Slack DM"""
        try:
            slack_user = self.get_slack_user(task.assignee_email)
            message = self.format_task_message(task)

            # Get Slack tools
            tools = self.composio.tools.get(user_id=self.user_id, toolkits=["SLACKBOT"])

            # Create task message
            task_text = f"Send a direct message to {slack_user} with this task information: {message['text']}"

            # Use OpenAI to send
            completion = self.openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a task distribution bot. Send the task to the specified user."
                    },
                    {
                        "role": "user",
                        "content": task_text
                    }
                ],
                tools=tools
            )

            # Execute
            result = self.composio.provider.handle_tool_calls(
                user_id=self.user_id,
                response=completion
            )

            logger.info(f"Task sent to {slack_user} ({task.assignee_email})")
            return True

        except Exception as e:
            logger.error(f"Failed to send task to {task.assignee_email}: {e}")
            return False

    async def distribute_tasks(self, tasks: List[Task], notify_channel: Optional[str] = None) -> Dict:
        """Distribute multiple tasks to team members"""
        results = {
            "total": len(tasks),
            "successful": 0,
            "failed": 0,
            "details": []
        }

        for task in tasks:
            success = await self.send_task_to_user(task)

            if success:
                results["successful"] += 1
                results["details"].append({
                    "assignee": task.assignee_email,
                    "title": task.title,
                    "status": "sent"
                })
            else:
                results["failed"] += 1
                results["details"].append({
                    "assignee": task.assignee_email,
                    "title": task.title,
                    "status": "failed"
                })

        # Send summary to channel if specified
        if notify_channel and results["successful"] > 0:
            await self.send_summary_to_channel(notify_channel, results)

        return results

    async def send_summary_to_channel(self, channel: str, results: Dict):
        """Send task distribution summary to a channel"""
        try:
            tools = self.composio.tools.get(user_id=self.user_id, toolkits=["SLACKBOT"])

            summary = f"""
📊 Task Distribution Summary:
• Total tasks: {results['total']}
• Successfully distributed: {results['successful']}
• Failed: {results['failed']}
            """

            completion = self.openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": f"Send to Slack channel #{channel}: {summary}"
                    }
                ],
                tools=tools
            )

            self.composio.provider.handle_tool_calls(
                user_id=self.user_id,
                response=completion
            )

            logger.info(f"Summary sent to #{channel}")

        except Exception as e:
            logger.error(f"Failed to send summary: {e}")


# Initialize distributor
distributor = SlackTaskDistributor()


# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Task Distribution MCP",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/tasks/create")
async def create_task(task: Task, background_tasks: BackgroundTasks):
    """Create and distribute a single task"""
    try:
        success = await distributor.send_task_to_user(task)

        if success:
            return {
                "success": True,
                "message": f"Task sent to {task.assignee_email}",
                "task_id": f"task_{datetime.now().timestamp()}"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to send task")

    except Exception as e:
        logger.error(f"Task creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tasks/batch")
async def create_task_batch(batch: TaskBatch, background_tasks: BackgroundTasks):
    """Create and distribute multiple tasks"""
    try:
        results = await distributor.distribute_tasks(
            batch.tasks,
            batch.notify_channel
        )

        return {
            "success": True,
            "results": results
        }

    except Exception as e:
        logger.error(f"Batch task creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tasks/assign")
async def quick_assign_task(
    email: str,
    title: str,
    description: str,
    priority: str = "normal"
):
    """Quick endpoint to assign a task"""
    task = Task(
        title=title,
        description=description,
        assignee_email=email,
        priority=TaskPriority(priority)
    )

    success = await distributor.send_task_to_user(task)

    if success:
        return {"success": True, "message": f"Task assigned to {email}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to assign task")


@app.get("/users/mapping")
async def get_user_mapping():
    """Get current email to Slack user mapping"""
    return {
        "mapping": EMAIL_TO_SLACK_MAP,
        "count": len(EMAIL_TO_SLACK_MAP)
    }


@app.post("/users/mapping")
async def update_user_mapping(email: str, slack_user: str):
    """Update email to Slack user mapping"""
    EMAIL_TO_SLACK_MAP[email] = slack_user
    return {
        "success": True,
        "message": f"Mapping updated: {email} -> {slack_user}"
    }


def run_server():
    """Run the MCP server"""
    host = os.getenv('MCP_SERVER_HOST', '127.0.0.1')
    port = 8080

    logger.info(f"Starting Task Distribution MCP Server on {host}:{port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=os.getenv('LOG_LEVEL', 'info').lower()
    )


if __name__ == "__main__":
    run_server()