"""Simple example for calling the ADK API server.

Usage:
    1. Start the server:  uv run adk api_server --host 0.0.0.0 --port 8000 .
    2. Run this script:   uv run python example_request.py
"""

import json

import httpx

BASE_URL = "http://localhost:8000"
APP_NAME = "doc_assistant"
USER_ID = "test_user"


def list_apps():
    """List all available agents."""
    resp = httpx.get(f"{BASE_URL}/list-apps")
    resp.raise_for_status()
    print("Available apps:", resp.json())
    return resp.json()


def list_sessions():
    """List all existing sessions for the user."""
    resp = httpx.get(
        f"{BASE_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions",
    )
    resp.raise_for_status()
    sessions = resp.json()
    print(f"Found {len(sessions)} session(s):")
    for s in sessions:
        print(f"  - {s['id']}")
    return sessions


def create_session() -> str:
    """Create a new session and return its ID."""
    resp = httpx.post(
        f"{BASE_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions",
        json={},
    )
    resp.raise_for_status()
    session_id = resp.json()["id"]
    print(f"Created session: {session_id}")
    return session_id


def send_message(session_id: str, message: str):
    """Send a message and print the response (synchronous /run)."""
    resp = httpx.post(
        f"{BASE_URL}/run",
        json={
            "app_name": APP_NAME,
            "user_id": USER_ID,
            "session_id": session_id,
            "new_message": {
                "role": "user",
                "parts": [{"text": message}],
            },
        },
        timeout=120,
    )
    resp.raise_for_status()
    events = resp.json()
    print(json.dumps(events, indent=2, ensure_ascii=False))


def send_message_with_confirmation(session_id: str, message: str):
    """Send a message, auto-approve any tool confirmation, and print all events."""
    resp = httpx.post(
        f"{BASE_URL}/run",
        json={
            "app_name": APP_NAME,
            "user_id": USER_ID,
            "session_id": session_id,
            "new_message": {
                "role": "user",
                "parts": [{"text": message}],
            },
        },
        timeout=120,
    )
    resp.raise_for_status()
    events = resp.json()
    print(json.dumps(events, indent=2, ensure_ascii=False))

    # Check if any event contains a confirmation request
    confirmation_id = None
    for event in events:
        content = event.get("content")
        if not content or not content.get("parts"):
            continue
        for part in content["parts"]:
            fc = part.get("functionCall")
            if fc and fc.get("name") == "adk_request_confirmation":
                confirmation_id = fc["id"]
                tool_name = fc["args"]["originalFunctionCall"]["name"]
                print(f"\n>>> Tool confirmation requested: {tool_name}")
                break

    if not confirmation_id:
        return events

    # Send confirmation (approved)
    print(">>> Auto-approving...")
    resp = httpx.post(
        f"{BASE_URL}/run",
        json={
            "app_name": APP_NAME,
            "user_id": USER_ID,
            "session_id": session_id,
            "new_message": {
                "role": "user",
                "parts": [
                    {
                        "functionResponse": {
                            "id": confirmation_id,
                            "name": "adk_request_confirmation",
                            "response": {"confirmed": True},
                        }
                    }
                ],
            },
        },
        timeout=120,
    )
    resp.raise_for_status()
    confirmation_events = resp.json()
    print("\n>>> After confirmation:")
    print(json.dumps(confirmation_events, indent=2, ensure_ascii=False))
    return confirmation_events


def send_message_sse(session_id: str, message: str):
    """Send a message and stream the response via SSE (/run_sse)."""
    with httpx.stream(
        "POST",
        f"{BASE_URL}/run_sse",
        json={
            "app_name": APP_NAME,
            "user_id": USER_ID,
            "session_id": session_id,
            "new_message": {
                "role": "user",
                "parts": [{"text": message}],
            },
        },
        timeout=120,
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line.startswith("data:"):
                print(line)


if __name__ == "__main__":
    # 1. List available apps
    list_apps()

    # 2. List sessions
    list_sessions()

    # 3. Create a session
    sid = create_session()

    # 4. Send a message with auto-confirmation
    print("\n--- Synchronous /run with confirmation ---")
    send_message_with_confirmation(sid, "创建一个新的终端")

    # 4. Send a message (SSE streaming)
    print("\n--- Streaming /run_sse ---")
    send_message_sse(sid, "你能做什么？")
