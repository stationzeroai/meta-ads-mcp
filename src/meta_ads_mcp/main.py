from mcp.server.fastmcp import FastMCP

from .tools import ads as ads_tools
from .tools import adsets as adsets_tools
from .tools import campaigns as campaigns_tools


def create_server():
    mcp = FastMCP("Meta Ads MCP Server")

    ads_tools.register_tools(mcp)
    adsets_tools.register_tools(mcp)
    campaigns_tools.register_tools(mcp)

    return mcp


def main():
    server = create_server()
    server.run()
