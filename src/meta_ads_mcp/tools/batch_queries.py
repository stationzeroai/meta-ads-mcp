import json
from typing import Optional, List, Dict

from fastmcp import FastMCP

from meta_ads_mcp.config import config
from meta_ads_mcp.meta_api_client.client import make_graph_api_call
from meta_ads_mcp.meta_api_client.constants import FB_GRAPH_URL


def register_tools(mcp: FastMCP):
    @mcp.tool()
    async def fetch_meta_campaigns_by_name(
        act_id: str,
        campaign_names: List[str],
        metrics: List[str],
        date_preset: Optional[str] = None,
        time_range: Optional[Dict[str, str]] = None,
    ) -> str:
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
            str: JSON string containing matched campaigns with insights data and summary.
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

        return json.dumps(result, indent=2)

    @mcp.tool()
    async def fetch_meta_ad_sets_by_name(
        act_id: str,
        adset_names: List[str],
        metrics: List[str],
        date_preset: Optional[str] = None,
        time_range: Optional[Dict[str, str]] = None,
    ) -> str:
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
            str: JSON string containing matched ad sets with insights data and summary.
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

        return json.dumps(result, indent=2)

    @mcp.tool()
    async def fetch_meta_objects_by_name(
        act_id: str,
        object_names: List[str],
        object_type: str,
        metrics: List[str],
        date_preset: Optional[str] = None,
        time_range: Optional[Dict[str, str]] = None,
    ) -> str:
        """Generic function to fetch Meta objects (campaigns, ad sets, ads) by name with insights.

        Args:
            act_id (str): The Meta ad account ID with 'act_' prefix (e.g., 'act_1234567890').
            object_names (List[str]): List of object names to fetch.
            object_type (str): Type of object to fetch. Options: 'campaign', 'adset', 'ad'.
            metrics (List[str]): List of Meta insights metrics to retrieve.
            date_preset (Optional[str]): Predefined relative date range.
            time_range (Optional[Dict[str, str]]): Custom date range with 'since' and 'until'.

        Returns:
            str: JSON string containing matched objects with insights data and summary.
        """
        access_token = config.META_ACCESS_TOKEN
        
        # Map object type to API endpoint
        endpoint_map = {
            "campaign": "campaigns",
            "adset": "adsets",
            "ad": "ads",
        }
        
        level_map = {
            "campaign": "campaign",
            "adset": "adset",
            "ad": "ad",
        }
        
        if object_type not in endpoint_map:
            return json.dumps(
                {
                    "error": f"Invalid object_type: {object_type}. Must be 'campaign', 'adset', or 'ad'."
                },
                indent=2,
            )
        
        endpoint = endpoint_map[object_type]
        level = level_map[object_type]
        matched_objects = []

        # Fetch each object with exact match
        for requested_name in object_names:
            name_filter = [
                {"field": "name", "operator": "EQUAL", "value": requested_name}
            ]
            
            objects_url = f"{FB_GRAPH_URL}/{act_id}/{endpoint}"
            objects_params = {
                "access_token": access_token,
                "fields": "id,name,effective_status",
                "filtering": json.dumps(name_filter),
                "limit": 500,
            }

            try:
                object_response = await make_graph_api_call(objects_url, objects_params)

                if object_response.get("data"):
                    for obj in object_response.get("data", []):
                        obj["requested_name"] = requested_name
                        obj["matched_name"] = requested_name
                        matched_objects.append(obj)
            except Exception as e:
                print(f"Error fetching {object_type} '{requested_name}': {str(e)}")

        # Fetch insights for each matched object
        objects_with_insights = []

        for obj in matched_objects:
            try:
                insights_url = f"{FB_GRAPH_URL}/{obj['id']}/insights"
                insights_params = {
                    "access_token": access_token,
                    "fields": ",".join(metrics),
                    "level": level,
                }

                if time_range:
                    insights_params["time_range"] = json.dumps(time_range)
                elif date_preset:
                    insights_params["date_preset"] = date_preset

                insights_response = await make_graph_api_call(
                    insights_url, insights_params
                )

                object_with_insights = {
                    **obj,
                    "insights": insights_response.get("data", []),
                }
                objects_with_insights.append(object_with_insights)

            except Exception as e:
                object_with_insights = {
                    **obj,
                    "insights": [],
                    "insights_error": str(e),
                }
                objects_with_insights.append(object_with_insights)

        # Create summary
        name_mappings = {}
        matched_requested_names = []

        for obj in matched_objects:
            requested = obj.get("requested_name", "")
            matched = obj.get("matched_name", "")
            if requested:
                name_mappings[requested] = matched
                matched_requested_names.append(requested)

        unmatched_requests = [
            name for name in object_names if name not in matched_requested_names
        ]

        result = {
            "data": objects_with_insights,
            "summary": {
                "requested_names": object_names,
                "object_type": object_type,
                f"total_matched_{endpoint}": len(matched_objects),
                f"{endpoint}_with_insights": len(
                    [o for o in objects_with_insights if "insights_error" not in o]
                ),
                "unmatched_requests": unmatched_requests,
                "name_mappings": name_mappings,
            },
        }

        return json.dumps(result, indent=2)
