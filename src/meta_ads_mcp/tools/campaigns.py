import json
from typing import Optional, Dict, Any

from mcp.server.fastmcp import FastMCP

from meta_ads_mcp.config import config
from meta_ads_mcp.meta_api_client.client import make_graph_api_post
from meta_ads_mcp.meta_api_client.constants import FB_GRAPH_URL


def _prepare_params(base_params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Adds optional parameters to a dictionary if they are not None."""
    params = base_params.copy()
    for key, value in kwargs.items():
        if value is not None:
            params[key] = value
    return params


def register_tools(mcp: FastMCP):
    @mcp.tool()
    async def create_cbo_campaign(
        act_id: str,
        name: str = None,
        objective: str = None,
        status: str = "PAUSED",
        daily_budget: Optional[float] = None,
        lifetime_budget: Optional[float] = None,
        buying_type: Optional[str] = None,
        bid_strategy: Optional[str] = None,
        bid_amount: Optional[float] = None,
        spend_cap: Optional[float] = None,
    ) -> str:
        """Create a new CBO (Campaign Budget Optimization) campaign in a Meta Ads account.

        This function creates a new CBO campaign where budget and bidding strategy are managed at the campaign level.
        CBO campaigns automatically distribute budget across ad sets to get the best results.

        Args:
            name (str): Campaign name
            objective (str): Campaign objective. Validates ad objectives. enum{OUTCOME_APP_PROMOTION, OUTCOME_AWARENESS, OUTCOME_ENGAGEMENT, OUTCOME_LEADS, OUTCOME_SALES, OUTCOME_TRAFFIC}. Default is OUTCOME_SALES.
            status (str): Initial campaign status (default: PAUSED)
            special_ad_categories (List[str]): List of special ad categories if applicable. This is optional.
            daily_budget (float): Daily budget in account currency (in cents) as a string. Either daily_budget or lifetime_budget is required for CBO campaigns.
            lifetime_budget (float): Lifetime budget in account currency (in cents) as a string. Either daily_budget or lifetime_budget is required for CBO campaigns.
            buying_type (str): Buying type (e.g., 'AUCTION')
            bid_strategy (str): Bid strategy. Options are 'LOWEST_COST_WITHOUT_CAP' (default), 'LOWEST_COST_WITH_BID_CAP', 'COST_CAP'.
            bid_amount (float): Bid amount in account currency (in cents) as a string. Required if bid_strategy is 'LOWEST_COST_WITH_BID_CAP' or 'COST_CAP'.
            spend_cap (float): Spending limit for the campaign in account currency (in cents) as a string. This is optional.
            ab_test_control_setups (Optional[List[Dict[str, Any]]]): Settings for A/B testing (e.g., [{"name":"Creative A", "ad_format":"SINGLE_IMAGE"}])

        Returns:
            str: A JSON string containing the created campaign details.
            If the campaign creation fails, it returns a JSON string with an error message and details.
        """

        if not name:
            return json.dumps({"error": "No campaign name provided"}, indent=2)

        if not objective:
            return json.dumps({"error": "No campaign objective provided"}, indent=2)

        # For CBO campaigns, either daily_budget or lifetime_budget is required
        if not daily_budget and not lifetime_budget:
            return json.dumps(
                {
                    "error": "CBO campaigns require either daily_budget or lifetime_budget"
                },
                indent=2,
            )

        # Default bid strategy for CBO campaigns
        if not bid_strategy:
            bid_strategy = "LOWEST_COST_WITHOUT_CAP"

        # Validate bid_amount requirement
        if bid_strategy in ["LOWEST_COST_WITH_BID_CAP", "COST_CAP"] and not bid_amount:
            return json.dumps(
                {
                    "error": f"bid_amount is required when bid_strategy is {bid_strategy}"
                },
                indent=2,
            )

        access_token = config.META_ACCESS_TOKEN
        account_id = act_id
        url = f"{FB_GRAPH_URL}/{account_id}/campaigns"
        print(f"Account ID: {account_id}")
        print(f"Creating CBO campaign with URL: {url}")

        base_params = {
            "access_token": access_token,
            "name": name,
            "objective": objective,
            "status": status,
            "campaign_budget_optimization": True,  # Always true for CBO campaigns
        }

        params = _prepare_params(
            base_params,
            daily_budget=daily_budget,
            lifetime_budget=lifetime_budget,
            buying_type=buying_type,
            bid_strategy=bid_strategy,
            bid_amount=bid_amount,
            spend_cap=spend_cap,
            special_ad_categories=[],  # required by the API, hardcode default for now
            ab_test_control_setups=[],  # required by the API, hardcode default for now
        )

        try:
            data = await make_graph_api_post(url, params)
            return json.dumps(data, indent=2)
        except Exception as e:
            error_msg = str(e)
            return json.dumps(
                {
                    "error": "Failed to create CBO campaign",
                    "details": error_msg,
                    "params_sent": params,
                },
                indent=2,
            )

    @mcp.tool()
    async def create_abo_campaign(
        act_id: str,
        name: str = None,
        objective: str = "OUTCOME_SALES",
        status: str = "PAUSED",
        buying_type: Optional[str] = "AUCTION",
    ) -> str:
        """Create a new ABO (Ad Set Budget Optimization) campaign in a Meta Ads account.

        This function creates a new ABO campaign where budget and bidding strategy are managed at the ad set level.
        ABO campaigns allow you to control budget allocation for each ad set individually.

        Note: Budget and bid strategy parameters are NOT allowed for ABO campaigns at the campaign level.
        These must be set when creating ad sets for this campaign.

        Args:
            name (str): Campaign name
            objective (str): Campaign objective. Validates ad objectives. enum{OUTCOME_APP_PROMOTION, OUTCOME_AWARENESS, OUTCOME_ENGAGEMENT, OUTCOME_LEADS, OUTCOME_SALES, OUTCOME_TRAFFIC}. Default is OUTCOME_SALES.
            status (str): Initial campaign status (default: PAUSED)
            special_ad_categories (List[str]): List of special ad categories if applicable. This is optional.
            buying_type (str): Buying type (e.g., 'AUCTION')
            ab_test_control_setups (Optional[List[Dict[str, Any]]]): Settings for A/B testing (e.g., [{"name":"Creative A", "ad_format":"SINGLE_IMAGE"}])

        Returns:
            str: A JSON string containing the created campaign details.
            If the campaign creation fails, it returns a JSON string with an error message and details.
        """

        if not name:
            return json.dumps({"error": "No campaign name provided"}, indent=2)

        if not objective:
            return json.dumps({"error": "No campaign objective provided"}, indent=2)

        access_token = config.META_ACCESS_TOKEN
        account_id = act_id
        url = f"{FB_GRAPH_URL}/{account_id}/campaigns"
        print(f"Account ID: {account_id}")
        print(f"Creating ABO campaign with URL: {url}")

        base_params = {
            "access_token": access_token,
            "name": name,
            "objective": objective,
            "status": status,
            "campaign_budget_optimization": False,  # Always false for ABO campaigns
        }

        # For ABO campaigns, we only include non-budget related parameters
        params = _prepare_params(
            base_params,
            special_ad_categories=[],
            buying_type=buying_type,
            ab_test_control_setups=[],
        )

        try:
            data = await make_graph_api_post(url, params)
            return json.dumps(data, indent=2)
        except Exception as e:
            error_msg = str(e)
            return json.dumps(
                {
                    "error": "Failed to create ABO campaign",
                    "details": error_msg,
                    "params_sent": params,
                },
                indent=2,
            )

    @mcp.tool()
    async def deactivate_or_activate_campaign(
        campaign_id: str,
        status: str,
    ) -> str:
        """Turn off (pause or archive) a campaign.

        Sends a ``POST /<CAMPAIGN_ID>`` request with a new status.

        Args:
            campaign_id: The Campaign ID to be deactivated.
            status: The status to be set for the campaign.

        Returns:
            str: Pretty‑printed JSON with update result or error payload.
        """

        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{campaign_id}"
        params = {"access_token": access_token, "status": status}
        return json.dumps(
            await make_graph_api_post(url, params), indent=2, ensure_ascii=False
        )

    @mcp.tool()
    async def update_campaign_budget(
        campaign_id: str,
        daily_budget: Optional[float] = None,
        lifetime_budget: Optional[float] = None,
    ) -> str:
        """Update the budget of a campaign.

        Args:
            campaign_id: The Campaign ID to be updated.
            daily_budget: The daily budget in account currency (in cents) as a string. Optional: should be passed if lifetime_budget is not passed.
            lifetime_budget: The lifetime budget in account currency (in cents) as a string. Optional: should be passed if daily_budget is not passed.

        Returns:
            str: Pretty‑printed JSON with update result or error payload.
        """
        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{campaign_id}"
        params = {
            "access_token": access_token,
            "daily_budget": daily_budget,
            "lifetime_budget": lifetime_budget,
        }
        return json.dumps(
            await make_graph_api_post(url, params), indent=2, ensure_ascii=False
        )
