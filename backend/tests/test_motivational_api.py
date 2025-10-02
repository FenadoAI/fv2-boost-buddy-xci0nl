"""Test motivational chat API endpoints."""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load environment
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001")
API_URL = f"{BASE_URL}/api"


def test_signup():
    """Test user signup."""
    print("\n🧪 Testing signup...")

    response = requests.post(
        f"{API_URL}/auth/signup",
        json={
            "username": "testuser123",
            "email": "test@example.com",
            "password": "testpass123"
        }
    )

    data = response.json()
    print(f"Response: {data}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert data["success"] is True, "Signup should succeed"
    assert "token" in data, "Should return token"
    assert data["username"] == "testuser123", "Should return username"

    print("✅ Signup test passed!")
    return data["token"]


def test_login():
    """Test user login."""
    print("\n🧪 Testing login...")

    response = requests.post(
        f"{API_URL}/auth/login",
        json={
            "username": "testuser123",
            "password": "testpass123"
        }
    )

    data = response.json()
    print(f"Response: {data}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert data["success"] is True, "Login should succeed"
    assert "token" in data, "Should return token"

    print("✅ Login test passed!")
    return data["token"]


def test_motivational_chat(token):
    """Test motivational chat endpoint."""
    print("\n🧪 Testing motivational chat...")

    response = requests.post(
        f"{API_URL}/chat/motivational",
        json={"message": "I'm feeling down today"},
        headers={"Authorization": f"Bearer {token}"}
    )

    data = response.json()
    print(f"Response: {data}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert data["success"] is True, "Chat should succeed"
    assert len(data["response"]) > 0, "Should return a response"
    assert "timestamp" in data, "Should include timestamp"

    print(f"AI Response: {data['response'][:100]}...")
    print("✅ Motivational chat test passed!")


def test_daily_quote(token):
    """Test daily quote endpoint."""
    print("\n🧪 Testing daily quote...")

    response = requests.get(
        f"{API_URL}/daily-quote",
        headers={"Authorization": f"Bearer {token}"}
    )

    data = response.json()
    print(f"Response: {data}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert data["success"] is True, "Should succeed"
    assert len(data["quote"]) > 0, "Should return a quote"

    print(f"Daily Quote: {data['quote']}")
    print("✅ Daily quote test passed!")


def test_chat_history(token):
    """Test chat history endpoint."""
    print("\n🧪 Testing chat history...")

    response = requests.get(
        f"{API_URL}/chat/history",
        headers={"Authorization": f"Bearer {token}"}
    )

    data = response.json()
    print(f"Response: {data}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert data["success"] is True, "Should succeed"
    assert "messages" in data, "Should return messages"
    assert len(data["messages"]) > 0, "Should have at least one message from previous test"

    print(f"Found {len(data['messages'])} messages in history")
    print("✅ Chat history test passed!")


def test_unauthorized_access():
    """Test that endpoints require authentication."""
    print("\n🧪 Testing unauthorized access...")

    response = requests.post(
        f"{API_URL}/chat/motivational",
        json={"message": "Hello"}
    )

    assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    print("✅ Unauthorized access test passed!")


if __name__ == "__main__":
    print("🚀 Starting Motivational Chat API Tests")
    print(f"Testing against: {API_URL}")

    try:
        # Test signup (might fail if user exists)
        try:
            token = test_signup()
        except AssertionError as e:
            if "already exists" in str(e):
                print("User already exists, testing login instead...")
                token = test_login()
            else:
                raise

        # Test login
        token = test_login()

        # Test protected endpoints
        test_motivational_chat(token)
        test_daily_quote(token)
        test_chat_history(token)

        # Test unauthorized access
        test_unauthorized_access()

        print("\n✅ All tests passed!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
