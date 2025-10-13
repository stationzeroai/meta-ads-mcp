from mcp.server.fastmcp import FastMCP

from .logger import *


def main():
    server = FastMCP("Meta Ads MCP Server")
    server.run()
