import json
from typing import Optional, List, Dict

from fastmcp import FastMCP

from meta_ads_mcp.config import config
from meta_ads_mcp.meta_api_client.client import make_graph_api_call
from meta_ads_mcp.meta_api_client.constants import FB_GRAPH_URL


def register_tools(mcp: FastMCP):
    async def fetch_meta_campaigns_by_name(
        act_id: str,
        campaign_names: List[str],
        metrics: List[str],
        date_preset: Optional[str] = None,
        time_range: Optional[Dict[str, str]] = None,
    ) -> Dict:
        """Fetches Meta campaigns by name with insights data and proper date handling.

        This function efficiently retrieves multiple campaigns by their names and includes
        their insights data with proper date range handling. It uses Facebook's native
        filtering with exact name matching only.

        Args:
            act_id (str): The Meta ad account ID with 'act_' prefix (e.g., 'act_1234567890').
            campaign_names (List[str]): List of campaign names to fetch. Uses exact name
                matching only. Empty list returns no results.
            metrics (List[str]): List of Meta insights metrics to retrieve. Common options:
                'impressions', 'clicks', 'spend', 'reach', 'ctr', 'cpc', 'cpm', 'frequency',
                'conversions', 'cost_per_conversion'.
            date_preset (Optional[str]): Predefined relative date range. Valid options:
                'today', 'yesterday', 'this_month', 'last_month', 'last_7d', 'last_30d', etc.
                Cannot be used with time_range.
            time_range (Optional[Dict[str, str]]): Custom date range with 'since' and 'until'
                keys in 'YYYY-MM-DD' format. Takes precedence over date_preset.

        Returns:
            Dict: Dictionary containing matched campaigns with insights data and summary.
        """
        access_token = config.META_ACCESS_TOKEN
        matched_campaigns = []

        # Fetch each campaign with exact match
        for requested_name in campaign_names:
            name_filter = [
                {"field": "name", "operator": "EQUAL", "value": requested_name}
            ]

            campaigns_url = f"{FB_GRAPH_URL}/{act_id}/campaigns"
            campaigns_params = {
                "access_token": access_token,
                "fields": "id,name,effective_status",
                "filtering": json.dumps(name_filter),
                "limit": 500,
            }

            try:
                campaign_response = await make_graph_api_call(
                    campaigns_url, campaigns_params
                )

                if campaign_response.get("data"):
                    for campaign in campaign_response.get("data", []):
                        campaign["requested_name"] = requested_name
                        campaign["matched_name"] = requested_name
                        matched_campaigns.append(campaign)
            except Exception as e:
                print(f"Error fetching campaign '{requested_name}': {str(e)}")

        # Fetch insights for each matched campaign
        campaigns_with_insights = []

        for campaign in matched_campaigns:
            try:
                insights_url = f"{FB_GRAPH_URL}/{campaign['id']}/insights"
                insights_params = {
                    "access_token": access_token,
                    "fields": ",".join(metrics),
                    "level": "campaign",
                }

                if time_range:
                    insights_params["time_range"] = json.dumps(time_range)
                elif date_preset:
                    insights_params["date_preset"] = date_preset

                insights_response = await make_graph_api_call(
                    insights_url, insights_params
                )

                campaign_with_insights = {
                    **campaign,
                    "insights": insights_response.get("data", []),
                }
                campaigns_with_insights.append(campaign_with_insights)

            except Exception as e:
                campaign_with_insights = {
                    **campaign,
                    "insights": [],
                    "insights_error": str(e),
                }
                campaigns_with_insights.append(campaign_with_insights)

        # Create summary
        name_mappings = {}
        matched_requested_names = []

        for campaign in matched_campaigns:
            requested = campaign.get("requested_name", "")
            matched = campaign.get("matched_name", "")
            if requested:
                name_mappings[requested] = matched
                matched_requested_names.append(requested)

        unmatched_requests = [
            name for name in campaign_names if name not in matched_requested_names
        ]

        result = {
            "data": campaigns_with_insights,
            "summary": {
                "requested_names": campaign_names,
                "total_matched_campaigns": len(matched_campaigns),
                "campaigns_with_insights": len(
                    [c for c in campaigns_with_insights if "insights_error" not in c]
                ),
                "unmatched_requests": unmatched_requests,
                "name_mappings": name_mappings,
            },
        }

        return result

    async def fetch_meta_ad_sets_by_name(
        act_id: str,
        adset_names: List[str],
        metrics: List[str],
        date_preset: Optional[str] = None,
        time_range: Optional[Dict[str, str]] = None,
    ) -> Dict:
        """Fetches Meta ad sets by name with insights data and proper date handling.

        This function efficiently retrieves multiple ad sets by their names and includes
        their insights data with proper date range handling. It uses Facebook's native
        filtering with exact name matching only.

        Args:
            act_id (str): The Meta ad account ID with 'act_' prefix (e.g., 'act_1234567890').
            adset_names (List[str]): List of ad set names to fetch. Uses exact name
                matching only. Empty list returns no results.
            metrics (List[str]): List of Meta insights metrics to retrieve. Common options:
                'impressions', 'clicks', 'spend', 'reach', 'ctr', 'cpc', 'cpm', 'frequency',
                'conversions', 'cost_per_conversion'.
            date_preset (Optional[str]): Predefined relative date range. Valid options:
                'today', 'yesterday', 'this_month', 'last_month', 'last_7d', 'last_30d', etc.
                Cannot be used with time_range.
            time_range (Optional[Dict[str, str]]): Custom date range with 'since' and 'until'
                keys in 'YYYY-MM-DD' format. Takes precedence over date_preset.

        Returns:
            Dict: Dictionary containing matched ad sets with insights data and summary.
        """
        access_token = config.META_ACCESS_TOKEN
        matched_adsets = []

        # Fetch each ad set with exact match
        for requested_name in adset_names:
            name_filter = [
                {"field": "name", "operator": "EQUAL", "value": requested_name}
            ]
            
            adsets_url = f"{FB_GRAPH_URL}/{act_id}/adsets"
            adsets_params = {
                "access_token": access_token,
                "fields": "id,name,effective_status",
                "filtering": json.dumps(name_filter),
                "limit": 500,
            }

            try:
                adset_response = await make_graph_api_call(adsets_url, adsets_params)

                if adset_response.get("data"):
                    for adset in adset_response.get("data", []):
                        adset["requested_name"] = requested_name
                        adset["matched_name"] = requested_name
                        matched_adsets.append(adset)
            except Exception as e:
                print(f"Error fetching ad set '{requested_name}': {str(e)}")

        # Fetch insights for each matched ad set
        adsets_with_insights = []

        for adset in matched_adsets:
            try:
                insights_url = f"{FB_GRAPH_URL}/{adset['id']}/insights"
                insights_params = {
                    "access_token": access_token,
                    "fields": ",".join(metrics),
                    "level": "adset",
                }

                if time_range:
                    insights_params["time_range"] = json.dumps(time_range)
                elif date_preset:
                    insights_params["date_preset"] = date_preset

                insights_response = await make_graph_api_call(
                    insights_url, insights_params
                )

                adset_with_insights = {
                    **adset,
                    "insights": insights_response.get("data", []),
                }
                adsets_with_insights.append(adset_with_insights)

            except Exception as e:
                adset_with_insights = {
                    **adset,
                    "insights": [],
                    "insights_error": str(e),
                }
                adsets_with_insights.append(adset_with_insights)

        # Create summary
        name_mappings = {}
        matched_requested_names = []

        for adset in matched_adsets:
            requested = adset.get("requested_name", "")
            matched = adset.get("matched_name", "")
            if requested:
                name_mappings[requested] = matched
                matched_requested_names.append(requested)

        unmatched_requests = [
            name for name in adset_names if name not in matched_requested_names
        ]

        result = {
            "data": adsets_with_insights,
            "summary": {
                "requested_names": adset_names,
                "total_matched_adsets": len(matched_adsets),
                "adsets_with_insights": len(
                    [a for a in adsets_with_insights if "insights_error" not in a]
                ),
                "unmatched_requests": unmatched_requests,
                "name_mappings": name_mappings,
            },
        }

        return result

    @mcp.tool()
    async def fetch_meta_objects_by_name(
        act_id: str,
        object_names: List[str],
        metrics: List[str],
        date_preset: Optional[str] = None,
        time_range: Optional[Dict[str, str]] = None,
    ) -> Dict:
        """Unified tool to fetch Meta campaigns and ad sets by name with automatic fallback.

        This function automatically tries to find objects by name, first searching for campaigns,
        then searching for ad sets for any names not found as campaigns. Each returned object
        includes an 'object_type' field to identify whether it's a campaign or ad set.

        Args:
            act_id (str): The Meta ad account ID with 'act_' prefix.
                Example format 'act_1234567890'
            object_names (List[str]): List of object names to fetch. Uses exact name
                matching only. The function will automatically try each name as a campaign
                first, then as an ad set if not found. Empty list returns no results.
            metrics (List[str]): List of Meta insights metrics to retrieve.
                Common options are 'impressions', 'clicks', 'spend', 'reach', 'ctr',
                'cpc', 'cpm', 'frequency', 'conversions', 'cost_per_conversion'
            date_preset (Optional[str], optional): Predefined relative date range.
                Valid options are 'today', 'yesterday', 'this_month', 'last_month',
                'this_quarter', 'last_quarter', 'this_year', 'last_year', 'last_3d',
                'last_7d', 'last_14d', 'last_28d', 'last_30d', 'last_90d',
                'last_week_mon_sun', 'last_week_sun_sat', 'this_week_mon_today',
                'this_week_sun_today', 'maximum'. Cannot be used with time_range.
                Defaults to None.
            time_range (Optional[Dict[str, str]], optional): Custom date range with
                'since' and 'until' keys in 'YYYY-MM-DD' format. Takes precedence over
                date_preset if both are provided. Must contain both 'since' and 'until'
                keys. Defaults to None.

        Returns:
            Dict: Response dictionary containing the following structure:
                - 'data' (List[Dict]): Combined list of found objects (campaigns and ad sets), each containing:
                    - All standard campaign/ad set fields (id, name, effective_status)
                    - 'object_type' (str): Either "campaign" or "adset"
                    - 'requested_name' (str): Originally requested name
                    - 'matched_name' (str): Actual name that was matched
                    - 'insights' (List[Dict]): Performance insights data
                    - 'insights_error' (str, optional): Error message if insights failed
                - 'summary' (Dict): Summary information containing:
                    - 'requested_names' (List[str]): All originally requested names
                    - 'found_as_campaigns' (List[str]): Names found as campaigns
                    - 'found_as_adsets' (List[str]): Names found as ad sets
                    - 'not_found' (List[str]): Names not found as either campaigns or ad sets
                    - 'total_objects_found' (int): Total number of objects found
                    - 'campaigns_count' (int): Number of campaigns found
                    - 'adsets_count' (int): Number of ad sets found
                    - 'objects_with_insights' (int): Number with successful insights

        Examples:
            Fetch objects with automatic campaign/ad set detection

            ```python
            result = fetch_meta_objects_by_name(
                act_id="act_1234567890",
                object_names=["Summer Sale Campaign", "Holiday Ad Set", "Black Friday"],
                metrics=["impressions", "clicks", "spend"],
                date_preset="yesterday"
            )
            # Returns campaigns and ad sets found, each with object_type field
            ```

            Fetch objects with custom date range

            ```python
            result = fetch_meta_objects_by_name(
                act_id="act_1234567890",
                object_names=["Q4 Campaign", "Retargeting Audience"],
                metrics=["impressions", "spend", "conversions"],
                time_range={"since": "2023-11-24", "until": "2023-11-27"}
            )
            # Automatically tries as campaigns first, then ad sets for unmatched names
            ```

        Note:
            This function implements intelligent fallback:
            1. Tries all names as campaigns first
            2. For unmatched names, tries them as ad sets
            3. Returns combined results with clear object type identification
            Each object in the result includes an 'object_type' field for easy identification.
        """
        # Step 1: Try fetching all names as campaigns first
        campaigns_result = await fetch_meta_campaigns_by_name(
            act_id=act_id,
            campaign_names=object_names,
            metrics=metrics,
            date_preset=date_preset,
            time_range=time_range,
        )

        # Step 2: Identify which names weren't found as campaigns
        unmatched_campaign_names = campaigns_result["summary"]["unmatched_requests"]

        # Step 3: Try fetching unmatched names as ad sets
        adsets_result = None
        if unmatched_campaign_names:
            adsets_result = await fetch_meta_ad_sets_by_name(
                act_id=act_id,
                adset_names=unmatched_campaign_names,
                metrics=metrics,
                date_preset=date_preset,
                time_range=time_range,
            )

        # Step 4: Combine results
        all_objects = []

        # Add campaigns with object_type field
        for campaign in campaigns_result["data"]:
            campaign["object_type"] = "campaign"
            all_objects.append(campaign)

        # Add ad sets with object_type field
        if adsets_result:
            for adset in adsets_result["data"]:
                adset["object_type"] = "adset"
                all_objects.append(adset)

        # Step 5: Calculate summary statistics
        found_as_campaigns = [obj["requested_name"] for obj in campaigns_result["data"]]
        found_as_adsets = []
        if adsets_result:
            found_as_adsets = [obj["requested_name"] for obj in adsets_result["data"]]

        all_found_names = found_as_campaigns + found_as_adsets
        not_found = [name for name in object_names if name not in all_found_names]

        # Step 6: Return combined results
        return {
            "data": all_objects,
            "summary": {
                "requested_names": object_names,
                "found_as_campaigns": found_as_campaigns,
                "found_as_adsets": found_as_adsets,
                "not_found": not_found,
                "total_objects_found": len(all_objects),
                "campaigns_count": len(campaigns_result["data"]),
                "adsets_count": len(adsets_result["data"]) if adsets_result else 0,
                "objects_with_insights": len(
                    [obj for obj in all_objects if "insights_error" not in obj]
                ),
            },
        }
