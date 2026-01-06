import asyncio

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from orchestrator.agent import root_agent

# App name for session management
APP_NAME = "table-filler"


async def main():
    # Initialize session service
    session_service = InMemorySessionService()

    # Create a new session
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id="user-1",
    )

    # Create Runner with the orchestrator agent
    runner = Runner(
        app_name=APP_NAME,
        agent=root_agent,
        session_service=session_service,
    )

    print("=" * 50)
    print("Contract Digitization Assistant")
    print("=" * 50)
    print("Features:")
    print("  1. Configure fields - Tell me which fields to extract")
    print("  2. Process PDFs     - Provide PDF file paths")
    print("  3. Export Excel     - Export results to Excel")
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
            new_message=user_input,
        ):
            # Print agent responses
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        print(part.text, end="", flush=True)

        print("\n")


if __name__ == "__main__":
    asyncio.run(main())
