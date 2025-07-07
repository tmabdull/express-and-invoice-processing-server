import asyncio
from fastmcp import Client

async def main():
    async with Client("http://localhost:8000/mcp") as client:
        # List available tools
        tools = await client.list_tools()
        print("Tools:", tools)

        # Run the end-to-end workflow
        result = await client.call_tool("run_full_workflow", {})
        print("Workflow completed:", result)

if __name__ == "__main__":
    asyncio.run(main())