import json
from typing import Optional, List, Dict

from mcp.server.fastmcp import FastMCP

from meta_ads_mcp.config import config
from meta_ads_mcp.meta_api_client.client import make_graph_api_call
from meta_ads_mcp.meta_api_client.constants import (
    FB_GRAPH_URL,
    DEFAULT_AD_ACCOUNT_FIELDS,
)


def register_tools(mcp: FastMCP):
    @mcp.tool()
    async def list_ad_accounts() -> str:
        """List ad accounts associated with your Facebook account.

        Returns:
            str: JSON string containing list of ad accounts with their names and IDs.
        """
        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/me"
        params = {
            "access_token": access_token,
            "fields": "adaccounts{name,account_id}",
        }

        data = await make_graph_api_call(url, params)

        return json.dumps(data, indent=2)

    @mcp.tool()
    async def get_details_of_ad_account(
        act_id: str,
        fields: Optional[List[str]] = None,
    ) -> str:
        """Get details of a specific ad account.

        Args:
            act_id (str): The ad account ID (format: act_XXXXXXXXXX).
            fields (List[str]): Specific fields to retrieve. If not provided, default fields are used.
                Available fields include: name, business_name, age, account_status, balance,
                amount_spent, attribution_spec, account_id, business, business_city,
                brand_safety_content_filter_levels, currency, created_time, id.

        Returns:
            str: JSON string containing the ad account details.
        """
        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{act_id}"

        effective_fields = fields if fields else DEFAULT_AD_ACCOUNT_FIELDS

        params = {
            "access_token": access_token,
            "fields": ",".join(effective_fields),
        }

        data = await make_graph_api_call(url, params)

        return json.dumps(data, indent=2)

    @mcp.tool()
    async def get_activities_by_adaccount(
        act_id: str,
        fields: Optional[List[str]] = None,
        limit: Optional[int] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        time_range: Optional[Dict[str, str]] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> str:
        """Retrieves activities for a Facebook ad account.

        This function accesses the Facebook Graph API to retrieve information about
        key updates to an ad account and ad objects associated with it. By default,
        this API returns one week's data. Information returned includes major account
        status changes, updates made to budget, campaign, targeting, audiences and more.

        Args:
            act_id (str): The ID of the ad account, prefixed with 'act_', e.g., 'act_1234567890'.
            fields (Optional[List[str]]): A list of specific fields to retrieve. Available fields include:
                'actor_id', 'actor_name', 'application_id', 'application_name', 'changed_data',
                'date_time_in_timezone', 'event_time', 'event_type', 'extra_data', 'object_id',
                'object_name', 'object_type', 'translated_event_type'.
            limit (Optional[int]): Maximum number of activities to return per page.
            after (Optional[str]): Pagination cursor for the next page of results.
            before (Optional[str]): Pagination cursor for the previous page of results.
            time_range (Optional[Dict[str, str]]): A custom time range with 'since' and 'until' dates
                in 'YYYY-MM-DD' format. Example: {'since': '2023-01-01', 'until': '2023-01-31'}.
                This parameter overrides the since/until parameters if both are provided.
            since (Optional[str]): Start date in YYYY-MM-DD format. Ignored if 'time_range' is provided.
            until (Optional[str]): End date in YYYY-MM-DD format. Ignored if 'time_range' is provided.

        Returns:
            str: JSON string containing the requested activities with 'data' and 'paging' keys.
        """
        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{act_id}/activities"
        params = {"access_token": access_token}

        if fields:
            params["fields"] = ",".join(fields)

        if limit is not None:
            params["limit"] = limit

        if after:
            params["after"] = after

        if before:
            params["before"] = before

        # time_range takes precedence over since/until
        if time_range:
            params["time_range"] = json.dumps(time_range)
        else:
            if since:
                params["since"] = since
            if until:
                params["until"] = until

        data = await make_graph_api_call(url, params)

        return json.dumps(data, indent=2)

    @mcp.tool()
    async def get_activities_by_adset(
        adset_id: str,
        fields: Optional[List[str]] = None,
        limit: Optional[int] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        time_range: Optional[Dict[str, str]] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> str:
        """Retrieves activities for a Facebook ad set.

        This function accesses the Facebook Graph API to retrieve information about
        key updates to an ad set. By default, this API returns one week's data.
        Information returned includes status changes, budget updates, targeting changes, and more.

        Args:
            adset_id (str): The ID of the ad set, e.g., '123456789'.
            fields (Optional[List[str]]): A list of specific fields to retrieve. Available fields include:
                'actor_id', 'actor_name', 'application_id', 'application_name', 'changed_data',
                'date_time_in_timezone', 'event_time', 'event_type', 'extra_data', 'object_id',
                'object_name', 'object_type', 'translated_event_type'.
            limit (Optional[int]): Maximum number of activities to return per page.
            after (Optional[str]): Pagination cursor for the next page of results.
            before (Optional[str]): Pagination cursor for the previous page of results.
            time_range (Optional[Dict[str, str]]): A custom time range with 'since' and 'until' dates
                in 'YYYY-MM-DD' format. Example: {'since': '2023-01-01', 'until': '2023-01-31'}.
                This parameter overrides the since/until parameters if both are provided.
            since (Optional[str]): Start date in YYYY-MM-DD format. Ignored if 'time_range' is provided.
            until (Optional[str]): End date in YYYY-MM-DD format. Ignored if 'time_range' is provided.

        Returns:
            str: JSON string containing the requested activities with 'data' and 'paging' keys.
        """
        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{adset_id}/activities"
        params = {"access_token": access_token}

        if fields:
            params["fields"] = ",".join(fields)

        if limit is not None:
            params["limit"] = limit

        if after:
            params["after"] = after

        if before:
            params["before"] = before

        # time_range takes precedence over since/until
        if time_range:
            params["time_range"] = json.dumps(time_range)
        else:
            if since:
                params["since"] = since
            if until:
                params["until"] = until

        data = await make_graph_api_call(url, params)

        return json.dumps(data, indent=2)
