import asyncio
import httpx
import pytest

from meta_ads_mcp.meta_api_client.client import make_graph_api_post
from meta_ads_mcp.meta_api_client.errors import (
    AuthenticationError,
    MetaApiError,
)
from meta_ads_mcp.meta_api_client import utils as utils_module


@pytest.fixture(autouse=True)
def _fast_asyncio_sleep(mocker):
    mocker.patch.object(asyncio, "sleep", new=mocker.AsyncMock(return_value=None))


@pytest.mark.asyncio
async def test_make_graph_api_post_returns_response_when_successful(mocker):
    expected_response = {"id": "67890"}
    url = "https://graph.facebook.com/v17.0/12345"
    data = {"name": "Test Ad"}

    mock_response = mocker.Mock()
    mock_response.json.return_value = expected_response
    mock_response.raise_for_status.return_value = None

    mock_client = mocker.AsyncMock()
    mock_client.post.return_value = mock_response

    mock_async_client = mocker.patch(
        "meta_ads_mcp.meta_api_client.client.httpx.AsyncClient"
    )
    mock_async_client.return_value.__aenter__ = mocker.AsyncMock(
        return_value=mock_client
    )
    mock_async_client.return_value.__aexit__ = mocker.AsyncMock(return_value=None)

    response = await make_graph_api_post(url=url, data=data)

    assert response == expected_response
    mock_async_client.assert_called_once()
    mock_client.post.assert_awaited_once_with(url, data=data)
    mock_response.raise_for_status.assert_called_once_with()


@pytest.mark.asyncio
async def test_make_graph_api_post_raises_authentication_error_when_meta_returns_auth_error(
    mocker,
):
    url = "https://graph.facebook.com/v17.0/12345"
    data = {"name": "Test"}
    error_body = {"error": {"code": 190}}

    response = httpx.Response(400, request=httpx.Request("POST", url), json=error_body)
    exception = httpx.HTTPStatusError(
        "client error", request=response.request, response=response
    )

    mock_client = mocker.AsyncMock()
    mock_client.post.side_effect = exception

    mock_async_client = mocker.patch(
        "meta_ads_mcp.meta_api_client.client.httpx.AsyncClient"
    )
    mock_async_client.return_value.__aenter__ = mocker.AsyncMock(
        return_value=mock_client
    )
    mock_async_client.return_value.__aexit__ = mocker.AsyncMock(return_value=None)

    with pytest.raises(AuthenticationError):
        await make_graph_api_post(url=url, data=data)

    mock_client.post.assert_awaited_once_with(url, data=data)


@pytest.mark.asyncio
async def test_make_graph_api_post_raises_meta_api_error_when_response_is_not_json(
    mocker,
):
    url = "https://graph.facebook.com/v17.0/12345"
    data = {"name": "Test"}

    response = httpx.Response(
        500, request=httpx.Request("POST", url), content=b"<!DOCTYPE html>"
    )
    exception = httpx.HTTPStatusError(
        "server error", request=response.request, response=response
    )

    mock_client = mocker.AsyncMock()
    mock_client.post.side_effect = exception

    mock_async_client = mocker.patch(
        "meta_ads_mcp.meta_api_client.client.httpx.AsyncClient"
    )
    mock_async_client.return_value.__aenter__ = mocker.AsyncMock(
        return_value=mock_client
    )
    mock_async_client.return_value.__aexit__ = mocker.AsyncMock(return_value=None)

    with pytest.raises(MetaApiError) as exc:
        await make_graph_api_post(url=url, data=data)

    mock_client.post.assert_awaited_once_with(url, data=data)
    assert "non-JSON response" in str(exc.value)


@pytest.mark.asyncio
async def test_make_graph_api_post_retries_and_succeeds_after_transient_errors(mocker):
    expected_response = {"id": "67890"}
    url = "https://graph.facebook.com/v17.0/12345"
    data = {"name": "Test"}

    retry_error_body = {"error": {"code": 4}}
    retry_response_one = httpx.Response(
        500, request=httpx.Request("POST", url), json=retry_error_body
    )
    retry_response_two = httpx.Response(
        500, request=httpx.Request("POST", url), json=retry_error_body
    )
    retry_exception_one = httpx.HTTPStatusError(
        "server error", request=retry_response_one.request, response=retry_response_one
    )
    retry_exception_two = httpx.HTTPStatusError(
        "server error", request=retry_response_two.request, response=retry_response_two
    )

    mock_response = mocker.Mock()
    mock_response.json.return_value = expected_response
    mock_response.raise_for_status.return_value = None

    mock_client = mocker.AsyncMock()
    mock_client.post.side_effect = [
        retry_exception_one,
        retry_exception_two,
        mock_response,
    ]

    mock_async_client = mocker.patch(
        "meta_ads_mcp.meta_api_client.client.httpx.AsyncClient"
    )
    mock_async_client.return_value.__aenter__ = mocker.AsyncMock(
        return_value=mock_client
    )
    mock_async_client.return_value.__aexit__ = mocker.AsyncMock(return_value=None)

    response = await make_graph_api_post(url=url, data=data)

    assert response == expected_response
    assert mock_client.post.await_count == 3


@pytest.mark.asyncio
async def test_make_graph_api_post_raises_error_after_exhausting_retries(mocker):
    url = "https://graph.facebook.com/v17.0/12345"
    data = {"name": "Test"}
    error_body = {"error": {"code": 4}}

    errors = []
    for _ in range(utils_module.config.MAX_RETRIES):
        retry_response = httpx.Response(
            500, request=httpx.Request("POST", url), json=error_body
        )
        errors.append(
            httpx.HTTPStatusError(
                "server error",
                request=retry_response.request,
                response=retry_response,
            )
        )

    mock_client = mocker.AsyncMock()
    mock_client.post.side_effect = errors

    mock_async_client = mocker.patch(
        "meta_ads_mcp.meta_api_client.client.httpx.AsyncClient"
    )
    mock_async_client.return_value.__aenter__ = mocker.AsyncMock(
        return_value=mock_client
    )
    mock_async_client.return_value.__aexit__ = mocker.AsyncMock(return_value=None)

    with pytest.raises(MetaApiError):
        await make_graph_api_post(url=url, data=data)

    assert mock_client.post.await_count == utils_module.config.MAX_RETRIES
