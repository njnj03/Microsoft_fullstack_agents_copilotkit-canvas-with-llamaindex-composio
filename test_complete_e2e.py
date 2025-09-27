#!/usr/bin/env python
"""
Complete End-to-End Test for File Upload -> LlamaIndex Processing -> Task Creation -> Slack Distribution
Tests the full workflow from frontend to backend with all integrations.
"""

import os
import sys
import time
import json
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
MAIN_SERVER_URL = os.getenv('MAIN_SERVER_URL', 'http://localhost:9000')
MCP_SERVER_URL = os.getenv('MCP_SERVER_URL', 'http://localhost:8000')
FRONTEND_API_URL = os.getenv('FRONTEND_API_URL', 'http://localhost:8001')

# Test data
TEST_MEETING_ID = "complete-e2e-test-2025-09-27"
TEST_EMAILS = [
    'ydishajadav12402@gmail.com',
    'akshat@futurepath.ai',
]
SLACK_TEST_CHANNEL = "general"

class Colors:
    """ANSI color codes"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class CompleteE2ETest:
    """Complete end-to-end test runner"""

    def __init__(self):
        self.test_results = []
        self.start_time = datetime.now()
        self.uploaded_file_id = None
        self.meeting_id = TEST_MEETING_ID

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

    def log_info(self, message: str):
        """Log info message"""
        self.log(f"ℹ️  {message}", Colors.BLUE)

    def test_servers_health(self) -> bool:
        """Test 1: Check all servers are healthy"""
        self.log_info("Test 1: Checking all servers health")

        try:
            # Test main server (port 9000)
            response = requests.get(f"{MAIN_SERVER_URL}/health", timeout=10)
            if response.status_code != 200:
                self.log_error("Main server health check failed")
                return False
            self.log_success("Main server (port 9000) is healthy")

            # Test MCP server (port 8000)
            response = requests.get(f"{MCP_SERVER_URL}/health", timeout=10)
            if response.status_code != 200:
                self.log_error("MCP server health check failed")
                return False
            self.log_success("MCP server (port 8000) is healthy")

            # Test frontend API (port 8001)
            response = requests.get(f"{FRONTEND_API_URL}/health", timeout=10)
            if response.status_code != 200:
                self.log_error("Frontend API health check failed")
                return False
            self.log_success("Frontend API (port 8001) is healthy")

            return True

        except Exception as e:
            self.log_error(f"Server health check failed: {str(e)}")
            return False

    def test_file_upload(self) -> bool:
        """Test 2: Upload test file"""
        self.log_info("Test 2: Testing file upload to main server")

        try:
            # Create test file path
            test_file_path = Path("test_meeting_minutes.txt")

            if not test_file_path.exists():
                self.log_error("Test file not found. Please ensure test_meeting_minutes.txt exists.")
                return False

            # Upload file
            with open(test_file_path, 'rb') as f:
                files = {'file': (test_file_path.name, f, 'text/plain')}
                response = requests.post(
                    f"{MAIN_SERVER_URL}/ingest/minutes-file?meeting_id={self.meeting_id}",
                    files=files,
                    timeout=30
                )

            if response.status_code == 200:
                result = response.json()
                self.uploaded_file_id = result['file_id']
                self.log_success(f"File uploaded successfully: {result['filename']}")
                self.log_info(f"File ID: {self.uploaded_file_id}")
                return True
            else:
                self.log_error(f"File upload failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            self.log_error(f"File upload test failed: {str(e)}")
            return False

    def test_document_processing_and_task_creation(self) -> bool:
        """Test 3: Process document and create tasks via LlamaIndex + MCP"""
        self.log_info("Test 3: Processing document with LlamaIndex and creating tasks via MCP")

        if not self.uploaded_file_id:
            self.log_error("No file uploaded to process")
            return False

        try:
            # Prepare task creation request
            task_request = {
                "file_id": self.uploaded_file_id,
                "meeting_id": self.meeting_id,
                "team_emails": TEST_EMAILS,
                "prompt": "Extract actionable tasks from this meeting minutes document and assign them to team members",
                "notify_channel": SLACK_TEST_CHANNEL
            }

            self.log_info(f"Processing document with file_id: {self.uploaded_file_id}")
            self.log_info(f"Team emails: {', '.join(TEST_EMAILS)}")

            # Send request to process document and create tasks
            response = requests.post(
                f"{MAIN_SERVER_URL}/process/create-tasks",
                json=task_request,
                timeout=60  # Longer timeout for AI processing
            )

            if response.status_code == 200:
                result = response.json()

                self.log_success(f"Document processed successfully!")
                self.log_info(f"File processed: {result['file_processed']}")
                self.log_info(f"Tasks created: {result['tasks_created']}")
                self.log_success(f"Tasks distributed to Slack: {result['tasks_distributed']}")

                if result['failed_distributions'] > 0:
                    self.log_error(f"Failed distributions: {result['failed_distributions']}")

                # Show task details
                self.log_info("Task distribution details:")
                for detail in result['details']:
                    status_color = Colors.GREEN if detail['status'] == 'distributed' else Colors.RED
                    self.log(f"  • {detail['task']} → {detail['assignee']} [{detail['status']}]", status_color)

                return result['tasks_distributed'] > 0

            else:
                self.log_error(f"Document processing failed: {response.status_code}")
                self.log_error(f"Response: {response.text}")
                return False

        except Exception as e:
            self.log_error(f"Document processing test failed: {str(e)}")
            return False

    def test_verify_file_listing(self) -> bool:
        """Test 4: Verify uploaded files can be listed"""
        self.log_info("Test 4: Verifying file listing")

        try:
            response = requests.get(f"{MAIN_SERVER_URL}/ingest/files/{self.meeting_id}")

            if response.status_code == 200:
                result = response.json()
                if result['count'] > 0:
                    self.log_success(f"Found {result['count']} uploaded file(s)")
                    return True
                else:
                    self.log_error("No files found in listing")
                    return False
            else:
                self.log_error(f"File listing failed: {response.status_code}")
                return False

        except Exception as e:
            self.log_error(f"File listing test failed: {str(e)}")
            return False

    def run_all_tests(self):
        """Run complete end-to-end test suite"""
        self.log(f"\n{Colors.BOLD}{'='*70}", Colors.PURPLE)
        self.log(f"🚀 COMPLETE END-TO-END INTEGRATION TEST", Colors.PURPLE)
        self.log(f"Frontend → LlamaIndex → MCP → Slack", Colors.PURPLE)
        self.log(f"{'='*70}{Colors.END}", Colors.PURPLE)

        self.log_info(f"Main Server: {MAIN_SERVER_URL}")
        self.log_info(f"MCP Server: {MCP_SERVER_URL}")
        self.log_info(f"Frontend API: {FRONTEND_API_URL}")
        self.log_info(f"Meeting ID: {self.meeting_id}")
        self.log_info(f"Test Emails: {', '.join(TEST_EMAILS)}")

        print()

        tests = [
            ("Server Health Check", self.test_servers_health),
            ("File Upload", self.test_file_upload),
            ("Document Processing & Task Creation", self.test_document_processing_and_task_creation),
            ("File Listing Verification", self.test_verify_file_listing),
        ]

        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            self.log(f"\n{'-'*60}", Colors.CYAN)
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

        print(f"\n{Colors.BOLD}{'='*70}", Colors.PURPLE)
        print(f"📋 COMPLETE E2E TEST RESULTS", Colors.PURPLE)
        print(f"{'='*70}{Colors.END}", Colors.PURPLE)

        for test_name, status in self.test_results:
            if status == "PASSED":
                self.log_success(f"{test_name}: {status}")
            elif status == "FAILED":
                self.log_error(f"{test_name}: {status}")
            else:
                self.log_error(f"{test_name}: {status}")

        print()
        success_rate = (passed / total) * 100 if total > 0 else 0

        if success_rate == 100:
            self.log(f"🎉 ALL TESTS PASSED! ({passed}/{total})", Colors.GREEN + Colors.BOLD)
            self.log("🚀 Your complete end-to-end integration is working!", Colors.GREEN + Colors.BOLD)
        elif success_rate >= 75:
            self.log(f"✅ Most tests passed ({passed}/{total}) - {success_rate:.1f}%", Colors.YELLOW + Colors.BOLD)
        else:
            self.log(f"❌ Many tests failed ({passed}/{total}) - {success_rate:.1f}%", Colors.RED + Colors.BOLD)

        self.log_info(f"Total execution time: {duration:.2f} seconds")

        print(f"\n{Colors.BOLD}📱 NEXT STEPS:{Colors.END}")
        print(f"1. Check your Slack channels/DMs for the generated task messages")
        print(f"2. Verify that team members received task assignments")
        print(f"3. Test the interactive buttons in Slack task messages")
        print(f"4. Review the uploaded files in the uploads/{self.meeting_id}/ directory")
        print(f"5. Test with different document types and content")

        if passed == total:
            print(f"\n{Colors.GREEN + Colors.BOLD}🎯 INTEGRATION COMPLETE - READY FOR PRODUCTION!{Colors.END}")
        else:
            print(f"\n{Colors.YELLOW}⚠️  Fix failing tests before production deployment{Colors.END}")


def main():
    """Main function"""
    print(f"{Colors.BOLD}Starting Complete End-to-End Integration Test...{Colors.END}")

    # Check environment
    required_env_vars = ['OPENAI_API_KEY', 'COMPOSIO_API_KEY']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        print(f"{Colors.RED}❌ Missing required environment variables: {', '.join(missing_vars)}{Colors.END}")
        print("Please set up your .env file with required API keys")
        sys.exit(1)

    # Run tests
    runner = CompleteE2ETest()
    runner.run_all_tests()


if __name__ == "__main__":
    main()