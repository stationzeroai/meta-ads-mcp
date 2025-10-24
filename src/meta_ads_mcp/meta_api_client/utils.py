from typing import Dict
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import json
import httpx
import logging

from meta_ads_mcp.meta_api_client.errors import (
    AuthenticationError,
    MetaApiError,
    NotFoundError,
    ServerError,
    TooManyRequestsError,
)

from meta_ads_mcp.config import config

logger = logging.getLogger(__name__)

EXCEPTION_MAPPING = {
    4: TooManyRequestsError,
    17: TooManyRequestsError,
    190: AuthenticationError,
    102: AuthenticationError,
    104: AuthenticationError,
    803: NotFoundError,
}


def meta_request_handler(func):
    @retry(
        reraise=True,
        stop=stop_after_attempt(config.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=(
            retry_if_exception_type(ServerError)
            | retry_if_exception_type(TooManyRequestsError)
        ),
    )
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except httpx.HTTPStatusError as e:
            logger.debug(f"HTTP error occurred: {str(e)}")

            try:
                error_response = e.response.json()
            except json.JSONDecodeError:
                raise MetaApiError(
                    f"HTTP error occurred: {str(e)} with non-JSON response"
                )

            handle_error_response(error_response)

            raise MetaApiError(f"HTTP error occurred: {str(e)}")

    return wrapper


def handle_error_response(response: Dict) -> None:
    if "error" not in response:
        return

    error_info = response["error"]
    error_code = error_info.get("code", None)
    exception_class = EXCEPTION_MAPPING.get(error_code, MetaApiError)

    # Capture full error details for better debugging
    detailed_error = {
        "error": {
            "message": error_info.get("message", "Unknown error"),
            "code": error_code,
        }
    }

    # Add optional fields if present
    if "error_subcode" in error_info:
        detailed_error["error"]["error_subcode"] = error_info["error_subcode"]
    if "error_user_title" in error_info:
        detailed_error["error"]["error_user_title"] = error_info["error_user_title"]
    if "error_user_msg" in error_info:
        detailed_error["error"]["error_user_msg"] = error_info["error_user_msg"]
    if "fbtrace_id" in error_info:
        detailed_error["error"]["fbtrace_id"] = error_info["fbtrace_id"]

    raise exception_class(detailed_error)
