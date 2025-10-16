from fastmcp import FastMCP
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware

from .tools import ads as ads_tools
from .tools import adsets as adsets_tools
from .tools import campaigns as campaigns_tools
from .tools import reporting as reporting_tools
from .tools import audiences as audiences_tools


def create_server():
    mcp = FastMCP("Meta Ads MCP Server")

    ads_tools.register_tools(mcp)
    adsets_tools.register_tools(mcp)
    campaigns_tools.register_tools(mcp)
    reporting_tools.register_tools(mcp)
    audiences_tools.register_tools(mcp)

    mcp.add_middleware(ErrorHandlingMiddleware())

    return mcp


def main():
    server = create_server()
    server.run()
