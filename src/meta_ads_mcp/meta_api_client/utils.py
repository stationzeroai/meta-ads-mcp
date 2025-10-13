from typing import Dict
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import json
import httpx

from meta_ads_mcp.meta_api_client.errors import (
    AuthenticationError,
    MetaApiError,
    NotFoundError,
    ServerError,
    TooManyRequestsError,
)

from meta_ads_mcp.config import config

EXCEPTION_MAPPING = {
    4: TooManyRequestsError,
    17: TooManyRequestsError,
    1: ServerError,
    2: ServerError,
    3: ServerError,
    190: AuthenticationError,
    102: AuthenticationError,
    104: AuthenticationError,
    803: NotFoundError,
    100: ServerError,
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
    if not "error" in response:
        return

    error_info = response["error"]
    error_code = error_info.get("code", None)
    exception_class = EXCEPTION_MAPPING.get(error_code, MetaApiError)

    raise exception_class(response)
