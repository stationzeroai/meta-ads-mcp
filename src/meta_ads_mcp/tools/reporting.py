import json
import httpx
from typing import Optional, List, Dict, Any

from fastmcp import FastMCP

from meta_ads_mcp.config import config
from meta_ads_mcp.meta_api_client.client import (
    make_graph_api_call,
    make_graph_api_batch_call,
    build_relative_url,
)
from meta_ads_mcp.meta_api_client.constants import FB_GRAPH_URL


def _prepare_params(base_params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    params = base_params.copy()
    for key, value in kwargs.items():
        if value is not None:
            if key in ["filtering", "time_range", "time_ranges"] and isinstance(
                value, (list, dict)
            ):
                params[key] = json.dumps(value)
            elif key == "fields" and isinstance(value, list):
                params[key] = ",".join(value)
            elif key in [
                "action_attribution_windows",
                "action_breakdowns",
                "breakdowns",
            ] and isinstance(value, list):
                params[key] = ",".join(value)
            else:
                params[key] = value
    return params


def _build_insights_params(
    params: Dict[str, Any],
    fields: Optional[List[str]] = None,
    date_preset: Optional[str] = None,
    time_range: Optional[Dict[str, str]] = None,
    time_ranges: Optional[List[Dict[str, str]]] = None,
    time_increment: Optional[str] = None,
    level: Optional[str] = None,
    action_attribution_windows: Optional[List[str]] = None,
    action_breakdowns: Optional[List[str]] = None,
    action_report_time: Optional[str] = None,
    breakdowns: Optional[List[str]] = None,
    default_summary: bool = False,
    use_account_attribution_setting: bool = False,
    use_unified_attribution_setting: bool = True,
    filtering: Optional[List[dict]] = None,
    sort: Optional[str] = None,
    limit: Optional[int] = None,
    after: Optional[str] = None,
    before: Optional[str] = None,
    offset: Optional[int] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    locale: Optional[str] = None,
) -> Dict[str, Any]:
    params = _prepare_params(
        params,
        fields=fields,
        level=level,
        action_attribution_windows=action_attribution_windows,
        action_breakdowns=action_breakdowns,
        action_report_time=action_report_time,
        breakdowns=breakdowns,
        filtering=filtering,
        sort=sort,
        limit=limit,
        after=after,
        before=before,
        offset=offset,
        locale=locale,
    )

    time_params_provided = time_range or time_ranges or since or until
    if not time_params_provided and date_preset:
        params["date_preset"] = date_preset
    if time_range:
        params["time_range"] = json.dumps(time_range)
    if time_ranges:
        params["time_ranges"] = json.dumps(time_ranges)
    if time_increment and time_increment != "all_days":
        params["time_increment"] = time_increment

    if not time_range and not time_ranges:
        if since:
            params["since"] = since
        if until:
            params["until"] = until

    if default_summary:
        params["default_summary"] = "true"
    if use_account_attribution_setting:
        params["use_account_attribution_setting"] = "true"
    if use_unified_attribution_setting:
        params["use_unified_attribution_setting"] = "true"

    return params


def register_tools(mcp: FastMCP):
    @mcp.tool()
    async def get_adaccount_insights(
        act_id: str,
        fields: Optional[List[str]] = None,
        date_preset: str = "last_30d",
        time_range: Optional[Dict[str, str]] = None,
        time_ranges: Optional[List[Dict[str, str]]] = None,
        time_increment: str = "all_days",
        level: str = "account",
        action_attribution_windows: Optional[List[str]] = None,
        action_breakdowns: Optional[List[str]] = None,
        action_report_time: Optional[str] = None,
        breakdowns: Optional[List[str]] = None,
        default_summary: bool = False,
        use_account_attribution_setting: bool = False,
        use_unified_attribution_setting: bool = True,
        filtering: Optional[List[dict]] = None,
        sort: Optional[str] = None,
        limit: Optional[int] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        offset: Optional[int] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        locale: Optional[str] = None,
    ) -> str:
        """Retrieves performance insights for a specified Facebook ad account.

        Args:
            act_id (str): The target ad account ID, prefixed with 'act_', e.g., 'act_1234567890'.
            fields (Optional[List[str]]): Specific metrics and fields to retrieve. Common examples:
                'account_currency', 'account_id', 'account_name', 'actions', 'clicks', 'conversions',
                'cpc', 'cpm', 'cpp', 'ctr', 'frequency', 'impressions', 'reach', 'spend', 'purchase_roas'.
            date_preset (str): Predefined relative time range. Options: 'today', 'yesterday', 'this_month',
                'last_month', 'this_quarter', 'maximum', 'last_3d', 'last_7d', 'last_14d', 'last_28d',
                'last_30d', 'last_90d', 'last_week_mon_sun', 'last_week_sun_sat', 'last_quarter',
                'last_year', 'this_week_mon_today', 'this_week_sun_today', 'this_year'. Default: 'last_30d'.
            time_range (Optional[Dict[str, str]]): Specific time range {'since': 'YYYY-MM-DD', 'until': 'YYYY-MM-DD'}.
            time_ranges (Optional[List[Dict[str, str]]]): Array of time range objects for comparison.
            time_increment (str): Time granularity. Integer (1-90) for days, 'monthly', or 'all_days'. Default: 'all_days'.
            level (str): Aggregation level: 'account', 'campaign', 'adset', 'ad'. Default: 'account'.
            action_attribution_windows (Optional[List[str]]): Attribution windows: '1d_view', '7d_view',
                '28d_view', '1d_click', '7d_click', '28d_click', 'dda', 'default'.
            action_breakdowns (Optional[List[str]]): Segments 'actions' results. Examples: 'action_device', 'action_type'.
            action_report_time (Optional[str]): When actions are counted: 'impression', 'conversion', 'mixed'. Default: 'mixed'.
            breakdowns (Optional[List[str]]): Segments results by dimensions: 'age', 'gender', 'country', 'region',
                'impression_device', 'publisher_platform', 'platform_position', 'device_platform'.
            default_summary (bool): Include additional summary row. Default: False.
            use_account_attribution_setting (bool): Use ad account attribution settings. Default: False.
            use_unified_attribution_setting (bool): Use unified attribution settings. Default: True.
            filtering (Optional[List[dict]]): Filter objects with 'field', 'operator', 'value' keys.
            sort (Optional[str]): Sort field and direction: '{field}_ascending' or '{field}_descending'.
            limit (Optional[int]): Maximum results per page.
            after (Optional[str]): Pagination cursor for next page.
            before (Optional[str]): Pagination cursor for previous page.
            offset (Optional[int]): Number of results to skip.
            since (Optional[str]): Start timestamp for time-based pagination.
            until (Optional[str]): End timestamp for time-based pagination.
            locale (Optional[str]): Locale for text responses (e.g., 'en_US').

        Returns:
            str: JSON string containing ad account insights with 'data' and 'paging' keys.
        """
        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{act_id}/insights"
        params = {"access_token": access_token}

        params = _build_insights_params(
            params=params,
            fields=fields,
            date_preset=date_preset,
            time_range=time_range,
            time_ranges=time_ranges,
            time_increment=time_increment,
            level=level,
            action_attribution_windows=action_attribution_windows,
            action_breakdowns=action_breakdowns,
            action_report_time=action_report_time,
            breakdowns=breakdowns,
            default_summary=default_summary,
            use_account_attribution_setting=use_account_attribution_setting,
            use_unified_attribution_setting=use_unified_attribution_setting,
            filtering=filtering,
            sort=sort,
            limit=limit,
            after=after,
            before=before,
            offset=offset,
            since=since,
            until=until,
            locale=locale,
        )

        data = await make_graph_api_call(url, params)

        return json.dumps(data, indent=2)

    @mcp.tool()
    async def get_campaign_insights_by_id(
        campaign_id: str,
        fields: Optional[List[str]] = None,
        date_preset: str = "last_30d",
        time_range: Optional[Dict[str, str]] = None,
        time_ranges: Optional[List[Dict[str, str]]] = None,
        time_increment: str = "all_days",
        action_attribution_windows: Optional[List[str]] = None,
        action_breakdowns: Optional[List[str]] = None,
        action_report_time: Optional[str] = None,
        breakdowns: Optional[List[str]] = None,
        default_summary: bool = False,
        use_account_attribution_setting: bool = False,
        use_unified_attribution_setting: bool = True,
        level: Optional[str] = None,
        filtering: Optional[List[dict]] = None,
        sort: Optional[str] = None,
        limit: Optional[int] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        offset: Optional[int] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        locale: Optional[str] = None,
    ) -> str:
        """Retrieves performance insights for a specific Facebook ad campaign.

        Args:
            campaign_id (str): The ID of the target Facebook ad campaign.
            fields (Optional[List[str]]): Specific metrics. Examples: 'campaign_name', 'account_id',
                'impressions', 'clicks', 'spend', 'ctr', 'reach', 'actions', 'objective',
                'cost_per_action_type', 'conversions', 'cpc', 'cpm', 'cpp', 'frequency'.
            date_preset (str): Predefined relative time range. Default: 'last_30d'.
            time_range (Optional[Dict[str, str]]): Specific time range {'since':'YYYY-MM-DD','until':'YYYY-MM-DD'}.
            time_ranges (Optional[List[Dict[str, str]]]): Array of time range objects for comparison.
            time_increment (str): Time granularity. Default: 'all_days'.
            action_attribution_windows (Optional[List[str]]): Attribution windows.
            action_breakdowns (Optional[List[str]]): Segments 'actions' results.
            action_report_time (Optional[str]): When actions are counted. Default: 'mixed'.
            breakdowns (Optional[List[str]]): Segments results by dimensions.
            default_summary (bool): Include additional summary row. Default: False.
            use_account_attribution_setting (bool): Use ad account attribution settings. Default: False.
            use_unified_attribution_setting (bool): Use unified attribution settings. Default: True.
            level (Optional[str]): Aggregation level: 'campaign', 'adset', 'ad'. Default: 'campaign'.
            filtering (Optional[List[dict]]): Filter objects.
            sort (Optional[str]): Sort field and direction.
            limit (Optional[int]): Maximum results per page.
            after (Optional[str]): Pagination cursor for next page.
            before (Optional[str]): Pagination cursor for previous page.
            offset (Optional[int]): Number of results to skip.
            since (Optional[str]): Start timestamp.
            until (Optional[str]): End timestamp.
            locale (Optional[str]): Locale for text responses.

        Returns:
            str: JSON string containing campaign insights with 'data' and 'paging' keys.
        """
        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{campaign_id}/insights"
        params = {"access_token": access_token}

        effective_level = level if level else "campaign"

        params = _build_insights_params(
            params=params,
            fields=fields,
            date_preset=date_preset,
            time_range=time_range,
            time_ranges=time_ranges,
            time_increment=time_increment,
            level=effective_level,
            action_attribution_windows=action_attribution_windows,
            action_breakdowns=action_breakdowns,
            action_report_time=action_report_time,
            breakdowns=breakdowns,
            default_summary=default_summary,
            use_account_attribution_setting=use_account_attribution_setting,
            use_unified_attribution_setting=use_unified_attribution_setting,
            filtering=filtering,
            sort=sort,
            limit=limit,
            after=after,
            before=before,
            offset=offset,
            since=since,
            until=until,
            locale=locale,
        )

        data = await make_graph_api_call(url, params)

        return json.dumps(data, indent=2)

    @mcp.tool()
    async def get_adset_insights_by_id(
        adset_id: str,
        fields: Optional[List[str]] = None,
        date_preset: str = "last_30d",
        time_range: Optional[Dict[str, str]] = None,
        time_ranges: Optional[List[Dict[str, str]]] = None,
        time_increment: str = "all_days",
        action_attribution_windows: Optional[List[str]] = None,
        action_breakdowns: Optional[List[str]] = None,
        action_report_time: Optional[str] = None,
        breakdowns: Optional[List[str]] = None,
        default_summary: bool = False,
        use_account_attribution_setting: bool = False,
        use_unified_attribution_setting: bool = True,
        level: Optional[str] = None,
        filtering: Optional[List[dict]] = None,
        sort: Optional[str] = None,
        limit: Optional[int] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        offset: Optional[int] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        locale: Optional[str] = None,
    ) -> str:
        """Retrieves performance insights for a specific Facebook ad set.

        Args:
            adset_id (str): The ID of the target ad set.
            fields (Optional[List[str]]): Specific metrics. Examples: 'adset_name', 'campaign_name',
                'account_id', 'impressions', 'clicks', 'spend', 'ctr', 'reach', 'frequency',
                'actions', 'conversions', 'cpc', 'cpm', 'cpp', 'cost_per_action_type'.
            date_preset (str): Predefined relative time range. Default: 'last_30d'.
            time_range (Optional[Dict[str, str]]): Specific time range.
            time_ranges (Optional[List[Dict[str, str]]]): Array of time range objects.
            time_increment (str): Time granularity. Default: 'all_days'.
            action_attribution_windows (Optional[List[str]]): Attribution windows.
            action_breakdowns (Optional[List[str]]): Segments 'actions' results.
            action_report_time (Optional[str]): When actions are counted. Default: 'mixed'.
            breakdowns (Optional[List[str]]): Segments results by dimensions.
            default_summary (bool): Include additional summary row. Default: False.
            use_account_attribution_setting (bool): Use ad account attribution settings. Default: False.
            use_unified_attribution_setting (bool): Use unified attribution settings. Default: True.
            level (Optional[str]): Aggregation level: 'adset', 'ad'. Default: 'adset'.
            filtering (Optional[List[dict]]): Filter objects.
            sort (Optional[str]): Sort field and direction.
            limit (Optional[int]): Maximum results per page.
            after (Optional[str]): Pagination cursor for next page.
            before (Optional[str]): Pagination cursor for previous page.
            offset (Optional[int]): Number of results to skip.
            since (Optional[str]): Start timestamp.
            until (Optional[str]): End timestamp.
            locale (Optional[str]): Locale for text responses.

        Returns:
            str: JSON string containing ad set insights with 'data' and 'paging' keys.
        """
        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{adset_id}/insights"
        params = {"access_token": access_token}

        effective_level = level if level else "adset"

        params = _build_insights_params(
            params=params,
            fields=fields,
            date_preset=date_preset,
            time_range=time_range,
            time_ranges=time_ranges,
            time_increment=time_increment,
            level=effective_level,
            action_attribution_windows=action_attribution_windows,
            action_breakdowns=action_breakdowns,
            action_report_time=action_report_time,
            breakdowns=breakdowns,
            default_summary=default_summary,
            use_account_attribution_setting=use_account_attribution_setting,
            use_unified_attribution_setting=use_unified_attribution_setting,
            filtering=filtering,
            sort=sort,
            limit=limit,
            after=after,
            before=before,
            offset=offset,
            since=since,
            until=until,
            locale=locale,
        )

        data = await make_graph_api_call(url, params)

        return json.dumps(data, indent=2)

    @mcp.tool()
    async def get_ad_insights_by_id(
        ad_id: str,
        fields: Optional[List[str]] = None,
        date_preset: str = "last_30d",
        time_range: Optional[Dict[str, str]] = None,
        time_ranges: Optional[List[Dict[str, str]]] = None,
        time_increment: str = "all_days",
        action_attribution_windows: Optional[List[str]] = None,
        action_breakdowns: Optional[List[str]] = None,
        action_report_time: Optional[str] = None,
        breakdowns: Optional[List[str]] = None,
        default_summary: bool = False,
        use_account_attribution_setting: bool = False,
        use_unified_attribution_setting: bool = True,
        level: Optional[str] = None,
        filtering: Optional[List[dict]] = None,
        sort: Optional[str] = None,
        limit: Optional[int] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        offset: Optional[int] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        locale: Optional[str] = None,
    ) -> str:
        """Retrieves detailed performance insights for a specific Facebook ad.

        Args:
            ad_id (str): The ID of the target ad.
            fields (Optional[List[str]]): Specific metrics. Examples: 'ad_name', 'adset_name',
                'campaign_name', 'account_id', 'impressions', 'clicks', 'spend', 'ctr', 'cpc',
                'cpm', 'cpp', 'reach', 'frequency', 'actions', 'conversions', 'cost_per_action_type',
                'inline_link_clicks', 'inline_post_engagement', 'unique_clicks', 'video_p25_watched_actions',
                'video_p50_watched_actions', 'video_p75_watched_actions', 'video_p100_watched_actions',
                'website_ctr', 'website_purchases'.
            date_preset (str): Predefined relative time range. Default: 'last_30d'.
            time_range (Optional[Dict[str, str]]): Specific time range.
            time_ranges (Optional[List[Dict[str, str]]]): Array of time range objects.
            time_increment (str): Time granularity. Default: 'all_days'.
            action_attribution_windows (Optional[List[str]]): Attribution windows.
            action_breakdowns (Optional[List[str]]): Segments 'actions' results.
            action_report_time (Optional[str]): When actions are counted. Default: 'mixed'.
            breakdowns (Optional[List[str]]): Segments results by dimensions.
            default_summary (bool): Include additional summary row. Default: False.
            use_account_attribution_setting (bool): Use ad account attribution settings. Default: False.
            use_unified_attribution_setting (bool): Use unified attribution settings. Default: True.
            level (Optional[str]): Aggregation level. Should typically be 'ad'. Default: 'ad'.
            filtering (Optional[List[dict]]): Filter objects.
            sort (Optional[str]): Sort field and direction.
            limit (Optional[int]): Maximum results per page.
            after (Optional[str]): Pagination cursor for next page.
            before (Optional[str]): Pagination cursor for previous page.
            offset (Optional[int]): Number of results to skip.
            since (Optional[str]): Start timestamp.
            until (Optional[str]): End timestamp.
            locale (Optional[str]): Locale for text responses.

        Returns:
            str: JSON string containing ad insights with 'data' and 'paging' keys.
        """
        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{ad_id}/insights"
        params = {"access_token": access_token}

        effective_level = level if level else "ad"

        params = _build_insights_params(
            params=params,
            fields=fields,
            date_preset=date_preset,
            time_range=time_range,
            time_ranges=time_ranges,
            time_increment=time_increment,
            level=effective_level,
            action_attribution_windows=action_attribution_windows,
            action_breakdowns=action_breakdowns,
            action_report_time=action_report_time,
            breakdowns=breakdowns,
            default_summary=default_summary,
            use_account_attribution_setting=use_account_attribution_setting,
            use_unified_attribution_setting=use_unified_attribution_setting,
            filtering=filtering,
            sort=sort,
            limit=limit,
            after=after,
            before=before,
            offset=offset,
            since=since,
            until=until,
            locale=locale,
        )

        data = await make_graph_api_call(url, params)

        return json.dumps(data, indent=2)

    @mcp.tool()
    async def get_multiple_campaigns_insights_by_ids(
        campaign_ids: List[str],
        fields: Optional[List[str]] = None,
        date_preset: str = "last_30d",
        time_range: Optional[Dict[str, str]] = None,
        time_ranges: Optional[List[Dict[str, str]]] = None,
        time_increment: str = "all_days",
        action_attribution_windows: Optional[List[str]] = None,
        action_breakdowns: Optional[List[str]] = None,
        action_report_time: Optional[str] = None,
        breakdowns: Optional[List[str]] = None,
        default_summary: bool = False,
        use_account_attribution_setting: bool = False,
        use_unified_attribution_setting: bool = True,
        filtering: Optional[List[dict]] = None,
        sort: Optional[str] = None,
        limit: Optional[int] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        offset: Optional[int] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        locale: Optional[str] = None,
    ) -> Dict:
        """Retrieves performance insights for multiple Facebook ad campaigns in batch.

        Uses Facebook's Batch API to efficiently fetch insights for multiple campaigns
        in a single request (up to 50 campaigns per API call). Handles errors per
        campaign without failing the entire batch.

        Args:
            campaign_ids (List[str]): List of campaign IDs to fetch insights for.
            fields (Optional[List[str]]): Specific metrics. Examples: 'campaign_name', 'account_id',
                'impressions', 'clicks', 'spend', 'ctr', 'reach', 'actions', 'objective',
                'cost_per_action_type', 'conversions', 'cpc', 'cpm', 'cpp', 'frequency'.
            date_preset (str): Predefined relative time range. Default: 'last_30d'.
            time_range (Optional[Dict[str, str]]): Specific time range {'since':'YYYY-MM-DD','until':'YYYY-MM-DD'}.
            time_ranges (Optional[List[Dict[str, str]]]): Array of time range objects for comparison.
            time_increment (str): Time granularity. Default: 'all_days'.
            action_attribution_windows (Optional[List[str]]): Attribution windows.
            action_breakdowns (Optional[List[str]]): Segments 'actions' results.
            action_report_time (Optional[str]): When actions are counted. Default: 'mixed'.
            breakdowns (Optional[List[str]]): Segments results by dimensions.
            default_summary (bool): Include additional summary row. Default: False.
            use_account_attribution_setting (bool): Use ad account attribution settings. Default: False.
            use_unified_attribution_setting (bool): Use unified attribution settings. Default: True.
            filtering (Optional[List[dict]]): Filter objects.
            sort (Optional[str]): Sort field and direction.
            limit (Optional[int]): Maximum results per page.
            after (Optional[str]): Pagination cursor for next page.
            before (Optional[str]): Pagination cursor for previous page.
            offset (Optional[int]): Number of results to skip.
            since (Optional[str]): Start timestamp.
            until (Optional[str]): End timestamp.
            locale (Optional[str]): Locale for text responses.

        Returns:
            Dict: Dictionary containing:
                - 'results' (List[Dict]): List of results, each with:
                    - 'campaign_id' (str): The campaign ID
                    - 'insights' (Dict): Insights data if successful
                    - 'error' (str|null): Error message if failed, null if successful
                - 'summary' (Dict): Summary with:
                    - 'total_requested' (int): Number of campaigns requested
                    - 'successful' (int): Number of successful fetches
                    - 'failed' (int): Number of failed fetches
        """
        access_token = config.META_ACCESS_TOKEN

        # Build params for insights request
        params = {"access_token": access_token}
        params = _build_insights_params(
            params=params,
            fields=fields,
            date_preset=date_preset,
            time_range=time_range,
            time_ranges=time_ranges,
            time_increment=time_increment,
            level="campaign",
            action_attribution_windows=action_attribution_windows,
            action_breakdowns=action_breakdowns,
            action_report_time=action_report_time,
            breakdowns=breakdowns,
            default_summary=default_summary,
            use_account_attribution_setting=use_account_attribution_setting,
            use_unified_attribution_setting=use_unified_attribution_setting,
            filtering=filtering,
            sort=sort,
            limit=limit,
            after=after,
            before=before,
            offset=offset,
            since=since,
            until=until,
            locale=locale,
        )

        # Build batch requests
        batch_requests = []
        for campaign_id in campaign_ids:
            relative_url = build_relative_url(campaign_id, "insights", params)
            batch_requests.append({"method": "GET", "relative_url": relative_url})

        # Execute batch request
        batch_responses = await make_graph_api_batch_call(batch_requests, access_token)

        # Parse responses
        results = []
        successful = 0
        failed = 0

        for i, batch_response in enumerate(batch_responses):
            campaign_id = campaign_ids[i]
            code = batch_response.get("code")

            if code == 200:
                results.append({
                    "campaign_id": campaign_id,
                    "insights": batch_response.get("body"),
                    "error": None,
                })
                successful += 1
            else:
                error_body = batch_response.get("body", {})
                error_message = error_body.get("error", {}).get("message", f"HTTP {code}")
                results.append({
                    "campaign_id": campaign_id,
                    "insights": None,
                    "error": error_message,
                })
                failed += 1

        return {
            "results": results,
            "summary": {
                "total_requested": len(campaign_ids),
                "successful": successful,
                "failed": failed,
            },
        }

    @mcp.tool()
    async def get_multiple_adsets_insights_by_ids(
        adset_ids: List[str],
        fields: Optional[List[str]] = None,
        date_preset: str = "last_30d",
        time_range: Optional[Dict[str, str]] = None,
        time_ranges: Optional[List[Dict[str, str]]] = None,
        time_increment: str = "all_days",
        action_attribution_windows: Optional[List[str]] = None,
        action_breakdowns: Optional[List[str]] = None,
        action_report_time: Optional[str] = None,
        breakdowns: Optional[List[str]] = None,
        default_summary: bool = False,
        use_account_attribution_setting: bool = False,
        use_unified_attribution_setting: bool = True,
        filtering: Optional[List[dict]] = None,
        sort: Optional[str] = None,
        limit: Optional[int] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        offset: Optional[int] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        locale: Optional[str] = None,
    ) -> Dict:
        """Retrieves performance insights for multiple Facebook ad sets in batch.

        Uses Facebook's Batch API to efficiently fetch insights for multiple ad sets
        in a single request (up to 50 ad sets per API call). Handles errors per
        ad set without failing the entire batch.

        Args:
            adset_ids (List[str]): List of ad set IDs to fetch insights for.
            fields (Optional[List[str]]): Specific metrics. Examples: 'adset_name', 'account_id',
                'impressions', 'clicks', 'spend', 'ctr', 'reach', 'actions', 'objective',
                'cost_per_action_type', 'conversions', 'cpc', 'cpm', 'cpp', 'frequency'.
            date_preset (str): Predefined relative time range. Default: 'last_30d'.
            time_range (Optional[Dict[str, str]]): Specific time range {'since':'YYYY-MM-DD','until':'YYYY-MM-DD'}.
            time_ranges (Optional[List[Dict[str, str]]]): Array of time range objects for comparison.
            time_increment (str): Time granularity. Default: 'all_days'.
            action_attribution_windows (Optional[List[str]]): Attribution windows.
            action_breakdowns (Optional[List[str]]): Segments 'actions' results.
            action_report_time (Optional[str]): When actions are counted. Default: 'mixed'.
            breakdowns (Optional[List[str]]): Segments results by dimensions.
            default_summary (bool): Include additional summary row. Default: False.
            use_account_attribution_setting (bool): Use ad account attribution settings. Default: False.
            use_unified_attribution_setting (bool): Use unified attribution settings. Default: True.
            filtering (Optional[List[dict]]): Filter objects.
            sort (Optional[str]): Sort field and direction.
            limit (Optional[int]): Maximum results per page.
            after (Optional[str]): Pagination cursor for next page.
            before (Optional[str]): Pagination cursor for previous page.
            offset (Optional[int]): Number of results to skip.
            since (Optional[str]): Start timestamp.
            until (Optional[str]): End timestamp.
            locale (Optional[str]): Locale for text responses.

        Returns:
            Dict: Dictionary containing:
                - 'results' (List[Dict]): List of results, each with:
                    - 'adset_id' (str): The ad set ID
                    - 'insights' (Dict): Insights data if successful
                    - 'error' (str|null): Error message if failed, null if successful
                - 'summary' (Dict): Summary with:
                    - 'total_requested' (int): Number of ad sets requested
                    - 'successful' (int): Number of successful fetches
                    - 'failed' (int): Number of failed fetches
        """
        access_token = config.META_ACCESS_TOKEN

        # Build params for insights request
        params = {"access_token": access_token}
        params = _build_insights_params(
            params=params,
            fields=fields,
            date_preset=date_preset,
            time_range=time_range,
            time_ranges=time_ranges,
            time_increment=time_increment,
            level="adset",
            action_attribution_windows=action_attribution_windows,
            action_breakdowns=action_breakdowns,
            action_report_time=action_report_time,
            breakdowns=breakdowns,
            default_summary=default_summary,
            use_account_attribution_setting=use_account_attribution_setting,
            use_unified_attribution_setting=use_unified_attribution_setting,
            filtering=filtering,
            sort=sort,
            limit=limit,
            after=after,
            before=before,
            offset=offset,
            since=since,
            until=until,
            locale=locale,
        )

        # Build batch requests
        batch_requests = []
        for adset_id in adset_ids:
            relative_url = build_relative_url(adset_id, "insights", params)
            batch_requests.append({"method": "GET", "relative_url": relative_url})

        # Execute batch request
        batch_responses = await make_graph_api_batch_call(batch_requests, access_token)

        # Parse responses
        results = []
        successful = 0
        failed = 0

        for i, batch_response in enumerate(batch_responses):
            adset_id = adset_ids[i]
            code = batch_response.get("code")

            if code == 200:
                results.append({
                    "adset_id": adset_id,
                    "insights": batch_response.get("body"),
                    "error": None,
                })
                successful += 1
            else:
                error_body = batch_response.get("body", {})
                error_message = error_body.get("error", {}).get("message", f"HTTP {code}")
                results.append({
                    "adset_id": adset_id,
                    "insights": None,
                    "error": error_message,
                })
                failed += 1

        return {
            "results": results,
            "summary": {
                "total_requested": len(adset_ids),
                "successful": successful,
                "failed": failed,
            },
        }

    @mcp.tool()
    async def get_multiple_ads_insights_by_ids(
        ad_ids: List[str],
        fields: Optional[List[str]] = None,
        date_preset: str = "last_30d",
        time_range: Optional[Dict[str, str]] = None,
        time_ranges: Optional[List[Dict[str, str]]] = None,
        time_increment: str = "all_days",
        action_attribution_windows: Optional[List[str]] = None,
        action_breakdowns: Optional[List[str]] = None,
        action_report_time: Optional[str] = None,
        breakdowns: Optional[List[str]] = None,
        default_summary: bool = False,
        use_account_attribution_setting: bool = False,
        use_unified_attribution_setting: bool = True,
        filtering: Optional[List[dict]] = None,
        sort: Optional[str] = None,
        limit: Optional[int] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        offset: Optional[int] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        locale: Optional[str] = None,
    ) -> Dict:
        """Retrieves performance insights for multiple Facebook ads in batch.

        Uses Facebook's Batch API to efficiently fetch insights for multiple ads
        in a single request (up to 50 ads per API call). Handles errors per
        ad without failing the entire batch.

        Args:
            ad_ids (List[str]): List of ad IDs to fetch insights for.
            fields (Optional[List[str]]): Specific metrics. Examples: 'ad_name', 'account_id',
                'impressions', 'clicks', 'spend', 'ctr', 'reach', 'actions', 'objective',
                'cost_per_action_type', 'conversions', 'cpc', 'cpm', 'cpp', 'frequency'.
            date_preset (str): Predefined relative time range. Default: 'last_30d'.
            time_range (Optional[Dict[str, str]]): Specific time range {'since':'YYYY-MM-DD','until':'YYYY-MM-DD'}.
            time_ranges (Optional[List[Dict[str, str]]]): Array of time range objects for comparison.
            time_increment (str): Time granularity. Default: 'all_days'.
            action_attribution_windows (Optional[List[str]]): Attribution windows.
            action_breakdowns (Optional[List[str]]): Segments 'actions' results.
            action_report_time (Optional[str]): When actions are counted. Default: 'mixed'.
            breakdowns (Optional[List[str]]): Segments results by dimensions.
            default_summary (bool): Include additional summary row. Default: False.
            use_account_attribution_setting (bool): Use ad account attribution settings. Default: False.
            use_unified_attribution_setting (bool): Use unified attribution settings. Default: True.
            filtering (Optional[List[dict]]): Filter objects.
            sort (Optional[str]): Sort field and direction.
            limit (Optional[int]): Maximum results per page.
            after (Optional[str]): Pagination cursor for next page.
            before (Optional[str]): Pagination cursor for previous page.
            offset (Optional[int]): Number of results to skip.
            since (Optional[str]): Start timestamp.
            until (Optional[str]): End timestamp.
            locale (Optional[str]): Locale for text responses.

        Returns:
            Dict: Dictionary containing:
                - 'results' (List[Dict]): List of results, each with:
                    - 'ad_id' (str): The ad ID
                    - 'insights' (Dict): Insights data if successful
                    - 'error' (str|null): Error message if failed, null if successful
                - 'summary' (Dict): Summary with:
                    - 'total_requested' (int): Number of ads requested
                    - 'successful' (int): Number of successful fetches
                    - 'failed' (int): Number of failed fetches
        """
        access_token = config.META_ACCESS_TOKEN

        # Build params for insights request
        params = {"access_token": access_token}
        params = _build_insights_params(
            params=params,
            fields=fields,
            date_preset=date_preset,
            time_range=time_range,
            time_ranges=time_ranges,
            time_increment=time_increment,
            level="ad",
            action_attribution_windows=action_attribution_windows,
            action_breakdowns=action_breakdowns,
            action_report_time=action_report_time,
            breakdowns=breakdowns,
            default_summary=default_summary,
            use_account_attribution_setting=use_account_attribution_setting,
            use_unified_attribution_setting=use_unified_attribution_setting,
            filtering=filtering,
            sort=sort,
            limit=limit,
            after=after,
            before=before,
            offset=offset,
            since=since,
            until=until,
            locale=locale,
        )

        # Build batch requests
        batch_requests = []
        for ad_id in ad_ids:
            relative_url = build_relative_url(ad_id, "insights", params)
            batch_requests.append({"method": "GET", "relative_url": relative_url})

        # Execute batch request
        batch_responses = await make_graph_api_batch_call(batch_requests, access_token)

        # Parse responses
        results = []
        successful = 0
        failed = 0

        for i, batch_response in enumerate(batch_responses):
            ad_id = ad_ids[i]
            code = batch_response.get("code")

            if code == 200:
                results.append({
                    "ad_id": ad_id,
                    "insights": batch_response.get("body"),
                    "error": None,
                })
                successful += 1
            else:
                error_body = batch_response.get("body", {})
                error_message = error_body.get("error", {}).get("message", f"HTTP {code}")
                results.append({
                    "ad_id": ad_id,
                    "insights": None,
                    "error": error_message,
                })
                failed += 1

        return {
            "results": results,
            "summary": {
                "total_requested": len(ad_ids),
                "successful": successful,
                "failed": failed,
            },
        }

    @mcp.tool()
    async def fetch_pagination_url(url: str) -> str:
        """Fetch data from a Facebook Graph API pagination URL.

        Use this to get the next/previous page of results from an insights API call.

        Args:
            url (str): The complete pagination URL (e.g., from response['paging']['next'] or
                response['paging']['previous']). It includes the necessary token and parameters.

        Returns:
            str: JSON string containing the next/previous page of results.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        return json.dumps(data, indent=2)
