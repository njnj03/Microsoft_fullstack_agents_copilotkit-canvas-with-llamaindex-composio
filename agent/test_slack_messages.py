#!/usr/bin/env python
"""
Focused Slack Message Test Script
Tests actual Slack message delivery with real-time verification
"""

import os
import time
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
FRONTEND_API_URL = os.getenv('FRONTEND_API_URL', 'http://localhost:8001')

# Test configuration - UPDATE THESE WITH YOUR REAL EMAIL ADDRESSES
TEST_EMAILS = [
    'ydishajadav12402@gmail.com',  # Replace with your actual email
    'akshat@futurepath.ai',    # Replace with your teammate's email
]

def print_banner():
    """Print test banner"""
    print("\n" + "="*60)
    print("🔥 SLACK MESSAGE DELIVERY TEST")
    print("="*60)
    print(f"Frontend API: {FRONTEND_API_URL}")
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

def test_slack_message_delivery():
    """Test actual Slack message delivery"""
    print("\n📨 Testing Slack Message Delivery...")

    # Create a unique test message
    timestamp = datetime.now().strftime('%H:%M:%S')
    test_message = f"""
🧪 LIVE TEST MESSAGE - {timestamp}

This is an end-to-end test of the task distribution system.

TASK: Please respond with 👍 in Slack to confirm you received this message.

Details:
- Sent via: Frontend API → MCP Server → Slack
- Priority: High
- Test ID: TEST-{timestamp.replace(':', '')}
    """.strip()

    task_data = {
        "email_ids": TEST_EMAILS,
        "task_text": test_message,
        "title": f"🔥 LIVE TEST - {timestamp}",
        "priority": "high",
        "project": "E2E Testing",
        "notify_channel": "general"  # Change to your test channel
    }

    print(f"\n📋 Sending test message to:")
    for email in TEST_EMAILS:
        print(f"  → {email}")

    try:
        print(f"\n⏳ Sending request to API...")
        response = requests.post(
            f"{FRONTEND_API_URL}/distribute-tasks",
            json=task_data,
            timeout=60
        )

        print(f"📊 API Response: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ API Request Successful!")
            print(f"📄 Response Data:")
            print(json.dumps(result, indent=2))

            # Check distribution results
            successful = result.get('successful_assignments', 0)
            failed = result.get('failed_assignments', 0)

            if successful > 0:
                print(f"\n🎉 SUCCESS! {successful} messages sent to Slack")
                print(f"\n📱 NEXT STEPS:")
                print(f"1. Check your Slack DMs for the test messages")
                print(f"2. Look for messages from your Slack bot")
                print(f"3. Verify the message format and interactive buttons")
                print(f"4. Test the 'Accept Task' and 'Mark Complete' buttons")

                if failed > 0:
                    print(f"\n⚠️  {failed} messages failed to send")
                    print("Check the MCP server logs for details")

                return True
            else:
                print(f"\n❌ No messages were sent successfully")
                print("Details:", result.get('details', []))
                return False
        else:
            print(f"❌ API Request Failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API. Make sure servers are running:")
        print("   python agent/run_servers.py")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        return False

def test_quick_slack_message():
    """Test quick message to single user"""
    print("\n⚡ Testing Quick Slack Message...")

    timestamp = datetime.now().strftime('%H:%M:%S')

    quick_task = {
        "email": TEST_EMAILS[0],  # Send to first test email
        "task_description": f"⚡ Quick test message at {timestamp}. Please acknowledge in Slack!",
        "title": f"Quick Test - {timestamp}",
        "priority": "urgent"
    }

    try:
        response = requests.post(
            f"{FRONTEND_API_URL}/quick-assign",
            json=quick_task,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ Quick message sent!")
            print(f"📱 Check Slack DM for: {TEST_EMAILS[0]}")
            return True
        else:
            print(f"❌ Quick message failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Quick message test failed: {str(e)}")
        return False

def verify_slack_bot_setup():
    """Verify Slack bot is properly configured"""
    print("\n🔍 Verifying Slack Bot Setup...")

    try:
        # Check API health
        response = requests.get(f"{FRONTEND_API_URL}/health")
        if response.status_code == 200:
            health = response.json()
            print(f"✅ Frontend API: {health.get('status', 'unknown')}")

            mcp_status = health.get('mcp_server', 'unknown')
            if mcp_status == 'connected':
                print("✅ MCP Server: Connected")
            else:
                print(f"❌ MCP Server: {mcp_status}")
                return False

            # Check MCP status
            mcp_response = requests.get(f"{FRONTEND_API_URL}/mcp-status")
            if mcp_response.status_code == 200:
                mcp_data = mcp_response.json()
                print(f"📊 MCP Status: {mcp_data.get('status', 'unknown')}")
                return mcp_data.get('status') == 'healthy'

            return True
        else:
            print(f"❌ API Health Check Failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Setup verification failed: {str(e)}")
        return False

def main():
    """Main test function"""
    print_banner()

    # Update test emails warning
    if 'your.email@company.com' in TEST_EMAILS:
        print("\n⚠️  WARNING: Please update TEST_EMAILS with your real email addresses!")
        print("Edit test_slack_messages.py and replace the placeholder emails.")
        print("\nCurrent test emails:")
        for email in TEST_EMAILS:
            print(f"  → {email}")

        response = input("\nDo you want to continue with these emails? (y/n): ")
        if response.lower() != 'y':
            print("Please update the email addresses and try again.")
            return

    # Run verification
    if not verify_slack_bot_setup():
        print("\n❌ Slack bot setup verification failed!")
        print("\nTroubleshooting:")
        print("1. Make sure both servers are running: python agent/run_servers.py")
        print("2. Check your .env file has all required API keys")
        print("3. Verify Slack bot is authenticated with Composio")
        return

    print("\n✅ Slack bot setup verified!")

    # Run tests
    success_count = 0

    # Test 1: Multiple message distribution
    if test_slack_message_delivery():
        success_count += 1
        print("\n⏳ Waiting 5 seconds before next test...")
        time.sleep(5)

    # Test 2: Quick single message
    if test_quick_slack_message():
        success_count += 1

    # Results
    print(f"\n{'='*60}")
    print(f"🏁 TEST RESULTS: {success_count}/2 tests passed")

    if success_count == 2:
        print("🎉 ALL TESTS PASSED!")
        print("\n📱 Check your Slack now:")
        print("• Look for DMs from your bot")
        print("• Verify message formatting")
        print("• Test the interactive buttons")
        print("• Check if channel notifications were sent")
    else:
        print("⚠️  Some tests failed. Check the errors above.")

    print("="*60)

if __name__ == "__main__":
    main()