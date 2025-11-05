#!/usr/bin/env python3
"""
Load Testing Script for AI Counselor using Locust

Simulates multiple concurrent users chatting with the AI counselor
to test system performance under load.

Usage:
    # Install locust: pip install locust

    # Run with web UI
    locust -f tests/load_test.py --host=http://localhost:8000

    # Headless mode (100 users, 10 spawn rate, 60s duration)
    locust -f tests/load_test.py --host=http://localhost:8000 \
           --users 100 --spawn-rate 10 --run-time 60s --headless

    # Generate report
    locust -f tests/load_test.py --host=http://localhost:8000 \
           --users 50 --spawn-rate 5 --run-time 300s --headless \
           --html load_test_report.html
"""

from locust import HttpUser, task, between, events
import random
import json


# Sample messages for realistic testing
SAMPLE_MESSAGES = [
    "안녕하세요",
    "도움이 필요해요",
    "요즘 스트레스를 많이 받고 있어요",
    "어떻게 관리하면 좋을까요?",
    "잠을 잘 못 자요",
    "불안한 기분이 들어요",
    "구체적인 방법을 알려주세요",
    "감사합니다",
    "다음에 또 상담할 수 있나요?",
    "AI 상담은 어떻게 작동하나요?",
    "대화 내용이 안전하게 보호되나요?",
    "언제든지 상담 가능한가요?",
]

# FAQ queries (likely to hit cache)
FAQ_QUERIES = [
    "AI 상담은 어떻게 작동하나요?",
    "대화 내용이 안전하게 보호되나요?",
    "언제든지 대화를 시작할 수 있나요?",
    "전문 상담사와 연결할 수 있나요?",
]

# Crisis-related messages (for testing crisis detection)
CRISIS_MESSAGES = [
    "요즘 삶이 힘들어요",
    "우울한 기분이 계속돼요",
    "불안함을 느껴요",
]


