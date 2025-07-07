import argparse
from fastmcp import FastMCP
from src.tools import bootstrap_server
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware

from dotenv import load_dotenv
import os
load_dotenv()

def main():
    # Parse command-line options for host, port, and path
    parser = argparse.ArgumentParser(description="Run the ExpenseProcessor MCP server")
    parser.add_argument("--host", type=str, default="0.0.0.0",
                        help="Host interface to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000,
                        help="Port to listen on (default: 8000)")
    parser.add_argument("--path", type=str, default="/mcp",
                        help="HTTP path for the MCP endpoint (default: /mcp)")
    args = parser.parse_args()

    # Validate required environment variables
    if not os.getenv("SLACK_BOT_TOKEN") or not os.getenv("EXPENSE_SPREADSHEET_ID"):
        raise RuntimeError("SLACK_BOT_TOKEN and EXPENSE_SPREADSHEET_ID must be set")

    # Bootstrap and configure the FastMCP server
    mcp_server: FastMCP = bootstrap_server()

    # Add global middleware
    mcp_server.add_middleware(LoggingMiddleware())
    mcp_server.add_middleware(ErrorHandlingMiddleware())

    # Run with built-in Streamable HTTP transport
    mcp_server.run(
        transport="http",         # Streamable HTTP transport
        host=args.host,           # Bind interface
        port=args.port,           # Listening port
        path=args.path,           # MCP endpoint path
        log_level="info",         # Optional log-level override
    )

if __name__ == "__main__":
    main()
