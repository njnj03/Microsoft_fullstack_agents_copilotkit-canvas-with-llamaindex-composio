# 🚀 Task Distribution API - Frontend Integration Guide

Simple guide for frontend developers to integrate with the task distribution system that sends tasks to team members via Slack.

## 📝 Overview

This API allows your frontend to distribute tasks to team members by sending them directly to their Slack DMs. Perfect for project management, task assignment, and team coordination.

## 🔗 Base URL

```
http://localhost:8001
```

## 🎯 Main Endpoint: Distribute Tasks

### `POST /distribute-tasks`

Sends the same task to multiple team members via Slack.

**Request:**
```javascript
fetch('http://localhost:8001/distribute-tasks', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    "email_ids": ["user1@company.com", "user2@company.com"],
    "task_text": "Please review the Q4 report and provide feedback by Friday",
    "title": "Q4 Report Review",
    "priority": "high",
    "project": "Finance Review",
    "notify_channel": "team-updates"
  })
})
```

**Response:**
```json
{
  "success": true,
  "message": "Tasks distributed successfully to 2 team members",
  "total_tasks": 2,
  "successful_assignments": 2,
  "failed_assignments": 0,
  "details": [
    {
      "assignee": "user1@company.com",
      "title": "Q4 Report Review",
      "status": "sent"
    }
  ]
}
```

## ⚡ Quick Assignment Endpoint

### `POST /quick-assign`

Quickly assign a task to a single team member.

**Request:**
```javascript
fetch('http://localhost:8001/quick-assign', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    "email": "developer@company.com",
    "task_description": "Update the API documentation",
    "title": "Documentation Update",
    "priority": "normal"
  })
})
```

## 📋 Request Parameters

### Required Fields
- `email_ids` (array): List of team member email addresses
- `task_text` (string): The task description/instructions

### Optional Fields
- `title` (string): Task title (default: "Task Assignment")
- `priority` (string): "low", "normal", "high", "urgent" (default: "normal")
- `project` (string): Project name
- `notify_channel` (string): Slack channel for notifications

## 🛠️ Complete React Example

```jsx
import React, { useState } from 'react';

const TaskDistributor = () => {
  const [emails, setEmails] = useState('');
  const [taskText, setTaskText] = useState('');
  const [title, setTitle] = useState('');
  const [priority, setPriority] = useState('normal');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    const emailList = emails.split(',').map(email => email.trim());

    try {
      const response = await fetch('http://localhost:8001/distribute-tasks', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email_ids: emailList,
          task_text: taskText,
          title: title || 'Task Assignment',
          priority: priority,
          notify_channel: 'general'
        })
      });

      const data = await response.json();
      setResult(data);

      if (data.success) {
        alert(`✅ Tasks sent to ${data.successful_assignments} team members!`);
        // Reset form
        setEmails('');
        setTaskText('');
        setTitle('');
      } else {
        alert(`❌ Failed to distribute tasks: ${data.message}`);
      }

    } catch (error) {
      console.error('Error:', error);
      alert('❌ Network error occurred');
    }

    setLoading(false);
  };

  return (
    <div style={{ maxWidth: '600px', margin: '20px auto', padding: '20px' }}>
      <h2>📋 Distribute Tasks to Team</h2>

      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '15px' }}>
          <label>📧 Team Member Emails (comma separated):</label>
          <input
            type="text"
            value={emails}
            onChange={(e) => setEmails(e.target.value)}
            placeholder="user1@company.com, user2@company.com"
            style={{ width: '100%', padding: '8px', marginTop: '5px' }}
            required
          />
        </div>

        <div style={{ marginBottom: '15px' }}>
          <label>📝 Task Title:</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Enter task title"
            style={{ width: '100%', padding: '8px', marginTop: '5px' }}
          />
        </div>

        <div style={{ marginBottom: '15px' }}>
          <label>📄 Task Description:</label>
          <textarea
            value={taskText}
            onChange={(e) => setTaskText(e.target.value)}
            placeholder="Enter detailed task description and instructions"
            rows={4}
            style={{ width: '100%', padding: '8px', marginTop: '5px' }}
            required
          />
        </div>

        <div style={{ marginBottom: '15px' }}>
          <label>🚨 Priority:</label>
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            style={{ width: '100%', padding: '8px', marginTop: '5px' }}
          >
            <option value="low">🟢 Low</option>
            <option value="normal">🔵 Normal</option>
            <option value="high">🟡 High</option>
            <option value="urgent">🔴 Urgent</option>
          </select>
        </div>

        <button
          type="submit"
          disabled={loading}
          style={{
            backgroundColor: '#007bff',
            color: 'white',
            padding: '12px 24px',
            border: 'none',
            borderRadius: '4px',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          {loading ? '⏳ Distributing...' : '🚀 Distribute Tasks'}
        </button>
      </form>

      {result && (
        <div style={{
          marginTop: '20px',
          padding: '15px',
          backgroundColor: result.success ? '#d4edda' : '#f8d7da',
          border: `1px solid ${result.success ? '#c3e6cb' : '#f5c6cb'}`,
          borderRadius: '4px'
        }}>
          <p>{result.message}</p>
          {result.success && (
            <p>✅ Successfully sent to {result.successful_assignments} out of {result.total_tasks} team members</p>
          )}
        </div>
      )}
    </div>
  );
};

export default TaskDistributor;
```

## 🔍 Health Check

Check if the API is running:

```javascript
const checkHealth = async () => {
  try {
    const response = await fetch('http://localhost:8001/health');
    const data = await response.json();
    console.log('API Status:', data.status);
    console.log('Slack Connected:', data.mcp_server === 'connected');
  } catch (error) {
    console.error('API is not running');
  }
};
```

## 📱 What Happens in Slack?

When you send a task, team members receive:
- 📬 **Direct message** from the Slack bot
- 🎨 **Rich formatted card** with task details
- 🔘 **Interactive buttons**: "Accept Task", "View Details", "Mark Complete"
- 🏷️ **Priority indicators**: 🟢🔵🟡🔴
- 📅 **Project and deadline info** (if provided)

## 🧪 Testing

Test the API with sample data:

```bash
curl -X POST "http://localhost:8001/distribute-tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "email_ids": ["test@company.com"],
    "task_text": "This is a test message to verify the integration",
    "title": "API Integration Test",
    "priority": "normal"
  }'
```

## ❗ Error Handling

Always check the response:

```javascript
const response = await fetch('http://localhost:8001/distribute-tasks', {
  // ... request config
});

if (!response.ok) {
  throw new Error(`HTTP error! status: ${response.status}`);
}

const data = await response.json();

if (!data.success) {
  console.error('Task distribution failed:', data.message);
  // Handle failure
} else {
  console.log(`✅ Success! ${data.successful_assignments} tasks sent`);
  // Handle success
}
```

## 🚨 Common Issues

1. **CORS Error**: Make sure you're calling the correct URL (`http://localhost:8001`)
2. **500 Error**: Check if the backend servers are running
3. **No Slack Messages**: Verify email addresses are correct and bot is configured
4. **Connection Refused**: Ensure the API server is started

## 📞 Support

If you encounter issues:
1. Check the API health endpoint first
2. Verify the backend servers are running
3. Test with a simple cURL command
4. Check browser console for detailed error messages

---

🎉 **You're ready to integrate! The API will handle sending formatted task notifications directly to your team's Slack DMs.**