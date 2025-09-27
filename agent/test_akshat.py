#!/usr/bin/env python
"""
Test script to send tasks to team members via Slack
"""

import requests
import json
from datetime import datetime, timedelta
from composio import Composio
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# MCP Server URL
MCP_SERVER_URL = "http://localhost:8000"

# Direct Composio/OpenAI approach for immediate testing
composio = Composio(api_key=os.getenv('COMPOSIO_API_KEY'))
openai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
USER_ID = "default"


def send_direct_slack_message():
    """Send direct messages using Composio (works immediately)"""
    print("=" * 60)
    print("Sending Direct Slack Messages to Team")
    print("=" * 60)

    try:
        # Get Slack tools
        tools = composio.tools.get(user_id=USER_ID, toolkits=["SLACKBOT"])

        if not tools:
            print("❌ No Slack tools available. Please authenticate first.")
            return False

        print(f"✅ Loaded {len(tools)} Slack tools")

        # Test recipients
        recipients = [
            {"name": "Akshat", "username": "@akshat"},
            {"name": "Tanya", "username": "@tanyapragnesh.shah"}
        ]

        success_count = 0

        for recipient in recipients:
            print(f"\n📨 Sending message to {recipient['name']}...")

            # Create personalized message
            message = f"""
Hi {recipient['name']}! 👋

This is a test message from the Task Distribution Bot. The integration is working!

📋 *Sample Task Assignment*:
• Task: Review Task Distribution System
• Priority: High
• Due: End of day
• Project: MCP Integration

The bot can now:
✅ Send tasks to team members via email
✅ Format messages with rich Slack blocks
✅ Handle batch task distribution
✅ Track task priorities and due dates

Let me know if you receive this message!

Best,
Task Bot 🤖
            """

            try:
                # Send via OpenAI + Composio
                task = f"Send a direct message to {recipient['username']} on Slack with this message: {message}"

                completion = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a task distribution bot. Send the message exactly as provided."
                        },
                        {
                            "role": "user",
                            "content": task
                        }
                    ],
                    tools=tools
                )

                # Execute
                result = composio.provider.handle_tool_calls(
                    user_id=USER_ID,
                    response=completion
                )

                print(f"   ✅ Message sent successfully to {recipient['name']}!")
                success_count += 1

            except Exception as e:
                print(f"   ❌ Failed to send to {recipient['name']}: {e}")

        print(f"\n✅ Messages sent to {success_count}/{len(recipients)} recipients!")
        return success_count > 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def send_task_via_mcp():
    """Send tasks to team members via MCP server"""
    print("\n" + "=" * 60)
    print("Sending Tasks via MCP Server")
    print("=" * 60)

    # Update email mappings for both team members
    email_mappings = [
        {"email": "akshat@futurepath.ai", "slack_user": "@akshat", "name": "Akshat"},
        {"email": "tanyapragnesh.shah@sjsu.edu", "slack_user": "@tanyapragnesh.shah", "name": "Tanya"}
    ]

    print("1. Updating email mappings...")
    for mapping in email_mappings:
        print(f"   📧 Mapping {mapping['email']} → {mapping['slack_user']}")

        mapping_response = requests.post(
            f"{MCP_SERVER_URL}/users/mapping",
            params={
                "email": mapping["email"],
                "slack_user": mapping["slack_user"]
            }
        )

        if mapping_response.status_code == 200:
            print(f"   ✅ {mapping['name']} mapping updated")
        else:
            print(f"   ❌ Failed to update {mapping['name']} mapping")

    # Create tasks for both team members
    print("\n2. Creating individual tasks...")

    tasks = [
        {
            "email": "akshat@futurepath.ai",
            "name": "Akshat",
            "task": {
                "title": "Review Task Distribution System",
                "description": """Please review the new task distribution system implementation:

1. Check the MCP server endpoints
2. Verify Slack message formatting
3. Test batch task distribution
4. Review error handling

The system uses Composio for Slack integration and can distribute tasks based on email addresses.""",
                "assignee_email": "akshat@futurepath.ai",
                "priority": "high",
                "due_date": (datetime.now() + timedelta(days=1)).isoformat(),
                "project": "MCP Integration",
                "tags": ["review", "mcp", "slack", "composio"]
            }
        },
        {
            "email": "tanyapragnesh.shah@sjsu.edu",
            "name": "Tanya",
            "task": {
                "title": "Test Task Distribution Integration",
                "description": """Please test the new task distribution system:

1. Verify you receive this message in Slack
2. Test the interactive buttons
3. Check message formatting
4. Provide feedback on user experience

This is a working Composio MCP integration for team task distribution.""",
                "assignee_email": "tanyapragnesh.shah@sjsu.edu",
                "priority": "normal",
                "due_date": (datetime.now() + timedelta(days=2)).isoformat(),
                "project": "MCP Testing",
                "tags": ["testing", "integration", "feedback"]
            }
        }
    ]

    success_count = 0
    for item in tasks:
        print(f"\n   📋 Creating task for {item['name']}...")

        try:
            response = requests.post(
                f"{MCP_SERVER_URL}/tasks/create",
                json=item["task"]
            )

            if response.status_code == 200:
                print(f"   ✅ Task sent to {item['name']}!")
                success_count += 1
            else:
                print(f"   ❌ Failed to send task to {item['name']}: {response.status_code}")
                print(f"   Error: {response.text}")

        except Exception as e:
            print(f"   ❌ Error sending to {item['name']}: {e}")

    print(f"\n✅ Tasks sent to {success_count}/{len(tasks)} recipients!")

    try:
        return success_count > 0
    except requests.exceptions.ConnectionError:
        print("   ❌ MCP Server is not running")
        print("   Start it with: python -m agent.task_distribution_mcp")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def send_batch_tasks():
    """Send multiple tasks including one for Akshat"""
    print("\n" + "=" * 60)
    print("Sending Batch Tasks")
    print("=" * 60)

    batch = {
        "tasks": [
            {
                "title": "Code Review: Task Distribution",
                "description": "Review the task distribution implementation",
                "assignee_email": "tanyapragnesh.shah@sjsu.edu",
                "priority": "high",
                "project": "MCP",
                "tags": ["code-review"]
            },
            {
                "title": "Documentation Update",
                "description": "Update README with latest features",
                "assignee_email": "tanyapragnesh.shah@sjsu.edu",
                "priority": "normal",
                "project": "MCP"
            },
            {
                "title": "Testing Integration",
                "description": "Test Slack integration thoroughly",
                "assignee_email": "tanyapragnesh.shah@sjsu.edu",
                "priority": "high",
                "project": "MCP"
            }
        ],
        "notify_channel": "all-microsofthackathon"
    }

    try:
        response = requests.post(
            f"{MCP_SERVER_URL}/tasks/batch",
            json=batch
        )

        if response.status_code == 200:
            print("✅ Batch tasks sent!")
            result = response.json()
            print(f"   Successful: {result['results']['successful']}/{result['results']['total']}")
            for detail in result['results']['details']:
                status_icon = "✅" if detail['status'] == "sent" else "❌"
                print(f"   {status_icon} {detail['assignee']}: {detail['title']}")
        else:
            print(f"❌ Failed: {response.text}")

    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Main test function"""
    print("🚀 Task Distribution Test for Team Members")
    print("📧 Testing: akshat@futurepath.ai & tanyapragnesh.shah@sjsu.edu")
    print("=" * 60)

    # Option 1: Direct Slack messages (fastest, works immediately)
    print("\n[Option 1] Direct Slack Messages")
    send_direct_slack_message()

    # Option 2: Via MCP Server (if running)
    print("\n[Option 2] Via MCP Server")
    print("Checking if MCP server is running...")

    try:
        health = requests.get(f"{MCP_SERVER_URL}/health")
        if health.status_code == 200:
            print("✅ MCP Server is running")
            send_task_via_mcp()
            send_batch_tasks()
        else:
            print("❌ MCP Server health check failed")
    except:
        print("❌ MCP Server is not running")
        print("Start it with: python -m agent.task_distribution_mcp")

    print("\n" + "=" * 60)
    print("✅ Test Complete!")
    print("Check Slack for messages to both team members:")
    print("• @akshat (akshat@futurepath.ai)")
    print("• @tanyapragnesh.shah (tanyapragnesh.shah@sjsu.edu)")
    print("=" * 60)


if __name__ == "__main__":
    main()