from typing import Any, Dict, List
import json
from urllib.parse import urlencode
import httpx

from meta_ads_mcp.meta_api_client.utils import meta_request_handler
from meta_ads_mcp.meta_api_client.constants import FB_GRAPH_URL


def build_relative_url(object_id: str, endpoint: str, params: Dict[str, Any]) -> str:
    """Build a relative URL for Facebook Graph API batch requests.

    Args:
        object_id: The Facebook object ID (campaign, adset, or ad)
        endpoint: The API endpoint (e.g., "insights")
        params: Query parameters (access_token will be excluded)

    Returns:
        Relative URL string (e.g., "123456/insights?fields=impressions&date_preset=last_30d")
    """
    # Exclude access_token from params as it goes in batch request body
    params_copy = {k: v for k, v in params.items() if k != "access_token"}

    query_string = urlencode(params_copy)
    relative_url = f"{object_id}/{endpoint}"

    if query_string:
        relative_url += f"?{query_string}"

    return relative_url


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


@meta_request_handler
async def make_graph_api_batch_call(
    batch_requests: List[Dict[str, str]], access_token: str
) -> List[Dict[str, Any]]:
    """Make a batch request to the Facebook Graph API.

    Facebook allows up to 50 requests per batch. This function automatically
    splits larger batches into multiple requests.

    Args:
        batch_requests: List of batch request objects, each with:
            - method: HTTP method (usually "GET")
            - relative_url: Relative URL without the base Graph API URL
        access_token: Facebook access token

    Returns:
        List of response objects, each with:
            - code: HTTP status code
            - headers: Response headers
            - body: Response body (as parsed JSON if successful)

    Example:
        batch_requests = [
            {"method": "GET", "relative_url": "123/insights?fields=impressions"},
            {"method": "GET", "relative_url": "456/insights?fields=clicks"}
        ]
    """
    BATCH_LIMIT = 50
    all_responses = []

    # Split into chunks of 50
    for i in range(0, len(batch_requests), BATCH_LIMIT):
        batch_chunk = batch_requests[i : i + BATCH_LIMIT]

        # Prepare batch request
        data = {
            "access_token": access_token,
            "batch": json.dumps(batch_chunk),
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(FB_GRAPH_URL, data=data)

        response.raise_for_status()
        batch_responses = response.json()

        # Parse each response body from JSON string to dict
        for batch_response in batch_responses:
            if batch_response.get("code") == 200 and batch_response.get("body"):
                try:
                    batch_response["body"] = json.loads(batch_response["body"])
                except json.JSONDecodeError:
                    pass  # Keep as string if not valid JSON
            elif batch_response.get("body"):
                try:
                    batch_response["body"] = json.loads(batch_response["body"])
                except json.JSONDecodeError:
                    pass

            all_responses.append(batch_response)

    return all_responses
