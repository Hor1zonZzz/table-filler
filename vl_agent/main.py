"""VL Agent Main Entry Point.

Standalone entry point for running the VL agent with configurable persistence.
"""

import asyncio
from pathlib import Path

from dotenv import load_dotenv

# Load .env from vl_agent directory
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

from google.adk.runners import Runner
from google.genai import types

from .agent import root_agent
from .config import Config
from .services import create_session_service


async def main():
    """Run VL agent interactively."""
    # Create session service based on config
    session_service = create_session_service()

    # Create a new session
    session = await session_service.create_session(
        app_name=Config.APP_NAME,
        user_id="user-1",
    )

    # Create Runner with the VL agent
    runner = Runner(
        app_name=Config.APP_NAME,
        agent=root_agent,
        session_service=session_service,
    )

    print("=" * 50)
    print("VL Table Extractor Agent")
    print("=" * 50)
    print("Features:")
    print("  1. Define schema - Tell me which fields to extract")
    print("  2. Extract data  - Process PDF files")
    print("")
    print("Type 'quit' to exit")
    print("=" * 50)
    print("")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == "quit":
            break
        if not user_input:
            continue

        print("\nAgent: ", end="", flush=True)

        # Run agent and stream response
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=user_input)],
            ),
        ):
            # Print agent responses
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        print(part.text, end="", flush=True)

        print("\n")


if __name__ == "__main__":
    asyncio.run(main())
