import json
from typing import Dict, Any, List, Union, Optional

from fastmcp import FastMCP

from meta_ads_mcp.config import config
from meta_ads_mcp.meta_api_client.client import make_graph_api_post, make_graph_api_call
from meta_ads_mcp.meta_api_client.constants import FB_GRAPH_URL


def _prepare_params(base_params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Adds optional parameters to a dictionary if they are not None."""
    params = base_params.copy()
    for key, value in kwargs.items():
        if value is not None:
            params[key] = value
    return params


def _requires_conversion_details(optimization_goal: Optional[str]) -> bool:
    """Check if optimization goal requires conversion details like pixel_id and custom_event_type."""
    conversion_goals = {
        "OFFSITE_CONVERSIONS",
        "VALUE",
        "APP_INSTALLS",
        "APP_INSTALLS_AND_OFFSITE_CONVERSIONS",
        "IN_APP_VALUE",
        "LEAD_GENERATION",
        "QUALITY_LEAD",
    }
    return optimization_goal in conversion_goals if optimization_goal else False


def register_tools(mcp: FastMCP):
    @mcp.tool()
    async def create_adset(
        act_id: str,
        campaign_id: str,
        name: str,
        pixel_id: Optional[str] = None,
        website_domain: Optional[str] = None,
        custom_event_type: Optional[str] = None,
        status: str = "PAUSED",
        daily_budget: Optional[str] = None,
        lifetime_budget: Optional[str] = None,
        targeting: Union[str, Dict[str, Any]] | None = None,
        optimization_goal: Optional[str] = None,
        billing_event: Optional[str] = None,
        bid_amount: Optional[str] = None,
        bid_strategy: Optional[str] = None,
        roas_average_floor: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        destination_type: Optional[str] = "WEBSITE",
    ) -> str:
        """
        Create a new ad set in a Meta Ads account.

        If the campaign is CBO(campaign_budget_optimization=true), DO NOT provide the following parameters:
        - `daily_budget`
        - `lifetime_budget`
        - `bid_strategy`
        - `bid_amount`
        - `roas_average_floor`
        If the campaign is ABO(campaign_budget_optimization=false), it is required to provide exactly one of the following parameters:
        - `daily_budget` OR `lifetime_budget`
        - `bid_strategy` (required)
        - `bid_amount` (required for LOWEST_COST_WITH_BID_CAP or COST_CAP strategies)
        - `roas_average_floor` (required for LOWEST_COST_WITH_MIN_ROAS strategy)
        - `start_time` (required for lifetime budgets)
        - `end_time` (required for lifetime budgets)
        Always provide the following parameters:
        - `optimization_goal`
        - `billing_event`
        - `targeting`
        - `status`
        - `name`
        - `campaign_id`
        If the optimization_goal is a conversion goal(OFFSITE_CONVERSIONS, VALUE, APP_INSTALLS, etc.), you must provide the following parameters:
        - `custom_event_type`
        - `destination_type`
        - `pixel_id`


        ──────────────────────────────────────────────────────────────────────────
        1. Objective → optimisation_goal mapping
        ──────────────────────────────────────────────────────────────────────────
        Choose the `optimization_goal` from the set that matches the campaign's
        `objective` (ODAX, Graph-API v23 +).

        * **OUTCOME_AWARENESS**  →  `IMPRESSIONS`, `REACH`, `AD_RECALL_LIFT`, `THRUPLAY`
        * **OUTCOME_TRAFFIC**    →  `LINK_CLICKS`, `LANDING_PAGE_VIEWS`,
        `IMPRESSIONS`, `VISIT_INSTAGRAM_PROFILE`, `CONVERSATIONS`
        * **OUTCOME_ENGAGEMENT** →  `POST_ENGAGEMENT`, `PAGE_LIKES`,
        `EVENT_RESPONSES`, `PROFILE_VISIT`,
        `PROFILE_AND_PAGE_ENGAGEMENT`, `CONVERSATIONS`, `THRUPLAY`
        * **OUTCOME_LEADS**      →  `LEAD_GENERATION`, `QUALITY_LEAD`,
        `CONVERSATIONS`, `SUBSCRIBERS`,
        `MESSAGING_APPOINTMENT_CONVERSION`, `MESSAGING_PURCHASE_CONVERSION`
        * **OUTCOME_APP_PROMOTION** → `APP_INSTALLS`,
        `APP_INSTALLS_AND_OFFSITE_CONVERSIONS`, `IN_APP_VALUE`, `VALUE`
        * **OUTCOME_SALES**      →  `OFFSITE_CONVERSIONS`, `VALUE`,
        `ADVERTISER_SILOED_VALUE`, `MESSAGING_PURCHASE_CONVERSION`,
        `IN_APP_VALUE`

        ──────────────────────────────────────────────────────────────────────────
        2. optimisation_goal → billing_event mapping
        ──────────────────────────────────────────────────────────────────────────
        `billing_event` controls **what you pay for**. Only the combinations
        below pass API validation for _auction_ buying-type ad-sets
        (Graph-API v23 +).  A second value in **italics** means Meta may _accept_
        it but usually coerces it back to the first.

        | optimisation_goal                                 | Allowed `billing_event` values |
        |---------------------------------------------------|--------------------------------|
        | `IMPRESSIONS`, `REACH`, `AD_RECALL_LIFT`, `THRUPLAY` | `IMPRESSIONS` |
        | `LINK_CLICKS`, `LANDING_PAGE_VIEWS`               | `LINK_CLICKS`, *`IMPRESSIONS`* :contentReference[oaicite:0]{index=0} |
        | `VISIT_INSTAGRAM_PROFILE`, `PROFILE_VISIT`        | `IMPRESSIONS` |
        | `POST_ENGAGEMENT`, `PAGE_LIKES`, `EVENT_RESPONSES`| `POST_ENGAGEMENT` / `PAGE_LIKES` / `EVENT_RESPONSES` (match goal), *`IMPRESSIONS`* |
        | `CONVERSATIONS`, `SUBSCRIBERS`, `MESSAGING_*`     | `IMPRESSIONS` |
        | `LEAD_GENERATION`, `QUALITY_LEAD`                 | `IMPRESSIONS` |
        | `APP_INSTALLS`                                    | `APP_INSTALLS`, *`IMPRESSIONS`* |
        | `IN_APP_VALUE`, `APP_INSTALLS_AND_OFFSITE_CONVERSIONS` | `IMPRESSIONS` |
        | `OFFSITE_CONVERSIONS`, `VALUE`, `ADVERTISER_SILOED_VALUE` | `IMPRESSIONS` |
        | *(any goal not listed)*                           | `IMPRESSIONS` (fallback) :contentReference[oaicite:1]{index=1} |

        > **Tip →** If you supply a mismatched pair, the API throws
        > **(#1815003) Optimization/billing event not valid**, or silently
        > coerces `billing_event` to `IMPRESSIONS` for automatic bidding.
        > Always `GET /<ADSET_ID>` after creation to confirm the final value.

        ──────────────────────────────────────────────────────────────────────────
        3. bid strategy quick-reference
        ──────────────────────────────────────────────────────────────────────────
        Required when budget is set at adset level.
        * **`LOWEST_COST_WITHOUT_CAP`** (default) – fully automatic bidding. Ignore `bid_amount`.
        * **`LOWEST_COST_WITH_BID_CAP`** – auto-bid _capped_ at `bid_amount`. Provide `bid_amount` (minor units).
        * **`COST_CAP`** – aims to average results at `bid_amount` while spending. Provide `bid_amount` (minor units).
        * **`LOWEST_COST_WITH_MIN_ROAS`** – The delivery system freely bids to win as many high-value conversions as possible as long as the expected ROAS stays above the floor you set. If the auction can’t clear that ROAS, the ad set will slow or pause. Provide `roas_average_floor` (minor units).
        ──────────────────────────────────────────────────────────────────────────
        3. Targeting quick-reference
        Important: With targeting that use Advantage+ audience, the maximum age needs to be set to 65.
        ──────────────────────────────────────────────────────────────────────────
        ──────────────────────────────────────────────────────────────────────────
        Args
        ──────────────────────────────────────────────────────────────────────────
        state (State)
            Application state with a valid Graph-API `access_token`.
        campaign_id (str)
            ID of the parent campaign.
        name (str)
            Human-readable ad-set name.
        status (str, optional)
            Initial delivery status — default `"PAUSED"`.
        daily_budget, lifetime_budget (str, DO NOT SET IF THE PARENT CAMPAIGN HAS A BUDGET DEFINED)
            **Exactly one.** Minor units (``"5000"`` → R$ 50.00). *Important*: DO NOT SET IF THE PARENT CAMPAIGN HAS A BUDGET DEFINED.
        targeting (dict)
            *Important*: With targeting that use Advantage+ audience, the maximum age needs to be set to 65.
            Targeting specifications including age, location, interests, etc.
            Set ``targeting_automation.advantage_audience = 1`` to let Meta
            expand the audience automatically. If so, set the `age_max` to 65.

            **Examples**

            Broad country targeting
            -----------------------

            ```python
            targeting = {
                "geo_locations": {
                    "countries": ["BR"],
                },
                "age_min": 18,
                "age_max": 65,
                "genders": [1, 2]               # 1 = men, 2 = women
            }
            ```

            Regional + interest targeting
            -----------------------------

            ```python
            targeting = {
                "geo_locations": {
                    "regions": [
                        {"key": "3448"},        # São Paulo
                        {"key": "3451"}         # Rio de Janeiro
                    ],
                },
                "age_min": 25,
                "age_max": 45,
                "genders": [2],                # women only
                "interests": [
                    {"id": "6003139266461"},    # Futebol
                    {"id": "6003133743144"}     # Yoga
                ],
                "targeting_automation": {"advantage_audience": 1}
            }
            ```

            Advantage+ Audience only
            ------------------------

            ```python
            targeting = {
                "targeting_automation": {"advantage_audience": 1},
                "age_min": 18,
                "age_max": 65,
                "genders": [1, 2]               # 1 = men, 2 = women
            }
            ```
        optimization_goal (str)
            One value from mapping on section 1 above (must match the campaign objective).
        billing_event (str)
            One value from mapping on section 2 above (must match `optimization_goal`).
        bid_strategy (str, optional)
            Required when budget is set at adset level. Options are: LOWEST_COST_WITHOUT_CAP(default), LOWEST_COST_WITH_BID_CAP, COST_CAP, LOWEST_COST_WITH_MIN_ROAS.
        bid_amount (str, optional)
            Required when bid strategy is LOWEST_COST_WITH_BID_CAP or COST_CAP; amount in cents.
        roas_average_floor (str, optional)
            Required for LOWEST_COST_WITH_ROAS strategies; amount in cents.
        start_time, end_time (str, optional)
            ISO-8601 timestamps. `end_time` required with lifetime budgets.
        custom_event_type (str, required IF optimization_goal is OFFSITE_CONVERSIONS)
            Required for conversion optimization goals; type of conversion event. For optimization_goal OFFSITE_CONVERSIONS, default option is PURCHASE. Other options are: VIEW_CONTENT, ADD_TO_CART, ADD_TO_WISHLIST, INITIATE_CHECKOUT, PURCHASE, SUBSCRIBE, START_TRIAL.
        destination_type (str, optional)
            Required for conversion goals; type of destination are WEBSITE, APP, INSTAGRAM_DIRECT, INSTAGRAM_PROFILE. The default is WEBSITE.

        ──────────────────────────────────────────────────────────────────────────
        Examples
        ──────────────────────────────────────────────────────────────────────────
        **Traffic ad-set – auto-bid**

        ```python
        new_adset = create_adset(
            state=app_state,
            account_id="act_123",
            campaign_id="120123456",
            name="Women 25-34 • BR • Futebol",
            daily_budget="5000",
            optimization_goal="OFFSITE_CONVERSIONS",
            billing_event="IMPRESSIONS",
            bid_strategy="LOWEST_COST_WITHOUT_CAP",
            targeting={
                "geo_locations": {"countries": ["BR"]},
                "age_min": 25,
                "age_max": 34,
                "interests": [{"id": "6003139266461"}],
                "targeting_automation": {"advantage_audience": 1}
            },
            status="PAUSED"
        )
        """

        access_token = config.META_ACCESS_TOKEN
        account_id = act_id
        url = f"{FB_GRAPH_URL}/{account_id}/adsets"

        # Check required parameters
        if not all([account_id, campaign_id, name]):
            raise ValueError("account_id, campaign_id and name are required")
        if not optimization_goal or not billing_event:
            raise ValueError("optimization_goal and billing_event are required")

        if _requires_conversion_details(optimization_goal):
            if not pixel_id:
                raise ValueError("pixel_id is required for conversion goals")
            if not (custom_event_type):
                raise ValueError("Provide custom_event_type (standard)")
        if not account_id:
            return json.dumps({"error": "No account ID provided"}, indent=2)

        if not campaign_id:
            return json.dumps({"error": "No campaign ID provided"}, indent=2)

        if not name:
            return json.dumps({"error": "No ad set name provided"}, indent=2)

        if not optimization_goal:
            return json.dumps({"error": "No optimization goal provided"}, indent=2)

        if not billing_event:
            return json.dumps({"error": "No billing event provided"}, indent=2)

        if bid_strategy == "LOWEST_COST_WITH_MIN_ROAS" and not roas_average_floor:
            return json.dumps(
                {
                    "error": "ROAS average floor is required for LOWEST_COST_WITH_MIN_ROAS strategy"
                },
                indent=2,
            )

        # Basic targeting is required if not provided
        if not targeting:
            targeting = {
                "age_min": 18,
                "age_max": 65,
                "geo_locations": {"countries": ["BR"]},
                "targeting_automation": {"advantage_audience": 1},
            }

        if isinstance(targeting, str):
            try:
                targeting = json.loads(targeting)
            except json.JSONDecodeError as exc:
                return json.dumps(
                    {
                        "error": "targeting foi enviado como string, mas não é JSON válido",
                        "details": str(exc),
                        "received": targeting,
                    },
                    indent=2,
                    ensure_ascii=False,
                )

        base_params = {
            "access_token": access_token,
            "name": name,
            "campaign_id": campaign_id,
            "status": status,
            "optimization_goal": optimization_goal,
            "billing_event": billing_event,
        }

        if _requires_conversion_details(optimization_goal):
            promoted_object = {"pixel_id": pixel_id}
            promoted_object["custom_event_type"] = custom_event_type.upper()
            base_params["promoted_object"] = json.dumps(promoted_object)
            base_params["destination_type"] = destination_type
            base_params["conversion_domain"] = website_domain

        params = _prepare_params(
            base_params,
            targeting=targeting,
            daily_budget=daily_budget,
            lifetime_budget=lifetime_budget,
            bid_amount=bid_amount,
            bid_strategy=bid_strategy,
            start_time=start_time,
            end_time=end_time,
            roas_average_floor=roas_average_floor,
        )

        data = await make_graph_api_post(url, params)
        return json.dumps(data, indent=2)

    @mcp.tool()
    async def update_adset(
        adset_id: str = None,
        frequency_control_specs: List[Dict[str, Any]] = None,
        bid_strategy: str = None,
        bid_amount: int = None,
        status: str = None,
        targeting: Dict[str, Any] = None,
        optimization_goal: str = None,
    ) -> str:
        """
        Update an ad set with new settings including frequency caps.

        Args:
            adset_id: Meta Ads ad set ID
            frequency_control_specs: List of frequency control specifications
                                     (e.g. [{"event": "IMPRESSIONS", "interval_days": 7, "max_frequency": 3}])
            bid_strategy: Bid strategy (e.g., 'LOWEST_COST_WITH_BID_CAP', 'LOWEST_COST_WITHOUT_CAP(default)', 'COST_CAP', 'LOWEST_COST_WITH_MIN_ROAS')
            bid_amount: Bid amount in account currency (in cents for USD)
            status: Update ad set status (ACTIVE, PAUSED, etc.)
            targeting: Targeting specifications including targeting_automation
            targeting (dict | None):
                Targeting specification. **Key guidelines**

                * Provide either a **full spec** or just a
                  ``{"targeting_automation": ...}`` block to preserve existing rules.
                * **Geo-targeting** must include ``geo_locations`` plus
                  ``countries``.
                * When using *regions* or *cities*, include **only** the numeric
                  ``"key"``—omit ``"name"``.
                * Detailed targeting interests belong in ``interests`` (array of ID
                  dicts). You may mix interests with **Advantage+ Audience**
                  (``targeting_automation.advantage_audience = 1``).

                **Examples**

                *Minimal geo + one interest*::

                    {
                      "geo_locations": {"countries": ["BR"]},
                      "interests": [{"id": "6003139266461"}]  # Futebol
                    }

                *Geo region + multiple interests + Advantage Audience*::

                    {
                      "geo_locations": {
                        "regions": [{"key": "460"}],          # São Paulo
                      },
                      "age_min": 18,
                      "age_max": 45,
                      "genders": [1, 2],
                      "interests": [
                        {"id": "6003139266461"},               # Futebol
                        {"id": "6003349442628"}                # E-commerce
                      ],
                      "targeting_automation": {"advantage_audience": 1}
                    }

                *Advantage Audience **only** (keep the rest unchanged)*::

                    {
                      "targeting_automation": {"advantage_audience": 1}
                    }
            optimization_goal: Conversion optimization goal (e.g., 'LINK_CLICKS', 'CONVERSIONS', 'APP_INSTALLS', etc.)
        """
        if not adset_id:
            return json.dumps({"error": "No ad set ID provided"}, indent=2)

        changes = {}

        if frequency_control_specs is not None:
            changes["frequency_control_specs"] = json.dumps(frequency_control_specs)

        if bid_strategy is not None:
            changes["bid_strategy"] = bid_strategy

        if bid_amount is not None:
            changes["bid_amount"] = bid_amount

        if status is not None:
            changes["status"] = status

        if optimization_goal is not None:
            changes["optimization_goal"] = optimization_goal

        if targeting is not None:
            # Get current ad set details to preserve existing targeting settings
            access_token = config.META_ACCESS_TOKEN
            details_url = f"{FB_GRAPH_URL}/{adset_id}"
            details_params = {"access_token": access_token, "fields": "targeting"}
            current_details = await make_graph_api_call(details_url, details_params)

            # Check if the current ad set has targeting information
            current_targeting = current_details.get("targeting", {})

            if "targeting_automation" in targeting:
                # Only update targeting_automation while preserving other targeting settings
                if current_targeting:
                    merged_targeting = current_targeting.copy()
                    merged_targeting["targeting_automation"] = targeting[
                        "targeting_automation"
                    ]
                    changes["targeting"] = merged_targeting
                else:
                    # If there's no existing targeting, we need to create a basic one
                    # Meta requires at least a geo_locations setting
                    basic_targeting = {
                        "targeting_automation": targeting["targeting_automation"],
                        "geo_locations": {
                            "countries": ["BR"]
                        },  # Using US as default location
                    }
                    changes["targeting"] = basic_targeting
            else:
                # Full targeting replacement
                changes["targeting"] = targeting

            changes["targeting"] = json.dumps(targeting)

        if not changes:
            return json.dumps({"error": "No update parameters provided"}, indent=2)

        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{adset_id}"

        params = {"access_token": access_token, **changes}

        data = await make_graph_api_post(url, params)
        return json.dumps(data, indent=2)
