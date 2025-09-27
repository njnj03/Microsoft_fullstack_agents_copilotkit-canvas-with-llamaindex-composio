# Task Distribution MCP Server with Composio Slack Integration

## 🚀 Overview

A production-ready MCP (Model Context Protocol) server that distributes tasks to team members via Slack DMs based on their email addresses. Uses Composio for Slack integration and OpenAI for intelligent message routing.

## ✨ Features

- **Email-based Task Distribution**: Send tasks to team members using just their email addresses
- **Automatic Slack User Mapping**: Converts emails to Slack usernames
- **Rich Task Formatting**: Beautiful Slack messages with priority indicators, due dates, and action buttons
- **Batch Processing**: Distribute multiple tasks at once
- **Channel Notifications**: Optional summary notifications to team channels
- **RESTful API**: Easy integration with any system

## 📁 Clean File Structure

```
agent/
├── agent/
│   ├── __init__.py              # Main entry point
│   ├── task_distribution_mcp.py # Task distribution MCP server
│   ├── agent.py                 # Existing agent logic
│   └── server.py                 # Main server
├── mcp_client.py                 # Example client script
├── .env                          # Environment configuration
└── README_TASK_MCP.md           # This file
```

## 🔧 Configuration

Your `.env` file is already configured with:

```env
# OpenAI
OPENAI_API_KEY=sk-proj-p7tZ0_...  # ✅ Configured

# Composio
COMPOSIO_API_KEY=ak_1SJC1krF-19U_NTcON_V  # ✅ Configured
COMPOSIO_USER_ID=default
COMPOSIO_SLACKBOT_AUTH_CONFIG_ID=ac_PifaCardbZwt  # ✅ Configured

# Slack
SLACK_BOT_TOKEN=<REDACTED_SLACK_BOT_TOKEN>  # ✅ Configured

# MCP Server
MCP_SERVER_HOST=127.0.0.1
MCP_SERVER_PORT=8000
```

## 🚀 Usage

### 1. Start the MCP Server

```bash
python -m agent.task_distribution_mcp
```

Server runs at `http://localhost:8000`

### 2. Create a Single Task

```python
POST /tasks/create

{
  "title": "Review Q4 Report",
  "description": "Please review the Q4 financial report",
  "assignee_email": "john@example.com",
  "priority": "high",
  "due_date": "2024-01-15T17:00:00",
  "project": "Finance",
  "tags": ["urgent", "q4"]
}
```

### 3. Distribute Multiple Tasks

```python
POST /tasks/batch

{
  "tasks": [
    {
      "title": "Update Documentation",
      "description": "Update API docs",
      "assignee_email": "dev@example.com",
      "priority": "normal"
    },
    {
      "title": "Security Audit",
      "description": "Audit auth module",
      "assignee_email": "security@example.com",
      "priority": "urgent"
    }
  ],
  "notify_channel": "team-updates"
}
```

### 4. Quick Assignment

```python
POST /tasks/assign?email=intern@example.com&title=Code Review&description=Review PR 123&priority=normal
```

## 📊 Task Message Format

Tasks appear in Slack as rich formatted messages:

```
📋 New Task: [Title]
━━━━━━━━━━━━━━━━━━━━━
Description: [Task details]

Priority: 🔴 Urgent
Project: [Project Name]
Due Date: 2024-01-15 17:00
Tags: urgent, review

[Accept Task] [View Details] [Mark Complete]
```

## 🔄 Email to Slack Mapping

### Update Mapping
```python
POST /users/mapping?email=john@example.com&slack_user=@john.doe
```

### View Current Mappings
```python
GET /users/mapping
```

## 📝 Example Client Usage

```python
import requests

# MCP Server URL
url = "http://localhost:8000"

# Create a task
task = {
    "title": "Review Code",
    "description": "Review the latest PR",
    "assignee_email": "developer@company.com",
    "priority": "high"
}

response = requests.post(f"{url}/tasks/create", json=task)
print(response.json())
```

## 🧪 Testing

Run the example client:

```bash
python mcp_client.py
```

This will:
1. Check server health
2. Update user mappings
3. Create single task
4. Create batch tasks
5. Quick assign a task

## 🔍 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/tasks/create` | POST | Create single task |
| `/tasks/batch` | POST | Create multiple tasks |
| `/tasks/assign` | POST | Quick task assignment |
| `/users/mapping` | GET | View email mappings |
| `/users/mapping` | POST | Update email mapping |

## 🎯 Priority Levels

- 🟢 **Low**: Non-urgent tasks
- 🔵 **Normal**: Regular priority
- 🟡 **High**: Important tasks
- 🔴 **Urgent**: Immediate attention required

## 🚨 Troubleshooting

1. **Tasks not appearing in Slack**:
   - Ensure bot is in workspace
   - Check user has DMs enabled
   - Verify email mapping is correct

2. **Authentication issues**:
   - Verify Composio API key
   - Check Slack bot token
   - Ensure OpenAI key is valid

3. **Connection errors**:
   - Make sure MCP server is running
   - Check port 8000 is available

## 🔐 Security

- All credentials stored in `.env` (never commit!)
- Email mappings can be stored in database
- Rate limiting can be added
- Authentication can be added to endpoints

## 📈 Production Deployment

For production:
1. Add authentication to endpoints
2. Store email mappings in database
3. Add rate limiting
4. Enable HTTPS
5. Add monitoring/logging
6. Use environment-specific configs

## ✅ Summary

This clean implementation provides:
- **Simple task distribution** via email addresses
- **Composio integration** for Slack messaging
- **Clean code structure** with minimal files
- **Production-ready** error handling
- **RESTful API** for easy integration

Just update the email mappings and start distributing tasks to your team!