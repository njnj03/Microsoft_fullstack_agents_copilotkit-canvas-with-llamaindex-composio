#!/usr/bin/env python
"""
End-to-End Test Script for Task Distribution API with Slack Integration
Tests the complete flow: Frontend API -> MCP Server -> Slack Messages
"""

import os
import sys
import time
import json
import asyncio
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
FRONTEND_API_URL = os.getenv('FRONTEND_API_URL', 'http://localhost:8001')
MCP_SERVER_URL = os.getenv('MCP_SERVER_URL', 'http://localhost:8000')
TEST_EMAILS = [
    'ydishajadav12402@gmail.com',
    'akshat@futurepath.ai',
]
SLACK_TEST_CHANNEL = os.getenv('SLACK_TEST_CHANNEL', 'general')

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class E2ETestRunner:
    """End-to-End test runner for Slack task distribution"""

    def __init__(self):
        self.test_results = []
        self.start_time = datetime.now()

    def log(self, message: str, color: str = Colors.WHITE):
        """Log message with color and timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{color}[{timestamp}] {message}{Colors.END}")

    def log_success(self, message: str):
        """Log success message"""
        self.log(f"✅ {message}", Colors.GREEN)

    def log_error(self, message: str):
        """Log error message"""
        self.log(f"❌ {message}", Colors.RED)

    def log_warning(self, message: str):
        """Log warning message"""
        self.log(f"⚠️  {message}", Colors.YELLOW)

    def log_info(self, message: str):
        """Log info message"""
        self.log(f"ℹ️  {message}", Colors.BLUE)

    def wait_with_spinner(self, seconds: int, message: str):
        """Wait with a spinner animation"""
        print(f"{Colors.CYAN}{message}{Colors.END}", end="", flush=True)
        for i in range(seconds):
            for char in "|/-\\":
                print(f"\r{Colors.CYAN}{message} {char}{Colors.END}", end="", flush=True)
                time.sleep(0.25)
        print(f"\r{Colors.CYAN}{message} ✓{Colors.END}")

    def test_api_health(self) -> bool:
        """Test 1: Check API health"""
        self.log_info("Test 1: Checking API Health")

        try:
            # Test Frontend API health
            response = requests.get(f"{FRONTEND_API_URL}/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                self.log_success(f"Frontend API is healthy: {health_data.get('status')}")

                # Check MCP connection
                mcp_status = health_data.get('mcp_server', 'unknown')
                if mcp_status == 'connected':
                    self.log_success("MCP Server connection is healthy")
                    return True
                else:
                    self.log_error(f"MCP Server connection failed: {mcp_status}")
                    return False
            else:
                self.log_error(f"Frontend API health check failed: {response.status_code}")
                return False

        except requests.exceptions.ConnectionError:
            self.log_error("Could not connect to Frontend API. Is it running?")
            return False
        except Exception as e:
            self.log_error(f"Health check failed: {str(e)}")
            return False

    def test_mcp_server_direct(self) -> bool:
        """Test 2: Test MCP Server directly"""
        self.log_info("Test 2: Testing MCP Server directly")

        try:
            response = requests.get(f"{MCP_SERVER_URL}/health", timeout=10)
            if response.status_code == 200:
                self.log_success("MCP Server is responding")
                return True
            else:
                self.log_error(f"MCP Server health check failed: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            self.log_error("Could not connect to MCP Server. Is it running?")
            return False
        except Exception as e:
            self.log_error(f"MCP Server test failed: {str(e)}")
            return False

    def test_single_task_distribution(self) -> bool:
        """Test 3: Single task distribution"""
        self.log_info("Test 3: Testing single task distribution to Slack")

        task_data = {
            "email_ids": [TEST_EMAILS[0]],
            "task_text": f"🧪 E2E Test Task - {datetime.now().strftime('%H:%M:%S')} - Please acknowledge this test message.",
            "title": "E2E Test - Single Task",
            "priority": "normal",
            "project": "Testing"
        }

        try:
            self.log_info(f"Sending task to: {TEST_EMAILS[0]}")
            response = requests.post(
                f"{FRONTEND_API_URL}/distribute-tasks",
                json=task_data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                self.log_success("Task distribution request successful")
                self.log_info(f"Response: {json.dumps(result, indent=2)}")

                # Check if task was actually sent
                if result.get('success') and result.get('successful_assignments', 0) > 0:
                    self.log_success("✨ Task successfully sent to Slack!")
                    self.wait_with_spinner(5, "Waiting for Slack message delivery")
                    return True
                else:
                    self.log_error("Task distribution reported as failed")
                    return False
            else:
                self.log_error(f"Task distribution failed: {response.status_code}")
                self.log_error(f"Response: {response.text}")
                return False

        except Exception as e:
            self.log_error(f"Single task distribution test failed: {str(e)}")
            return False

    def test_multiple_task_distribution(self) -> bool:
        """Test 4: Multiple task distribution"""
        self.log_info("Test 4: Testing multiple task distribution to Slack")

        task_data = {
            "email_ids": TEST_EMAILS,
            "task_text": f"🚀 E2E Bulk Test - {datetime.now().strftime('%H:%M:%S')} - This is a bulk distribution test. Please confirm receipt.",
            "title": "E2E Test - Bulk Distribution",
            "priority": "high",
            "project": "Bulk Testing",
            "notify_channel": SLACK_TEST_CHANNEL
        }

        try:
            self.log_info(f"Distributing tasks to {len(TEST_EMAILS)} recipients:")
            for email in TEST_EMAILS:
                self.log_info(f"  → {email}")

            response = requests.post(
                f"{FRONTEND_API_URL}/distribute-tasks",
                json=task_data,
                timeout=60  # Longer timeout for multiple tasks
            )

            if response.status_code == 200:
                result = response.json()
                self.log_success("Bulk task distribution request successful")

                total = result.get('total_tasks', 0)
                successful = result.get('successful_assignments', 0)
                failed = result.get('failed_assignments', 0)

                self.log_info(f"📊 Distribution Summary:")
                self.log_info(f"   Total tasks: {total}")
                self.log_success(f"   Successful: {successful}")
                if failed > 0:
                    self.log_warning(f"   Failed: {failed}")

                if successful > 0:
                    self.log_success("✨ Tasks successfully sent to Slack!")
                    self.wait_with_spinner(10, "Waiting for all Slack messages to be delivered")
                    return True
                else:
                    self.log_error("No tasks were successfully distributed")
                    return False
            else:
                self.log_error(f"Bulk task distribution failed: {response.status_code}")
                return False

        except Exception as e:
            self.log_error(f"Multiple task distribution test failed: {str(e)}")
            return False

    def test_quick_assign(self) -> bool:
        """Test 5: Quick assignment"""
        self.log_info("Test 5: Testing quick task assignment")

        quick_task = {
            "email": TEST_EMAILS[1],
            "task_description": f"⚡ Quick Assignment Test - {datetime.now().strftime('%H:%M:%S')} - This is a quick assignment test message.",
            "title": "E2E Test - Quick Assignment",
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
                if result.get('success'):
                    self.log_success("Quick assignment successful!")
                    self.wait_with_spinner(3, "Waiting for Slack message")
                    return True
                else:
                    self.log_error("Quick assignment reported as failed")
                    return False
            else:
                self.log_error(f"Quick assignment failed: {response.status_code}")
                return False

        except Exception as e:
            self.log_error(f"Quick assignment test failed: {str(e)}")
            return False

    def test_error_handling(self) -> bool:
        """Test 6: Error handling"""
        self.log_info("Test 6: Testing error handling")

        # Test with invalid data
        invalid_data = {
            "email_ids": [],  # Empty email list
            "task_text": ""   # Empty task
        }

        try:
            response = requests.post(
                f"{FRONTEND_API_URL}/distribute-tasks",
                json=invalid_data,
                timeout=10
            )

            if response.status_code == 400:
                self.log_success("Error handling works correctly - rejected invalid data")
                return True
            else:
                self.log_warning(f"Expected 400 error, got {response.status_code}")
                return False

        except Exception as e:
            self.log_error(f"Error handling test failed: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all end-to-end tests"""
        self.log(f"\n{Colors.BOLD}{'='*60}", Colors.PURPLE)
        self.log(f"🚀 SLACK TASK DISTRIBUTION - END-TO-END TESTS", Colors.PURPLE)
        self.log(f"{'='*60}{Colors.END}", Colors.PURPLE)

        self.log_info(f"Frontend API: {FRONTEND_API_URL}")
        self.log_info(f"MCP Server: {MCP_SERVER_URL}")
        self.log_info(f"Test Emails: {', '.join(TEST_EMAILS)}")
        self.log_info(f"Test Channel: #{SLACK_TEST_CHANNEL}")

        print()

        tests = [
            ("API Health Check", self.test_api_health),
            ("MCP Server Direct", self.test_mcp_server_direct),
            ("Single Task Distribution", self.test_single_task_distribution),
            ("Multiple Task Distribution", self.test_multiple_task_distribution),
            ("Quick Assignment", self.test_quick_assign),
            ("Error Handling", self.test_error_handling),
        ]

        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            self.log(f"\n{'-'*50}", Colors.CYAN)
            try:
                if test_func():
                    self.test_results.append((test_name, "PASSED"))
                    passed += 1
                else:
                    self.test_results.append((test_name, "FAILED"))
            except Exception as e:
                self.log_error(f"Test '{test_name}' crashed: {str(e)}")
                self.test_results.append((test_name, "CRASHED"))

        # Print final results
        self.print_final_results(passed, total)

    def print_final_results(self, passed: int, total: int):
        """Print final test results"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        print(f"\n{Colors.BOLD}{'='*60}", Colors.PURPLE)
        print(f"📋 TEST RESULTS SUMMARY", Colors.PURPLE)
        print(f"{'='*60}{Colors.END}", Colors.PURPLE)

        for test_name, status in self.test_results:
            if status == "PASSED":
                self.log_success(f"{test_name}: {status}")
            elif status == "FAILED":
                self.log_error(f"{test_name}: {status}")
            else:
                self.log_warning(f"{test_name}: {status}")

        print()
        success_rate = (passed / total) * 100 if total > 0 else 0

        if success_rate == 100:
            self.log(f"🎉 ALL TESTS PASSED! ({passed}/{total})", Colors.GREEN + Colors.BOLD)
        elif success_rate >= 80:
            self.log(f"✅ Most tests passed ({passed}/{total}) - {success_rate:.1f}%", Colors.YELLOW + Colors.BOLD)
        else:
            self.log(f"❌ Many tests failed ({passed}/{total}) - {success_rate:.1f}%", Colors.RED + Colors.BOLD)

        self.log_info(f"Total execution time: {duration:.2f} seconds")

        print(f"\n{Colors.BOLD}📱 NEXT STEPS:{Colors.END}")
        print(f"1. Check your Slack channels/DMs for the test messages")
        print(f"2. Verify that team members received the task notifications")
        print(f"3. Test the interactive buttons in Slack messages")
        print(f"4. Update email mappings in the MCP server if needed")

        if passed == total:
            print(f"\n{Colors.GREEN + Colors.BOLD}🚀 Your system is ready for production use!{Colors.END}")
        else:
            print(f"\n{Colors.YELLOW}⚠️  Please fix the failing tests before production deployment{Colors.END}")


def main():
    """Main function"""
    print(f"{Colors.BOLD}Starting End-to-End Slack Integration Tests...{Colors.END}")

    # Check environment
    if not os.getenv('COMPOSIO_API_KEY'):
        print(f"{Colors.RED}❌ COMPOSIO_API_KEY not found in environment{Colors.END}")
        print("Please set up your .env file with required API keys")
        sys.exit(1)

    # Run tests
    runner = E2ETestRunner()
    runner.run_all_tests()


if __name__ == "__main__":
    main()