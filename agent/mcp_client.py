#!/usr/bin/env python
"""
MCP Client for Task Distribution
Example script showing how to use the MCP server
"""

import requests
import json
from datetime import datetime, timedelta

# MCP Server URL
MCP_SERVER_URL = "http://localhost:8000"


def create_single_task():
    """Example: Create a single task"""
    task = {
        "title": "Review Q4 Report",
        "description": "Please review the Q4 financial report and provide feedback by EOD",
        "assignee_email": "john@example.com",
        "priority": "high",
        "due_date": (datetime.now() + timedelta(days=2)).isoformat(),
        "project": "Finance",
        "tags": ["urgent", "finance", "q4"]
    }

    response = requests.post(
        f"{MCP_SERVER_URL}/tasks/create",
        json=task
    )

    print("Single Task Creation:")
    print(json.dumps(response.json(), indent=2))


def create_batch_tasks():
    """Example: Create multiple tasks at once"""
    batch = {
        "tasks": [
            {
                "title": "Update Documentation",
                "description": "Update API documentation for new endpoints",
                "assignee_email": "developer@example.com",
                "priority": "normal",
                "project": "API",
                "tags": ["documentation"]
            },
            {
                "title": "Security Audit",
                "description": "Conduct security audit for user authentication module",
                "assignee_email": "security@example.com",
                "priority": "urgent",
                "project": "Security",
                "tags": ["security", "audit"]
            },
            {
                "title": "Client Meeting Prep",
                "description": "Prepare presentation for client meeting on Friday",
                "assignee_email": "sales@example.com",
                "priority": "high",
                "due_date": (datetime.now() + timedelta(days=3)).isoformat(),
                "project": "Sales"
            }
        ],
        "notify_channel": "team-updates"  # Optional: notify a channel about the distribution
    }

    response = requests.post(
        f"{MCP_SERVER_URL}/tasks/batch",
        json=batch
    )

    print("\nBatch Task Creation:")
    print(json.dumps(response.json(), indent=2))


def quick_assign():
    """Example: Quick task assignment"""
    params = {
        "email": "intern@example.com",
        "title": "Code Review",
        "description": "Review PR #123 for the new feature implementation",
        "priority": "normal"
    }

    response = requests.post(
        f"{MCP_SERVER_URL}/tasks/assign",
        params=params
    )

    print("\nQuick Assignment:")
    print(json.dumps(response.json(), indent=2))


def update_user_mapping():
    """Example: Update email to Slack user mapping"""
    mapping_data = {
        "email": "john@example.com",
        "slack_user": "@john.doe"
    }

    response = requests.post(
        f"{MCP_SERVER_URL}/users/mapping",
        params=mapping_data
    )

    print("\nUser Mapping Update:")
    print(json.dumps(response.json(), indent=2))


def check_health():
    """Check MCP server health"""
    response = requests.get(f"{MCP_SERVER_URL}/health")
    print("\nHealth Check:")
    print(json.dumps(response.json(), indent=2))


def main():
    """Run all examples"""
    print("=" * 60)
    print("MCP Task Distribution Client Examples")
    print("=" * 60)

    try:
        # Check server health
        check_health()

        # Update user mappings
        print("\n1. Updating user mappings...")
        update_user_mapping()

        # Create single task
        print("\n2. Creating single task...")
        create_single_task()

        # Create batch tasks
        print("\n3. Creating batch tasks...")
        create_batch_tasks()

        # Quick assign
        print("\n4. Quick task assignment...")
        quick_assign()

    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to MCP server at", MCP_SERVER_URL)
        print("Make sure the server is running: python -m agent.task_distribution_mcp")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()