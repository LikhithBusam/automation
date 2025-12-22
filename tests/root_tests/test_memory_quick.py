import asyncio
from src.autogen_adapters.conversation_manager import ConversationManager


async def test_memory():
    mgr = ConversationManager()
    await mgr.initialize()
    mem = mgr.function_registry.tool_manager.tools["memory"]

    result = await mem._store_memory({"key": "test123", "content": "test content", "type": "test"})

    print("Store Result:", result)

    if result.get("success"):
        retrieve = await mem._retrieve_memory({"key": "test123"})
        print("Retrieve Result:", retrieve)


asyncio.run(test_memory())
