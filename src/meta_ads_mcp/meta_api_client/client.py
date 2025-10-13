from typing import Any, Dict
import httpx

from meta_ads_mcp.meta_api_client.utils import meta_request_handler


@meta_request_handler
async def make_graph_api_call(url: str, params: Dict[str, Any]) -> Dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)

    response.raise_for_status()

    return response.json()


@meta_request_handler
async def make_graph_api_post(url: str, data: Dict[str, Any]) -> Dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=data)

    response.raise_for_status()
    response_json = response.json()

    return response_json