class AICounselorUser(HttpUser):
    """Simulated AI Counselor user"""

    # Wait between 1-3 seconds between tasks (realistic user behavior)
    wait_time = between(1, 3)

    def on_start(self):
        """Initialize user session"""
        # Create anonymous session
        response = self.client.post("/auth/anonymous")
        if response.status_code == 201:
            data = response.json()
            self.session_token = data["session_token"]
            self.conversation_id = None
        else:
            self.session_token = None

    @task(10)
    def send_regular_message(self):
        """Send regular chat message (most common task)"""
        if not self.session_token:
            return

        message = random.choice(SAMPLE_MESSAGES)
        payload = {
            "message": message,
            "stream": False
        }

        if self.conversation_id:
            payload["conversation_id"] = self.conversation_id

        with self.client.post(
            "/chat/send",
            json=payload,
            headers={"X-Session-Token": self.session_token},
            catch_response=True,
            name="/chat/send (regular)"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if not self.conversation_id:
                    self.conversation_id = data.get("conversation_id")
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(5)
    def send_faq_query(self):
        """Send FAQ query (likely to hit cache)"""
        if not self.session_token:
            return

        query = random.choice(FAQ_QUERIES)
        payload = {
            "message": query,
            "stream": False
        }

        with self.client.post(
            "/chat/send",
            json=payload,
            headers={"X-Session-Token": self.session_token},
            catch_response=True,
            name="/chat/send (FAQ)"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @task(2)
    def send_streaming_message(self):
        """Send message with streaming response"""
        if not self.session_token:
            return

        message = random.choice(SAMPLE_MESSAGES)
        payload = {
            "message": message,
            "stream": True
        }

        if self.conversation_id:
            payload["conversation_id"] = self.conversation_id

        with self.client.post(
            "/chat/send",
            json=payload,
            headers={"X-Session-Token": self.session_token},
            stream=True,
            catch_response=True,
            name="/chat/send (streaming)"
        ) as response:
            if response.status_code == 200:
                # Consume stream
                for line in response.iter_lines():
                    pass
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @task(1)
    def send_crisis_message(self):
        """Send crisis-related message (tests crisis detection)"""
        if not self.session_token:
            return

        message = random.choice(CRISIS_MESSAGES)
        payload = {
            "message": message,
            "stream": False
        }

        with self.client.post(
            "/chat/send",
            json=payload,
            headers={"X-Session-Token": self.session_token},
            catch_response=True,
            name="/chat/send (crisis)"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @task(3)
    def get_conversation_history(self):
        """Get conversation history"""
        if not self.session_token or not self.conversation_id:
            return

        with self.client.get(
            f"/chat/history/{self.conversation_id}",
            headers={"X-Session-Token": self.session_token},
            catch_response=True,
            name="/chat/history/{id}"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @task(1)
    def check_health(self):
        """Check API health"""
        with self.client.get(
            "/health",
            catch_response=True,
            name="/health"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")


# Event handlers for reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Print test start message"""
    print("\n╔═══════════════════════════════════════════════════════════╗")
    print("║                                                           ║")
    print("║          AI Counselor - Load Test Starting               ║")
    print("║                                                           ║")
    print("╚═══════════════════════════════════════════════════════════╝\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print test results summary"""
    stats = environment.stats

    print("\n╔═══════════════════════════════════════════════════════════╗")
    print("║                                                           ║")
    print("║          AI Counselor - Load Test Results                ║")
    print("║                                                           ║")
    print("╚═══════════════════════════════════════════════════════════╝\n")

    print(f"Total requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Failure rate: {stats.total.fail_ratio * 100:.2f}%")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"Min response time: {stats.total.min_response_time:.2f}ms")
    print(f"Max response time: {stats.total.max_response_time:.2f}ms")
    print(f"Requests per second: {stats.total.total_rps:.2f}\n")

    # Percentiles
    print("Response time percentiles:")
    for percentile, value in stats.total.get_response_time_percentile({
        0.50: "50th",
        0.75: "75th",
        0.90: "90th",
        0.95: "95th",
        0.99: "99th",
    }).items():
        print(f"  {percentile}: {value:.2f}ms")

    print("\n")


# Custom scenarios for different test types
class LightLoadUser(AICounselorUser):
    """Light load - casual browsing"""
    wait_time = between(3, 10)


class MediumLoadUser(AICounselorUser):
    """Medium load - active users"""
    wait_time = between(1, 5)


class HeavyLoadUser(AICounselorUser):
    """Heavy load - power users"""
    wait_time = between(0.5, 2)


# Spike test scenario
class SpikeTestUser(AICounselorUser):
    """Spike test - rapid requests"""
    wait_time = between(0.1, 0.5)

    @task(20)  # Higher weight for stress testing
    def rapid_fire_messages(self):
        """Send multiple rapid messages"""
        if not self.session_token:
            return

        for i in range(5):
            message = random.choice(SAMPLE_MESSAGES)
            payload = {"message": message, "stream": False}

            self.client.post(
                "/chat/send",
                json=payload,
                headers={"X-Session-Token": self.session_token},
                name="/chat/send (spike)"
            )


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║          AI Counselor - Load Testing Script               ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

Usage:
  # Run with web UI (http://localhost:8089)
  locust -f tests/load_test.py --host=http://localhost:8000

  # Headless mode
  locust -f tests/load_test.py --host=http://localhost:8000 \\
         --users 100 --spawn-rate 10 --run-time 60s --headless

  # Generate HTML report
  locust -f tests/load_test.py --host=http://localhost:8000 \\
         --users 50 --spawn-rate 5 --run-time 300s --headless \\
         --html load_test_report.html

Test Scenarios:
  - AICounselorUser: Normal user behavior
  - LightLoadUser: Casual browsing (slow)
  - MediumLoadUser: Active users (normal)
  - HeavyLoadUser: Power users (fast)
  - SpikeTestUser: Stress test (rapid-fire)

Recommended Tests:
  1. Baseline: 10 users, 2/s spawn, 2 minutes
  2. Normal Load: 50 users, 5/s spawn, 5 minutes
  3. Peak Load: 100 users, 10/s spawn, 10 minutes
  4. Stress Test: 200 users, 20/s spawn, 5 minutes (SpikeTestUser)
    """)
