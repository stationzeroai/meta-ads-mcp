import asyncio

from mcp.server.fastmcp.server import FastMCP

from meta_ads_mcp.main import create_server


def test_create_server_returns_fastmcp_instance():
    server = create_server()

    assert isinstance(server, FastMCP)


def test_create_server_registers_tools():
    server = create_server()

    assert len(asyncio.run(server.list_tools())) > 0
