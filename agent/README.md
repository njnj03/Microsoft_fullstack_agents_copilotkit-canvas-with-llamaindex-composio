# 🚀 Composio MCP Slack Task Distribution System

A production-ready **Model Context Protocol (MCP)** server that automatically distributes tasks to team members via **Slack Direct Messages** using **Composio** integration. Simply provide email addresses, and the system handles the rest!

## 🎯 What This Does

- **📧 Email → Slack**: Send tasks to `john@company.com` → automatically delivered to `@john` in Slack
- **🤖 AI-Powered**: Uses OpenAI + Composio for intelligent message routing
- **💬 Rich Messages**: Beautiful Slack messages with priorities, due dates, and action buttons
- **⚡ Instant Delivery**: Tasks appear in Slack DMs immediately
- **📊 Batch Processing**: Distribute multiple tasks at once

## 🏗️ Architecture

```
Your App/Script → MCP Server → Composio → Slack API → Team Members' DMs
```

**Key Components:**
- **MCP Server**: FastAPI server handling task distribution
- **Composio**: Third-party service managing Slack integration
- **OpenAI**: AI model for message routing and formatting
- **Slack Bot**: Authenticated bot delivering messages

## 📁 Project Structure

```
agent/
├── agent/
│   ├── __init__.py                    # Package entry point
│   ├── task_distribution_mcp.py       # 🔥 Main MCP server
│   ├── agent.py                       # Additional agent logic
│   └── server.py                      # Original server
├── test_akshat.py                     # ✅ Test script (working example)
├── mcp_client.py                      # 📝 Client usage examples
├── .env                               # 🔐 Environment credentials
├── README_TASK_MCP.md                 # 📚 Detailed technical docs
└── README.md                          # 👋 This file
```

## ⚡ Quick Start

### 1. Prerequisites

- Python 3.8+
- Slack workspace admin access
- OpenAI API key
- Composio account

### 2. Setup Environment

Your `.env` file should contain:

```bash
# OpenAI API Key
OPENAI_API_KEY=sk-proj-your-key-here

# Composio Configuration
COMPOSIO_API_KEY=ak_your-composio-key
COMPOSIO_USER_ID=default
COMPOSIO_SLACKBOT_AUTH_CONFIG_ID=ac_your-auth-config

# Slack Bot Token
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token

# Server Configuration
MCP_SERVER_HOST=127.0.0.1
MCP_SERVER_PORT=8000
```

### 3. Install Dependencies

```bash
# Activate your Python environment
pyenv activate mcp-slack  # or your preferred method

# Install required packages
pip install composio-core openai python-dotenv fastapi uvicorn requests
```

### 4. Start the MCP Server

```bash
python -m agent.task_distribution_mcp
```

Server starts at: `http://localhost:8000`

### 5. Send Your First Task

```python
import requests

# Create a task
task = {
    "title": "Review Q4 Report",
    "description": "Please review the quarterly report by EOD",
    "assignee_email": "teammate@company.com",
    "priority": "high",
    "due_date": "2024-01-15T17:00:00",
    "project": "Finance"
}

# Send via MCP server
response = requests.post("http://localhost:8000/tasks/create", json=task)
print(response.json())
```

**Result:** Your teammate receives a beautifully formatted task in their Slack DMs! 🎉

## 🧪 Test the System

We've included a working test script:

```bash
python test_akshat.py
```

This will:
1. ✅ Test direct Composio connection
2. ✅ Send message to akshat@futurepath.ai
3. ✅ Test MCP server endpoints
4. ✅ Demonstrate batch task distribution

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Check server status |
| `/tasks/create` | POST | Send single task |
| `/tasks/batch` | POST | Send multiple tasks |
| `/tasks/assign` | POST | Quick task assignment |
| `/users/mapping` | GET/POST | Manage email→Slack mappings |

## 💬 Message Format

Tasks appear in Slack as rich, interactive messages:

```
📋 New Task: Review Q4 Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Description: Please review the quarterly report by EOD

Priority: 🔴 High          Project: Finance
Due Date: 2024-01-15 17:00

Tags: urgent, finance, review

[Accept Task] [View Details] [Mark Complete]
```

## 🔧 Configuration

### Email to Slack Mapping

The system automatically converts emails to Slack usernames, but you can set custom mappings:

```python
# Update mapping via API
requests.post("http://localhost:8000/users/mapping", params={
    "email": "john@company.com",
    "slack_user": "@john.doe"
})
```

### Priority Levels

- 🟢 **Low**: Non-urgent tasks
- 🔵 **Normal**: Regular priority (default)
- 🟡 **High**: Important tasks
- 🔴 **Urgent**: Immediate attention required

## 🎯 Use Cases

### Single Task Assignment
```bash
curl -X POST "http://localhost:8000/tasks/assign" \
  -d "email=developer@company.com" \
  -d "title=Code Review" \
  -d "description=Review PR #123" \
  -d "priority=high"
```

### Batch Task Distribution
```python
batch = {
    "tasks": [
        {
            "title": "Update Documentation",
            "assignee_email": "writer@company.com",
            "priority": "normal"
        },
        {
            "title": "Security Audit",
            "assignee_email": "security@company.com",
            "priority": "urgent"
        }
    ],
    "notify_channel": "team-updates"  # Optional summary
}

requests.post("http://localhost:8000/tasks/batch", json=batch)
```

## 🛠️ How It Works

1. **Task Creation**: You send a task with an email address
2. **Email Mapping**: System converts email to Slack username
3. **AI Processing**: OpenAI formats the task message
4. **Composio Integration**: Routes message through Slack API
5. **Direct Delivery**: Task appears in recipient's Slack DMs
6. **Rich Formatting**: Slack renders interactive message blocks

## 🔐 Security & Production

- ✅ **Environment Variables**: All credentials in `.env` (never committed)
- ✅ **CORS Enabled**: API accessible from web applications
- ✅ **Error Handling**: Comprehensive error responses
- ✅ **Logging**: Detailed request/response logging
- ✅ **Background Tasks**: Non-blocking task distribution

For production deployment:
- Add authentication to API endpoints
- Store mappings in database
- Enable HTTPS
- Add rate limiting
- Set up monitoring

## 🚨 Troubleshooting

**Tasks not appearing in Slack?**
- Verify Slack bot is added to workspace
- Check recipient has DMs enabled
- Ensure email mapping is correct
- View server logs for errors

**Authentication issues?**
- Verify all API keys in `.env`
- Check Composio account status
- Ensure Slack bot permissions

**Server won't start?**
- Check port 8000 is available
- Verify Python environment
- Install missing dependencies

## 📚 Additional Resources

- **Detailed Technical Docs**: See `README_TASK_MCP.md`
- **Example Client**: Check `mcp_client.py`
- **Test Script**: Run `test_akshat.py`
- **Composio Docs**: [composio.dev](https://composio.dev)

## ✨ Features

- **🎯 Email-Based**: Just provide email addresses
- **⚡ Instant**: Messages delivered immediately
- **📱 Mobile-Ready**: Works on Slack mobile apps
- **🔄 Batch Processing**: Handle multiple tasks efficiently
- **📊 Channel Notifications**: Optional team summaries
- **🎨 Rich Formatting**: Beautiful, interactive messages
- **🔐 Secure**: Encrypted API communications
- **📈 Scalable**: Handle high-volume task distribution

---

**🎉 Ready to distribute tasks to your team via Slack?**

Start the server: `python -m agent.task_distribution_mcp`

Send a test: `python test_akshat.py`

Your team will love getting tasks directly in their Slack DMs! 🚀
