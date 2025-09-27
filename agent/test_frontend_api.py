#!/usr/bin/env python
"""
Test script for the Frontend API
Demonstrates how to use the API from a frontend application
"""

import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Frontend API URL
FRONTEND_API_URL = os.getenv('FRONTEND_API_URL', 'http://localhost:8001')

# Test configuration - Using real email addresses for testing
TEST_EMAILS = [
    'ydishajadav12402@gmail.com',  # Replace with your actual email
    'akshat@futurepath.ai',    # Replace with your teammate's email
]


def test_health():
    """Test health endpoint"""
    print("=" * 50)
    print("Testing Health Check")
    print("=" * 50)

    try:
        response = requests.get(f"{FRONTEND_API_URL}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Health check failed: {e}")


def test_distribute_tasks():
    """Test task distribution to multiple emails"""
    print("\n" + "=" * 50)
    print("Testing Task Distribution")
    print("=" * 50)

    # Example request from frontend
    task_request = {
        "email_ids": TEST_EMAILS,
        "task_text": "Please review the Q4 financial report and provide your feedback by end of day. Focus on revenue trends and cost analysis.",
        "title": "Q4 Financial Report Review",
        "priority": "high",
        "project": "Finance Review",
        "notify_channel": "general"
    }

    try:
        response = requests.post(
            f"{FRONTEND_API_URL}/distribute-tasks",
            json=task_request
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Task distribution failed: {e}")


def test_quick_assign():
    """Test quick task assignment"""
    print("\n" + "=" * 50)
    print("Testing Quick Assignment")
    print("=" * 50)

    quick_request = {
        "email": TEST_EMAILS[0],
        "task_description": "Update the project documentation with the latest API changes",
        "title": "Documentation Update",
        "priority": "normal"
    }

    try:
        response = requests.post(
            f"{FRONTEND_API_URL}/quick-assign",
            json=quick_request
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Quick assignment failed: {e}")


def test_mcp_status():
    """Test MCP server status"""
    print("\n" + "=" * 50)
    print("Testing MCP Status")
    print("=" * 50)

    try:
        response = requests.get(f"{FRONTEND_API_URL}/mcp-status")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"MCP status check failed: {e}")


def main():
    """Run all tests"""
    print("🚀 Testing Frontend API for Task Distribution")
    print(f"Frontend API URL: {FRONTEND_API_URL}")
    print(f"Test started at: {datetime.now()}")
    print(f"Using test emails: {', '.join(TEST_EMAILS)}")

    # Test all endpoints
    test_health()
    test_mcp_status()
    test_distribute_tasks()
    test_quick_assign()

    print("\n" + "=" * 50)
    print("✅ All tests completed!")
    print("=" * 50)

    print("\n📋 Frontend Integration Examples:")
    print("\n1. JavaScript/React Example:")
    print("""
// Distribute tasks to multiple team members
const distributeTask = async () => {
  const response = await fetch('http://localhost:8001/distribute-tasks', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email_ids: ['user1@company.com', 'user2@company.com'],
      task_text: 'Complete the project review by Friday',
      title: 'Weekly Review',
      priority: 'high',
      notify_channel: 'team-updates'
    })
  });

  const result = await response.json();
  console.log('Distribution result:', result);
};
""")

    print("\n2. cURL Example:")
    print("""
curl -X POST "http://localhost:8001/distribute-tasks" \\
     -H "Content-Type: application/json" \\
     -d '{
       "email_ids": ["user1@company.com", "user2@company.com"],
       "task_text": "Please review and test the new feature",
       "title": "Feature Review",
       "priority": "normal"
     }'
""")


if __name__ == "__main__":
    main()