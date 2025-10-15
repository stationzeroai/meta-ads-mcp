import json
from typing import Optional, List, Dict, Any
from datetime import datetime

from mcp.server.fastmcp import FastMCP

from meta_ads_mcp.config import config
from meta_ads_mcp.meta_api_client.client import make_graph_api_call
from meta_ads_mcp.meta_api_client.constants import FB_GRAPH_URL


def _validate_date_preset(date_preset: Optional[str]) -> bool:
    """Validate if the date preset is one of the allowed values."""
    valid_presets = [
        "today",
        "yesterday",
        "this_month",
        "last_month",
        "this_quarter",
        "lifetime",
        "last_3d",
        "last_7d",
        "last_14d",
        "last_28d",
        "last_30d",
        "last_90d",
        "last_week_mon_sun",
        "last_week_sun_sat",
        "last_quarter",
        "last_year",
        "this_week_mon_today",
        "this_week_sun_today",
        "this_year",
    ]
    return date_preset in valid_presets


def _validate_date_format(date_str: str) -> bool:
    """Validate if the date string is in YYYY-MM-DD format."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def register_tools(mcp: FastMCP):
    @mcp.tool()
    async def get_campaign_insights(
        campaign_id: str,
        date_preset: Optional[str] = "last_30d",
        time_range_start: Optional[str] = None,
        time_range_end: Optional[str] = None,
        level: str = "campaign",
        fields: Optional[List[str]] = None,
        breakdowns: Optional[List[str]] = None,
        time_increment: Optional[str] = None,
    ) -> str:
        """Get insights (performance metrics/reports) for a specific campaign.

        This tool retrieves detailed performance metrics for a campaign including impressions, clicks,
        conversions, spend, and other key performance indicators.

        Args:
            campaign_id (str): The Campaign ID to get insights for.
            date_preset (str): A preset date range. Options include: 'today', 'yesterday', 'last_7d',
                'last_14d', 'last_28d', 'last_30d', 'last_90d', 'this_month', 'last_month',
                'this_quarter', 'last_quarter', 'this_year', 'last_year', 'lifetime'.
                Default is 'last_30d'. Use 'lifetime' for all-time data.
            time_range_start (str): Custom start date in YYYY-MM-DD format. If provided,
                time_range_end must also be provided and date_preset will be ignored.
            time_range_end (str): Custom end date in YYYY-MM-DD format. If provided,
                time_range_start must also be provided and date_preset will be ignored.
            level (str): The level of data aggregation. Options: 'campaign', 'adset', 'ad'.
                Default is 'campaign'.
            fields (List[str]): Specific metrics to retrieve. Common fields include:
                'impressions', 'clicks', 'spend', 'reach', 'frequency', 'cpm', 'cpc', 'ctr',
                'conversions', 'cost_per_conversion', 'actions', 'action_values', 'website_ctr',
                'video_view', 'video_p25_watched_actions', 'video_p50_watched_actions',
                'video_p75_watched_actions', 'video_p100_watched_actions'.
                If not specified, default metrics will be returned.
            breakdowns (List[str]): Dimensions to break down the data by. Options include:
                'age', 'gender', 'country', 'region', 'placement', 'device_platform',
                'publisher_platform', 'product_id', 'hourly_stats_aggregated_by_advertiser_time_zone'.
            time_increment (str): Time increment for the data. Options: '1' (daily), '7' (weekly),
                '14', '28', 'monthly', 'all_days' (aggregate all data).
                Default is 'all_days' (returns single aggregate row).

        Returns:
            str: A JSON string containing the campaign insights data.
            If the request fails, it returns a JSON string with an error message and details.
        """
        # Validate date preset if using preset
        if not time_range_start and not time_range_end:
            if not _validate_date_preset(date_preset):
                return json.dumps(
                    {
                        "error": f"Invalid date_preset: {date_preset}. Must be one of: today, yesterday, last_7d, last_14d, last_28d, last_30d, last_90d, this_month, last_month, this_quarter, last_quarter, this_year, last_year, lifetime"
                    },
                    indent=2,
                )

        # Validate custom date range if provided
        if time_range_start or time_range_end:
            if not time_range_start or not time_range_end:
                return json.dumps(
                    {
                        "error": "Both time_range_start and time_range_end must be provided when using custom date range"
                    },
                    indent=2,
                )
            if not _validate_date_format(time_range_start) or not _validate_date_format(
                time_range_end
            ):
                return json.dumps(
                    {"error": "Dates must be in YYYY-MM-DD format"}, indent=2
                )

        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{campaign_id}/insights"

        # Build params
        params: Dict[str, Any] = {
            "access_token": access_token,
            "level": level,
        }

        # Add date range
        if time_range_start and time_range_end:
            params["time_range"] = json.dumps(
                {"since": time_range_start, "until": time_range_end}
            )
        else:
            params["date_preset"] = date_preset

        # Add optional parameters
        if fields:
            params["fields"] = ",".join(fields)

        if breakdowns:
            params["breakdowns"] = ",".join(breakdowns)

        if time_increment:
            params["time_increment"] = time_increment

        try:
            data = await make_graph_api_call(url, params)
            return json.dumps(data, indent=2)
        except Exception as e:
            error_msg = str(e)
            return json.dumps(
                {
                    "error": "Failed to fetch campaign insights",
                    "details": error_msg,
                    "params_sent": params,
                },
                indent=2,
            )

    @mcp.tool()
    async def get_account_insights(
        account_id: str,
        date_preset: Optional[str] = "last_30d",
        time_range_start: Optional[str] = None,
        time_range_end: Optional[str] = None,
        level: str = "account",
        fields: Optional[List[str]] = None,
        breakdowns: Optional[List[str]] = None,
        filtering: Optional[List[Dict[str, Any]]] = None,
        time_increment: Optional[str] = None,
        limit: Optional[int] = 100,
    ) -> str:
        """Get insights (performance metrics/reports) for an ad account across all campaigns.

        This tool retrieves aggregated performance metrics for an entire ad account or broken down
        by campaigns, ad sets, or ads.

        Args:
            account_id (str): The Ad Account ID (format: act_XXXXXXXXXX).
            date_preset (str): A preset date range. Options include: 'today', 'yesterday', 'last_7d',
                'last_14d', 'last_28d', 'last_30d', 'last_90d', 'this_month', 'last_month',
                'this_quarter', 'last_quarter', 'this_year', 'last_year', 'lifetime'.
                Default is 'last_30d'.
            time_range_start (str): Custom start date in YYYY-MM-DD format. If provided,
                time_range_end must also be provided and date_preset will be ignored.
            time_range_end (str): Custom end date in YYYY-MM-DD format.
            level (str): The level of data aggregation. Options: 'account', 'campaign', 'adset', 'ad'.
                Default is 'account'.
            fields (List[str]): Specific metrics to retrieve. Common fields include:
                'impressions', 'clicks', 'spend', 'reach', 'frequency', 'cpm', 'cpc', 'ctr',
                'conversions', 'cost_per_conversion', 'actions', 'action_values', 'campaign_name',
                'adset_name', 'ad_name'.
            breakdowns (List[str]): Dimensions to break down the data by. Options include:
                'age', 'gender', 'country', 'region', 'placement', 'device_platform',
                'publisher_platform'.
            filtering (List[Dict]): Filter the results. Example:
                [{"field": "campaign.name", "operator": "CONTAIN", "value": "Holiday"}]
            time_increment (str): Time increment for the data. Options: '1' (daily), '7' (weekly),
                'monthly', 'all_days'.
            limit (int): Maximum number of results to return. Default is 100.

        Returns:
            str: A JSON string containing the account insights data.
        """
        # Validate date preset if using preset
        if not time_range_start and not time_range_end:
            if not _validate_date_preset(date_preset):
                return json.dumps(
                    {
                        "error": f"Invalid date_preset: {date_preset}. Must be one of: today, yesterday, last_7d, last_14d, last_28d, last_30d, last_90d, this_month, last_month, this_quarter, last_quarter, this_year, last_year, lifetime"
                    },
                    indent=2,
                )

        # Validate custom date range if provided
        if time_range_start or time_range_end:
            if not time_range_start or not time_range_end:
                return json.dumps(
                    {
                        "error": "Both time_range_start and time_range_end must be provided when using custom date range"
                    },
                    indent=2,
                )
            if not _validate_date_format(time_range_start) or not _validate_date_format(
                time_range_end
            ):
                return json.dumps(
                    {"error": "Dates must be in YYYY-MM-DD format"}, indent=2
                )

        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{account_id}/insights"

        # Build params
        params: Dict[str, Any] = {
            "access_token": access_token,
            "level": level,
            "limit": limit,
        }

        # Add date range
        if time_range_start and time_range_end:
            params["time_range"] = json.dumps(
                {"since": time_range_start, "until": time_range_end}
            )
        else:
            params["date_preset"] = date_preset

        # Add optional parameters
        if fields:
            params["fields"] = ",".join(fields)

        if breakdowns:
            params["breakdowns"] = ",".join(breakdowns)

        if filtering:
            params["filtering"] = json.dumps(filtering)

        if time_increment:
            params["time_increment"] = time_increment

        try:
            data = await make_graph_api_call(url, params)
            return json.dumps(data, indent=2)
        except Exception as e:
            error_msg = str(e)
            return json.dumps(
                {
                    "error": "Failed to fetch account insights",
                    "details": error_msg,
                    "params_sent": params,
                },
                indent=2,
            )

    @mcp.tool()
    async def get_adset_insights(
        adset_id: str,
        date_preset: Optional[str] = "last_30d",
        time_range_start: Optional[str] = None,
        time_range_end: Optional[str] = None,
        level: str = "adset",
        fields: Optional[List[str]] = None,
        breakdowns: Optional[List[str]] = None,
        time_increment: Optional[str] = None,
    ) -> str:
        """Get insights (performance metrics/reports) for a specific ad set.

        This tool retrieves detailed performance metrics for an ad set including impressions, clicks,
        conversions, spend, and other key performance indicators.

        Args:
            adset_id (str): The Ad Set ID to get insights for.
            date_preset (str): A preset date range. Options include: 'today', 'yesterday', 'last_7d',
                'last_14d', 'last_28d', 'last_30d', 'last_90d', 'this_month', 'last_month',
                'this_quarter', 'last_quarter', 'this_year', 'last_year', 'lifetime'.
                Default is 'last_30d'.
            time_range_start (str): Custom start date in YYYY-MM-DD format.
            time_range_end (str): Custom end date in YYYY-MM-DD format.
            level (str): The level of data aggregation. Options: 'adset', 'ad'.
                Default is 'adset'.
            fields (List[str]): Specific metrics to retrieve.
            breakdowns (List[str]): Dimensions to break down the data by.
            time_increment (str): Time increment for the data.

        Returns:
            str: A JSON string containing the ad set insights data.
        """
        # Validate date preset if using preset
        if not time_range_start and not time_range_end:
            if not _validate_date_preset(date_preset):
                return json.dumps(
                    {
                        "error": f"Invalid date_preset: {date_preset}. Must be one of: today, yesterday, last_7d, last_14d, last_28d, last_30d, last_90d, this_month, last_month, this_quarter, last_quarter, this_year, last_year, lifetime"
                    },
                    indent=2,
                )

        # Validate custom date range if provided
        if time_range_start or time_range_end:
            if not time_range_start or not time_range_end:
                return json.dumps(
                    {
                        "error": "Both time_range_start and time_range_end must be provided when using custom date range"
                    },
                    indent=2,
                )
            if not _validate_date_format(time_range_start) or not _validate_date_format(
                time_range_end
            ):
                return json.dumps(
                    {"error": "Dates must be in YYYY-MM-DD format"}, indent=2
                )

        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{adset_id}/insights"

        # Build params
        params: Dict[str, Any] = {
            "access_token": access_token,
            "level": level,
        }

        # Add date range
        if time_range_start and time_range_end:
            params["time_range"] = json.dumps(
                {"since": time_range_start, "until": time_range_end}
            )
        else:
            params["date_preset"] = date_preset

        # Add optional parameters
        if fields:
            params["fields"] = ",".join(fields)

        if breakdowns:
            params["breakdowns"] = ",".join(breakdowns)

        if time_increment:
            params["time_increment"] = time_increment

        try:
            data = await make_graph_api_call(url, params)
            return json.dumps(data, indent=2)
        except Exception as e:
            error_msg = str(e)
            return json.dumps(
                {
                    "error": "Failed to fetch ad set insights",
                    "details": error_msg,
                    "params_sent": params,
                },
                indent=2,
            )

    @mcp.tool()
    async def get_ad_insights(
        ad_id: str,
        date_preset: Optional[str] = "last_30d",
        time_range_start: Optional[str] = None,
        time_range_end: Optional[str] = None,
        fields: Optional[List[str]] = None,
        breakdowns: Optional[List[str]] = None,
        time_increment: Optional[str] = None,
    ) -> str:
        """Get insights (performance metrics/reports) for a specific ad.

        This tool retrieves detailed performance metrics for an individual ad including impressions, clicks,
        conversions, spend, and other key performance indicators.

        Args:
            ad_id (str): The Ad ID to get insights for.
            date_preset (str): A preset date range. Default is 'last_30d'.
            time_range_start (str): Custom start date in YYYY-MM-DD format.
            time_range_end (str): Custom end date in YYYY-MM-DD format.
            fields (List[str]): Specific metrics to retrieve. Common fields include:
                'impressions', 'clicks', 'spend', 'reach', 'frequency', 'cpm', 'cpc', 'ctr',
                'conversions', 'cost_per_conversion', 'actions', 'action_values',
                'unique_clicks', 'unique_ctr', 'cost_per_unique_click'.
            breakdowns (List[str]): Dimensions to break down the data by.
            time_increment (str): Time increment for the data.

        Returns:
            str: A JSON string containing the ad insights data.
        """
        # Validate date preset if using preset
        if not time_range_start and not time_range_end:
            if not _validate_date_preset(date_preset):
                return json.dumps(
                    {
                        "error": f"Invalid date_preset: {date_preset}. Must be one of: today, yesterday, last_7d, last_14d, last_28d, last_30d, last_90d, this_month, last_month, this_quarter, last_quarter, this_year, last_year, lifetime"
                    },
                    indent=2,
                )

        # Validate custom date range if provided
        if time_range_start or time_range_end:
            if not time_range_start or not time_range_end:
                return json.dumps(
                    {
                        "error": "Both time_range_start and time_range_end must be provided when using custom date range"
                    },
                    indent=2,
                )
            if not _validate_date_format(time_range_start) or not _validate_date_format(
                time_range_end
            ):
                return json.dumps(
                    {"error": "Dates must be in YYYY-MM-DD format"}, indent=2
                )

        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{ad_id}/insights"

        # Build params
        params: Dict[str, Any] = {
            "access_token": access_token,
            "level": "ad",
        }

        # Add date range
        if time_range_start and time_range_end:
            params["time_range"] = json.dumps(
                {"since": time_range_start, "until": time_range_end}
            )
        else:
            params["date_preset"] = date_preset

        # Add optional parameters
        if fields:
            params["fields"] = ",".join(fields)

        if breakdowns:
            params["breakdowns"] = ",".join(breakdowns)

        if time_increment:
            params["time_increment"] = time_increment

        try:
            data = await make_graph_api_call(url, params)
            return json.dumps(data, indent=2)
        except Exception as e:
            error_msg = str(e)
            return json.dumps(
                {
                    "error": "Failed to fetch ad insights",
                    "details": error_msg,
                    "params_sent": params,
                },
                indent=2,
            )

    @mcp.tool()
    async def compare_campaign_performance(
        campaign_ids: List[str],
        date_preset: Optional[str] = "last_30d",
        time_range_start: Optional[str] = None,
        time_range_end: Optional[str] = None,
        fields: Optional[List[str]] = None,
    ) -> str:
        """Compare performance metrics across multiple campaigns.

        This tool retrieves and compares performance metrics for multiple campaigns side-by-side,
        making it easy to identify top performers and underperformers.

        Args:
            campaign_ids (List[str]): List of Campaign IDs to compare (max 10 recommended).
            date_preset (str): A preset date range. Default is 'last_30d'.
            time_range_start (str): Custom start date in YYYY-MM-DD format.
            time_range_end (str): Custom end date in YYYY-MM-DD format.
            fields (List[str]): Specific metrics to retrieve for comparison. If not specified,
                default metrics (impressions, clicks, spend, ctr, cpc, conversions) will be used.

        Returns:
            str: A JSON string containing comparative performance data for all campaigns.
        """
        if not campaign_ids or len(campaign_ids) == 0:
            return json.dumps(
                {"error": "At least one campaign_id must be provided"}, indent=2
            )

        # Validate date preset if using preset
        if not time_range_start and not time_range_end:
            if not _validate_date_preset(date_preset):
                return json.dumps(
                    {
                        "error": f"Invalid date_preset: {date_preset}. Must be one of: today, yesterday, last_7d, last_14d, last_28d, last_30d, last_90d, this_month, last_month, this_quarter, last_quarter, this_year, last_year, lifetime"
                    },
                    indent=2,
                )

        # Validate custom date range if provided
        if time_range_start or time_range_end:
            if not time_range_start or not time_range_end:
                return json.dumps(
                    {
                        "error": "Both time_range_start and time_range_end must be provided when using custom date range"
                    },
                    indent=2,
                )
            if not _validate_date_format(time_range_start) or not _validate_date_format(
                time_range_end
            ):
                return json.dumps(
                    {"error": "Dates must be in YYYY-MM-DD format"}, indent=2
                )

        # Use default fields if none provided
        if not fields:
            fields = [
                "campaign_name",
                "impressions",
                "clicks",
                "spend",
                "ctr",
                "cpc",
                "cpm",
            ]

        access_token = config.META_ACCESS_TOKEN
        comparison_results = []

        for campaign_id in campaign_ids:
            url = f"{FB_GRAPH_URL}/{campaign_id}/insights"

            params: Dict[str, Any] = {
                "access_token": access_token,
                "level": "campaign",
                "fields": ",".join(fields),
            }

            # Add date range
            if time_range_start and time_range_end:
                params["time_range"] = json.dumps(
                    {"since": time_range_start, "until": time_range_end}
                )
            else:
                params["date_preset"] = date_preset

            try:
                data = await make_graph_api_call(url, params)
                comparison_results.append(
                    {"campaign_id": campaign_id, "insights": data}
                )
            except Exception as e:
                comparison_results.append(
                    {
                        "campaign_id": campaign_id,
                        "error": f"Failed to fetch insights: {str(e)}",
                    }
                )

        return json.dumps(
            {"comparison": comparison_results, "date_range": date_preset}, indent=2
        )
