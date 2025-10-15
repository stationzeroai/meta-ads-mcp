import json
import httpx
from typing import Optional, List, Dict, Any

from mcp.server.fastmcp import FastMCP

from meta_ads_mcp.config import config
from meta_ads_mcp.meta_api_client.client import make_graph_api_call, make_graph_api_post
from meta_ads_mcp.meta_api_client.constants import FB_GRAPH_URL


def _prepare_params(base_params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    params = base_params.copy()
    for key, value in kwargs.items():
        if value is not None:
            params[key] = value
    return params


def register_tools(mcp: FastMCP):
    @mcp.tool()
    async def create_custom_audience(
        account_id: str,
        name: str,
        subtype: str,
        description: Optional[str] = None,
        customer_file_source: Optional[str] = None,
    ) -> str:
        """Create a new custom audience in a Meta Ads account.

        Args:
            account_id (str): The Ad Account ID (format: act_XXXXXXXXXX).
            name (str): Name for the custom audience.
            subtype (str): Type of custom audience. Options: 'CUSTOM', 'WEBSITE', 'APP', 
                'OFFLINE_CONVERSION', 'CLAIM', 'PARTNER', 'MANAGED', 'VIDEO', 'LOOKALIKE', 
                'ENGAGEMENT', 'DATA_SET', 'BAG_OF_ACCOUNTS', 'STUDY_RULE_AUDIENCE', 'FOX'.
            description (str): Optional description for the audience.
            customer_file_source (str): Source of customer file. Options: 'USER_PROVIDED_ONLY',
                'PARTNER_PROVIDED_ONLY', 'BOTH_USER_AND_PARTNER_PROVIDED'.

        Returns:
            str: JSON string containing the created custom audience details including audience ID.
        """
        if not name:
            return json.dumps({"error": "No audience name provided"}, indent=2)

        if not subtype:
            return json.dumps({"error": "No audience subtype provided"}, indent=2)

        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{account_id}/customaudiences"

        base_params = {
            "access_token": access_token,
            "name": name,
            "subtype": subtype,
        }

        params = _prepare_params(
            base_params,
            description=description,
            customer_file_source=customer_file_source,
        )

        try:
            data = await make_graph_api_post(url, params)
            return json.dumps(data, indent=2)
        except Exception as e:
            return json.dumps(
                {
                    "error": "Failed to create custom audience",
                    "details": str(e),
                    "params_sent": params,
                },
                indent=2,
            )

    @mcp.tool()
    async def create_lookalike_audience(
        account_id: str,
        name: str,
        origin_audience_id: str,
        lookalike_spec: Dict[str, Any],
        description: Optional[str] = None,
    ) -> str:
        """Create a lookalike audience based on an existing custom audience.

        Args:
            account_id (str): The Ad Account ID (format: act_XXXXXXXXXX).
            name (str): Name for the lookalike audience.
            origin_audience_id (str): ID of the source custom audience.
            lookalike_spec (Dict): Specification for lookalike audience. Must include:
                - country (str): Two-letter country code (e.g., 'US')
                - ratio (float): Size of audience as ratio (0.01 to 0.20, e.g., 0.01 = 1%)
                - starting_ratio (float): Optional starting ratio for tiered lookalikes
                Example: {"country": "US", "ratio": 0.01}
            description (str): Optional description for the audience.

        Returns:
            str: JSON string containing the created lookalike audience details.
        """
        if not name:
            return json.dumps({"error": "No audience name provided"}, indent=2)

        if not origin_audience_id:
            return json.dumps({"error": "No origin audience ID provided"}, indent=2)

        if not lookalike_spec or "country" not in lookalike_spec or "ratio" not in lookalike_spec:
            return json.dumps(
                {"error": "lookalike_spec must include 'country' and 'ratio'"}, indent=2
            )

        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{account_id}/customaudiences"

        base_params = {
            "access_token": access_token,
            "name": name,
            "subtype": "LOOKALIKE",
            "origin_audience_id": origin_audience_id,
            "lookalike_spec": json.dumps(lookalike_spec),
        }

        params = _prepare_params(base_params, description=description)

        try:
            data = await make_graph_api_post(url, params)
            return json.dumps(data, indent=2)
        except Exception as e:
            return json.dumps(
                {
                    "error": "Failed to create lookalike audience",
                    "details": str(e),
                    "params_sent": params,
                },
                indent=2,
            )

    @mcp.tool()
    async def add_users_to_custom_audience(
        audience_id: str,
        schema: List[str],
        data: List[List[str]],
    ) -> str:
        """Add users to a custom audience using hashed customer data.

        Args:
            audience_id (str): The Custom Audience ID.
            schema (List[str]): List of data types being provided. Options include:
                'EMAIL', 'PHONE', 'FN' (first name), 'LN' (last name), 'FI' (first initial),
                'CT' (city), 'ST' (state), 'ZIP', 'COUNTRY', 'DOBM' (birth month),
                'DOBY' (birth year), 'GEN' (gender), 'MADID' (mobile advertiser ID).
                Example: ['EMAIL', 'PHONE', 'FN', 'LN']
            data (List[List[str]]): User data in same order as schema. Data should be 
                pre-hashed with SHA256. Example: [['hash1@...', 'hash2...', 'hash3...', 'hash4...'], [...]]

        Returns:
            str: JSON string with response including number of users added successfully.
        """
        if not schema:
            return json.dumps({"error": "No schema provided"}, indent=2)

        if not data:
            return json.dumps({"error": "No user data provided"}, indent=2)

        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{audience_id}/users"

        payload = {
            "access_token": access_token,
            "payload": json.dumps({"schema": schema, "data": data}),
        }

        try:
            result = await make_graph_api_post(url, payload)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps(
                {
                    "error": "Failed to add users to custom audience",
                    "details": str(e),
                },
                indent=2,
            )

    @mcp.tool()
    async def remove_users_from_custom_audience(
        audience_id: str,
        schema: List[str],
        data: List[List[str]],
    ) -> str:
        """Remove users from a custom audience.

        Args:
            audience_id (str): The Custom Audience ID.
            schema (List[str]): List of data types. Same options as add_users_to_custom_audience.
            data (List[List[str]]): User data to remove, in same order as schema. 
                Data should be pre-hashed with SHA256.

        Returns:
            str: JSON string with response including number of users removed.
        """
        if not schema:
            return json.dumps({"error": "No schema provided"}, indent=2)

        if not data:
            return json.dumps({"error": "No user data provided"}, indent=2)

        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{audience_id}/users"

        payload = {
            "access_token": access_token,
            "payload": json.dumps({"schema": schema, "data": data, "is_remove": True}),
        }

        try:
            result = await make_graph_api_post(url, payload)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps(
                {
                    "error": "Failed to remove users from custom audience",
                    "details": str(e),
                },
                indent=2,
            )

    @mcp.tool()
    async def get_custom_audience(
        audience_id: str,
        fields: Optional[List[str]] = None,
    ) -> str:
        """Get details about a specific custom audience.

        Args:
            audience_id (str): The Custom Audience ID.
            fields (List[str]): Specific fields to retrieve. Common fields include:
                'name', 'description', 'subtype', 'approximate_count', 'data_source',
                'delivery_status', 'operation_status', 'permission_for_actions',
                'time_created', 'time_updated', 'lookalike_audience_ids'.
                If not specified, default fields will be returned.

        Returns:
            str: JSON string containing the custom audience details.
        """
        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{audience_id}"

        params: Dict[str, Any] = {"access_token": access_token}

        if fields:
            params["fields"] = ",".join(fields)

        try:
            data = await make_graph_api_call(url, params)
            return json.dumps(data, indent=2)
        except Exception as e:
            return json.dumps(
                {
                    "error": "Failed to fetch custom audience",
                    "details": str(e),
                },
                indent=2,
            )

    @mcp.tool()
    async def list_custom_audiences(
        account_id: str,
        fields: Optional[List[str]] = None,
        filtering: Optional[List[Dict[str, Any]]] = None,
        limit: int = 100,
    ) -> str:
        """List all custom audiences in an ad account.

        Args:
            account_id (str): The Ad Account ID (format: act_XXXXXXXXXX).
            fields (List[str]): Specific fields to retrieve for each audience.
                Common fields: 'name', 'description', 'subtype', 'approximate_count',
                'delivery_status', 'time_created'.
            filtering (List[Dict]): Filter the results. Example:
                [{"field": "subtype", "operator": "EQUAL", "value": "LOOKALIKE"}]
            limit (int): Maximum number of audiences to return. Default is 100.

        Returns:
            str: JSON string containing list of custom audiences.
        """
        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{account_id}/customaudiences"

        params: Dict[str, Any] = {
            "access_token": access_token,
            "limit": limit,
        }

        if fields:
            params["fields"] = ",".join(fields)

        if filtering:
            params["filtering"] = json.dumps(filtering)

        try:
            data = await make_graph_api_call(url, params)
            return json.dumps(data, indent=2)
        except Exception as e:
            return json.dumps(
                {
                    "error": "Failed to list custom audiences",
                    "details": str(e),
                },
                indent=2,
            )

    @mcp.tool()
    async def update_custom_audience(
        audience_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> str:
        """Update a custom audience's properties.

        Args:
            audience_id (str): The Custom Audience ID.
            name (str): New name for the audience.
            description (str): New description for the audience.

        Returns:
            str: JSON string with update confirmation.
        """
        if not name and not description:
            return json.dumps(
                {"error": "At least one field (name or description) must be provided"},
                indent=2,
            )

        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{audience_id}"

        params: Dict[str, Any] = {"access_token": access_token}

        if name:
            params["name"] = name
        if description:
            params["description"] = description

        try:
            data = await make_graph_api_post(url, params)
            return json.dumps(data, indent=2)
        except Exception as e:
            return json.dumps(
                {
                    "error": "Failed to update custom audience",
                    "details": str(e),
                },
                indent=2,
            )

    @mcp.tool()
    async def delete_custom_audience(audience_id: str) -> str:
        """Delete a custom audience.

        Args:
            audience_id (str): The Custom Audience ID to delete.

        Returns:
            str: JSON string with deletion confirmation.
        """
        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{audience_id}"

        params = {"access_token": access_token}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(url, params=params)
                response.raise_for_status()
                data = response.json()
            return json.dumps(data, indent=2)
        except Exception as e:
            return json.dumps(
                {
                    "error": "Failed to delete custom audience",
                    "details": str(e),
                },
                indent=2,
            )

    @mcp.tool()
    async def create_saved_audience(
        account_id: str,
        name: str,
        targeting: Dict[str, Any],
        description: Optional[str] = None,
    ) -> str:
        """Create a saved audience with specific targeting criteria.

        Args:
            account_id (str): The Ad Account ID (format: act_XXXXXXXXXX).
            name (str): Name for the saved audience.
            targeting (Dict): Targeting specification. Can include:
                - geo_locations: {"countries": ["US"], "cities": [...], "regions": [...]}
                - age_min: Minimum age (13-65)
                - age_max: Maximum age (13-65)
                - genders: [1] for male, [2] for female, [1,2] for all
                - interests: [{"id": "...", "name": "..."}]
                - behaviors: [{"id": "...", "name": "..."}]
                - life_events: [{"id": "...", "name": "..."}]
                - device_platforms: ["mobile", "desktop"]
                - publisher_platforms: ["facebook", "instagram", "audience_network"]
                Example: {"geo_locations": {"countries": ["US"]}, "age_min": 18, "age_max": 65}
            description (str): Optional description.

        Returns:
            str: JSON string containing the created saved audience details.
        """
        if not name:
            return json.dumps({"error": "No audience name provided"}, indent=2)

        if not targeting:
            return json.dumps({"error": "No targeting specification provided"}, indent=2)

        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{account_id}/saved_audiences"

        base_params = {
            "access_token": access_token,
            "name": name,
            "targeting": json.dumps(targeting),
        }

        params = _prepare_params(base_params, description=description)

        try:
            data = await make_graph_api_post(url, params)
            return json.dumps(data, indent=2)
        except Exception as e:
            return json.dumps(
                {
                    "error": "Failed to create saved audience",
                    "details": str(e),
                    "params_sent": params,
                },
                indent=2,
            )

    @mcp.tool()
    async def get_saved_audience(
        audience_id: str,
        fields: Optional[List[str]] = None,
    ) -> str:
        """Get details about a specific saved audience.

        Args:
            audience_id (str): The Saved Audience ID.
            fields (List[str]): Specific fields to retrieve. Common fields include:
                'name', 'description', 'targeting', 'time_created', 'time_updated',
                'account'.

        Returns:
            str: JSON string containing the saved audience details.
        """
        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{audience_id}"

        params: Dict[str, Any] = {"access_token": access_token}

        if fields:
            params["fields"] = ",".join(fields)

        try:
            data = await make_graph_api_call(url, params)
            return json.dumps(data, indent=2)
        except Exception as e:
            return json.dumps(
                {
                    "error": "Failed to fetch saved audience",
                    "details": str(e),
                },
                indent=2,
            )

    @mcp.tool()
    async def list_saved_audiences(
        account_id: str,
        fields: Optional[List[str]] = None,
        limit: int = 100,
    ) -> str:
        """List all saved audiences in an ad account.

        Args:
            account_id (str): The Ad Account ID (format: act_XXXXXXXXXX).
            fields (List[str]): Specific fields to retrieve for each audience.
            limit (int): Maximum number of audiences to return. Default is 100.

        Returns:
            str: JSON string containing list of saved audiences.
        """
        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{account_id}/saved_audiences"

        params: Dict[str, Any] = {
            "access_token": access_token,
            "limit": limit,
        }

        if fields:
            params["fields"] = ",".join(fields)

        try:
            data = await make_graph_api_call(url, params)
            return json.dumps(data, indent=2)
        except Exception as e:
            return json.dumps(
                {
                    "error": "Failed to list saved audiences",
                    "details": str(e),
                },
                indent=2,
            )

    @mcp.tool()
    async def delete_saved_audience(audience_id: str) -> str:
        """Delete a saved audience.

        Args:
            audience_id (str): The Saved Audience ID to delete.

        Returns:
            str: JSON string with deletion confirmation.
        """
        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{audience_id}"

        params = {"access_token": access_token}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(url, params=params)
                response.raise_for_status()
                data = response.json()
            return json.dumps(data, indent=2)
        except Exception as e:
            return json.dumps(
                {
                    "error": "Failed to delete saved audience",
                    "details": str(e),
                },
                indent=2,
            )

    @mcp.tool()
    async def share_custom_audience(
        audience_id: str,
        account_ids: List[str],
    ) -> str:
        """Share a custom audience with other ad accounts.

        Args:
            audience_id (str): The Custom Audience ID to share.
            account_ids (List[str]): List of ad account IDs to share with.

        Returns:
            str: JSON string with sharing confirmation.
        """
        if not account_ids:
            return json.dumps({"error": "No account IDs provided"}, indent=2)

        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{audience_id}/adaccounts"

        params = {
            "access_token": access_token,
            "adaccounts": json.dumps(account_ids),
        }

        try:
            data = await make_graph_api_post(url, params)
            return json.dumps(data, indent=2)
        except Exception as e:
            return json.dumps(
                {
                    "error": "Failed to share custom audience",
                    "details": str(e),
                },
                indent=2,
            )
