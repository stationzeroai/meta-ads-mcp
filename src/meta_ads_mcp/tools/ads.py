from typing import Optional, List, Dict, Any
import json
import requests

from fastmcp import FastMCP

from meta_ads_mcp.config import config
from meta_ads_mcp.meta_api_client.client import make_graph_api_post
from meta_ads_mcp.meta_api_client.constants import FB_GRAPH_URL


def register_tools(mcp: FastMCP):
    @mcp.tool()
    async def create_ad_with_catalog_creative(
        act_id: str,
        name: str | None = None,
        adset_id: str | None = None,
        creative_id: str | None = None,
        status: str = "PAUSED",
        tracking_specs: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Create an **Ad** that re‑uses an existing *catalog* creative.

        The tool sends a ``POST`` request to ``/<AD_ACCOUNT_ID>/ads`` with a
        *JSON‑encoded* ``creative`` field and returns the Marketing‑API response.

        Args:
            act_id: Ad account ID (with the ``act_`` prefix).
            name (str):
                Human‑readable ad name. *Required*.
            adset_id (str):
                ID of the ad set that will contain this ad. *Required*.
            creative_id (str):
                ID of an existing *template creative* (usually produced by
                the tool `create_catalog_creative`). *Required*.
            status (str, optional):
                Initial delivery status. Default ``"PAUSED"`` – recommended to
                review before activating.
            tracking_specs (list[dict], optional):
                Custom Pixel/App/Offline tracking specs. Must be JSON‑serialisable.

        Returns:
            str: Pretty‑printed JSON containing the new ``ad_id`` on success, or an
            error payload with ``params_sent`` and details.

        Example:
            >>> ad_json = create_ad_with_catalog_creative(
            ...     act_id="act_123456789",
            ...     name="Women 25‑34 • BR • Catalog",
            ...     adset_id="120225076465790427",
            ...     creative_id="1693813855352492",
            ... )
            >>> ad_id = json.loads(ad_json)["id"]

        Notes:
            * **Compound field** ``creative`` **must** be JSON‑encoded; the helper
              handles that automatically.
            * Omit ``tracking_specs`` unless you need custom attribution – the ad
              inherits Pixel mappings from the ad set by default.
        """

        # ──────────────────────────────────────────────────────────────────────
        # 0. Resolve credentials / IDs
        # ──────────────────────────────────────────────────────────────────────
        access_token = config.META_ACCESS_TOKEN
        account_id = act_id

        # ──────────────────────────────────────────────────────────────────────
        # 1. Validate required fields
        # ──────────────────────────────────────────────────────────────────────
        missing: list[str] = [
            field
            for field, value in {
                "account_id": account_id,
                "name": name,
                "adset_id": adset_id,
                "creative_id": creative_id,
            }.items()
            if not value
        ]
        if missing:
            return json.dumps(
                {"error": f"Missing required fields: {', '.join(missing)}"}, indent=2
            )

        # ──────────────────────────────────────────────────────────────────────
        # 2. Build request parameters
        # ──────────────────────────────────────────────────────────────────────
        base_params: Dict[str, Any] = {
            "access_token": access_token,
            "name": name,
            "adset_id": adset_id,
            "status": status,
            # creative must be JSON-encoded
            "creative": json.dumps({"creative_id": creative_id}),
        }

        if tracking_specs is not None:
            base_params["tracking_specs"] = json.dumps(tracking_specs)

        # ──────────────────────────────────────────────────────────────────────
        # 3. POST to Graph-API
        # ──────────────────────────────────────────────────────────────────────
        url = f"{FB_GRAPH_URL}/{account_id}/ads"

        data = await make_graph_api_post(url, base_params)

        return json.dumps(data, indent=2)

    def _build_dfo_spec(
        *,
        image_template: bool = True,
        image_touchups: bool = True,
        text_optimizations: bool = True,
        inline_comment: bool = True,
        video_auto_crop: bool = True,
    ) -> str:
        """Return a ``degrees_of_freedom_spec`` JSON string.

        Each boolean argument maps to an Advantage+ Creative feature. ``True``
        converts to ``"OPT_IN"`` and ``False`` to ``"OPT_OUT"``.

        Args:
            image_template: Opt‑in/out for automatic image templates.
            image_touchups: Opt‑in/out for AI image touch‑ups.
            text_optimizations: Opt‑in/out for AI text tweaks.
            inline_comment: Opt‑in/out for inline‑comment generation.
            video_auto_crop: Opt‑in/out for video auto‑crop (ignored by image ads).

        Returns:
            A JSON‑encoded *degrees_of_freedom_spec*.
        """

        def _status(flag: bool) -> Dict[str, str]:
            return {"enroll_status": "OPT_IN" if flag else "OPT_OUT"}

        spec = {
            "creative_features_spec": {
                "image_template": _status(image_template),
                "image_touchups": _status(image_touchups),
                "text_optimizations": _status(text_optimizations),
                "inline_comment": _status(inline_comment),
                "video_auto_crop": _status(video_auto_crop),
            }
        }
        return json.dumps(spec)

    # ---------------------------------------------------------------------------
    # Main helper
    # ---------------------------------------------------------------------------

    @mcp.tool()
    async def create_catalog_creative(
        act_id: str,
        facebook_page_id: str,
        name: str,
        product_set_id: str,
        link: str,
        message: str,
        headline: str,
        caption: str,
        instagram_user_id: Optional[str] = None,
        call_to_action: str = "SHOP_NOW",
        template_format: str = "carousel_images_multi_items",
        multi_share_end_card: bool = False,
        enable_dco: bool = False,
        # Advantage+ feature flags
        adv_image_template: bool = True,
        adv_image_touchups: bool = True,
        adv_text_optimizations: bool = True,
        adv_inline_comment: bool = True,
        adv_video_auto_crop: bool = True,
    ) -> str:
        """Create a catalogue *template creative* (Dynamic‑Ads).

        This helper sends a ``POST`` request to
        ``/<AD_ACCOUNT_ID>/adcreatives`` using Graph‑API **v22 or later**. If
        ``enable_dco`` is ``True``, a fully customisable
        ``degrees_of_freedom_spec`` is attached based on the ``adv_*`` flags.

        ### State prerequisites
            * ``state.meta_api_token`` – Long‑lived system‑user token.
            * ``state.act_id`` – Ad‑account ID **including** the ``act_`` prefix.
            * ``state.facebook_page_id`` – Page that owns the ad.
            * ``state.instagram_user_id`` – *(optional)* IG professional account ID
              for cross‑posting.

        Args:
            state: LangGraph‑injected state object.
            name: Internal creative name (≤ 255 chars).
            product_set_id: Catalogue product‑set ID to advertise.
            link: Final URL that users land on.
            message: Primary (body) text.
            headline: Headline text.
            caption: Optional link caption.
            call_to_action: CTA enum (default ``"SHOP_NOW"``). **Possible values** →
                ``"SHOP_NOW"``, ``"LEARN_MORE"``, ``"SIGN_UP"``, ``"SUBSCRIBE"``,
                ``"INSTALL_APP"``, ``"DOWNLOAD"``, ``"WATCH_MORE"``,
                ``"GET_OFFER"``, ``"CONTACT_US"``, ``"CALL_NOW"``,
                ``"WHATSAPP_MESSAGE"``, ``"BOOK_TRAVEL"``, ``"EVENT_RSVP"``,
                ``"MESSAGE_PAGE"``, ``"APPLY_NOW"``.
            template_format: Layout enum (default
                ``"carousel_images_multi_items"``). **Possible values** →
                ``"carousel_images_multi_items"``, ``"carousel_images_single_item"``,
                ``"collection"``, ``"single_image"``, ``"single_video"``,
                ``"slideshow"``, ``"carousel_videos_multi_items"``.
            multi_share_end_card: Whether to append a multi‑share end card.
                **Possible values** → ``True`` or ``False``.
            enable_dco: Opts in to Advantage+ automatic modifications when set to ``True``. **Possible
                values** → ``True`` or ``False``.
            adv_image_template: Opt‑in/out for ``image_template`` advantage+ automatic adjustments feature.
            adv_image_touchups: Opt‑in/out for ``image_touchups`` advantage+ automatic adjustments feature.
            adv_text_optimizations: Opt‑in/out for ``text_optimizations`` advantage+ automatic adjustments feature.
            adv_inline_comment: Opt‑in/out for ``inline_comment`` advantage+ automatic adjustments feature.
            adv_video_auto_crop: Opt‑in/out for ``video_auto_crop`` advantage+ automatic adjustments feature.

        Returns:
            str: Pretty‑printed JSON containing either the new ``creative_id`` or a
            Graph‑API error payload.

        Raises:
            httpx.HTTPStatusError: Raised for non‑2xx responses.
        """

        access_token = config.META_ACCESS_TOKEN
        account_id = act_id
        page_id = facebook_page_id
        ig_id = instagram_user_id

        # ---------------- template_data ----------------
        template_data: Dict[str, Any] = {
            "link": link,
            "call_to_action": {"type": call_to_action},
            "format_option": template_format,
            "multi_share_end_card": multi_share_end_card,
        }
        if message:
            template_data["message"] = message
        if headline:
            template_data["name"] = headline
        if caption:
            template_data["caption"] = caption

        # ---------------- object_story_spec ------------
        object_story_spec: Dict[str, Any] = {
            "page_id": page_id,
            "template_data": template_data,
        }
        if ig_id:
            object_story_spec["instagram_user_id"] = ig_id

        # ---------------- POST params ------------------
        params: Dict[str, Any] = {
            "access_token": access_token,
            "name": name,
            "object_story_spec": json.dumps(object_story_spec, ensure_ascii=False),
            "product_set_id": product_set_id,
        }
        if enable_dco:
            params["degrees_of_freedom_spec"] = _build_dfo_spec(
                image_template=adv_image_template,
                image_touchups=adv_image_touchups,
                text_optimizations=adv_text_optimizations,
                inline_comment=adv_inline_comment,
                video_auto_crop=adv_video_auto_crop,
            )

        # ---------------- POST request -----------------
        url = f"{FB_GRAPH_URL}/{account_id}/adcreatives"
        response = await make_graph_api_post(url, params)

        return json.dumps(response, indent=2, ensure_ascii=False)

    @mcp.tool()
    def fetch_product_sets(
        catalog_id: str,
    ) -> str:
        """Fetch **Product Sets** from a Commerce Catalog.

        Performs a ``GET /<CATALOG_ID>/product_sets`` request and returns the
        Marketing‑API JSON response. Supports basic pagination via the ``after``
        cursor.

        Args:
            catalog_id: The Commerce Catalog ID.

        Returns:
            str: Pretty‑printed JSON containing the list of product‑set objects or
            an error payload in the same format used by ``make_graph_api_post``.
        """

        access_token = config.META_ACCESS_TOKEN

        params: Dict[str, Any] = {
            "access_token": access_token,
            "limit": 100,
        }

        url = f"{FB_GRAPH_URL}/{catalog_id}/product_sets"

        try:
            response = requests.get(url, params=params, timeout=30)
            response_json = response.json()

            if "error" in response_json:
                return json.dumps(
                    {
                        "error": response_json["error"],
                        "url": url,
                        "params_sent": params,
                        "status_code": response.status_code,
                    },
                    indent=2,
                    ensure_ascii=False,
                )

            response.raise_for_status()
            return json.dumps(response_json, indent=2, ensure_ascii=False)

        except requests.exceptions.RequestException as exc:
            error_details: Dict[str, Any] = {
                "error": "Request failed",
                "details": str(exc),
                "url": url,
                "params_sent": params,
            }
            if hasattr(exc, "response") and exc.response is not None:
                error_details["status_code"] = exc.response.status_code
                try:
                    api_error = exc.response.json()
                    if "error" in api_error:
                        error_details["api_error"] = api_error["error"]
                except Exception:  # noqa: BLE001
                    error_details["response_text"] = exc.response.text

            return json.dumps(error_details, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def edit_ad(
        ad_id: str,
        name: Optional[str] = None,
        status: Optional[str] = None,
        adset_id: Optional[str] = None,
        creative_id: Optional[str] = None,
        tracking_specs: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Edit an existing Facebook ad by updating any of its editable fields.

        Sends a ``POST /<AD_ID>`` request with the fields to update.

        Args:
            ad_id: The Ad ID to be edited.
            name: New ad name (optional).
            status: New ad status (optional). Possible values:
                - "ACTIVE": Ad is running
                - "PAUSED": Ad is paused but can be reactivated
                - "DELETED": Ad is archived (cannot be reactivated)
                - "ARCHIVED": Ad is archived (cannot be reactivated)
            adset_id: Move ad to a different ad set (optional).
            creative_id: Update ad creative (optional).
            tracking_specs: Update tracking specifications (optional).

        Returns:
            str: Pretty‑printed JSON with update result or error payload.

        Example:
            >>> # Pause an ad
            >>> edit_ad(state, ad_id="123456789", status="PAUSED")

            >>> # Rename and activate an ad
            >>> edit_ad(ad_id="123456789", name="New Ad Name", status="ACTIVE")

            >>> # Move ad to different adset and update creative
            >>> edit_ad(ad_id="123456789", adset_id="987654321", creative_id="456789123")
        """

        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{ad_id}"

        # Build parameters with only the fields that are being updated
        params = {"access_token": access_token}

        if name is not None:
            params["name"] = name

        if status is not None:
            params["status"] = status

        if adset_id is not None:
            params["adset_id"] = adset_id

        if creative_id is not None:
            params["creative"] = json.dumps({"creative_id": creative_id})

        if tracking_specs is not None:
            params["tracking_specs"] = json.dumps(tracking_specs)

        # Check if any parameters were provided
        if len(params) == 1:  # Only access_token
            return json.dumps(
                {
                    "error": "No fields provided to update. Please specify at least one field to edit."
                },
                indent=2,
                ensure_ascii=False,
            )

        try:
            result = await make_graph_api_post(url, params)
            return json.dumps(result, indent=2, ensure_ascii=False)
        except Exception as exc:
            return json.dumps(
                {
                    "error": "Failed to edit ad",
                    "details": str(exc),
                    "ad_id": ad_id,
                    "params_sent": {
                        k: v for k, v in params.items() if k != "access_token"
                    },
                },
                indent=2,
                ensure_ascii=False,
            )

    @mcp.tool()
    async def bulk_update_status(
        object_ids: List[str],
        object_type: str,
        status: str,
    ) -> str:
        """Activate or deactivate multiple Facebook ads, adsets, or campaigns at once.

        Sends bulk update requests to change the status of multiple objects simultaneously.
        This is more efficient than updating objects one by one.

        Args:
            object_ids: List of IDs to update (ads, adsets, or campaigns).
            object_type: Type of objects being updated. Possible values:
                - "ads": Update Facebook ads
                - "adsets": Update ad sets
                - "campaigns": Update campaigns
            status: New status to set for all objects. Possible values:
                - "ACTIVE": Object is running
                - "PAUSED": Object is paused but can be reactivated
                - "DELETED": Object is archived (cannot be reactivated)
                - "ARCHIVED": Object is archived (cannot be reactivated)

        Returns:
            str: Pretty‑printed JSON with bulk update results, including success count,
            failed updates, and detailed error information.

        Example:
            >>> # Pause multiple ads
            >>> bulk_update_status(
            ...     state,
            ...     object_ids=["123456789", "987654321", "456789123"],
            ...     object_type="ads",
            ...     status="PAUSED"
            ... )

            >>> # Activate multiple campaigns
            >>> bulk_update_status(
            ...     state,
            ...     object_ids=["111222333", "444555666"],
            ...     object_type="campaigns",
            ...     status="ACTIVE"
            ... )

            >>> # Pause multiple adsets
            >>> bulk_update_status(
            ...     state,
            ...     object_ids=["789123456", "321654987"],
            ...     object_type="adsets",
            ...     status="PAUSED"
            ... )
        """

        access_token = config.META_ACCESS_TOKEN

        # Validate object_type
        valid_types = ["ads", "adsets", "campaigns"]
        if object_type not in valid_types:
            return json.dumps(
                {
                    "error": f"Invalid object_type '{object_type}'. Must be one of: {', '.join(valid_types)}",
                    "valid_types": valid_types,
                },
                indent=2,
                ensure_ascii=False,
            )

        # Validate status
        valid_statuses = ["ACTIVE", "PAUSED", "DELETED", "ARCHIVED"]
        if status not in valid_statuses:
            return json.dumps(
                {
                    "error": f"Invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}",
                    "valid_statuses": valid_statuses,
                },
                indent=2,
                ensure_ascii=False,
            )

        # Validate object_ids
        if not object_ids or len(object_ids) == 0:
            return json.dumps(
                {"error": "object_ids list cannot be empty"},
                indent=2,
                ensure_ascii=False,
            )

        # Track results
        successful_updates = []
        failed_updates = []

        # Process each object
        for object_id in object_ids:
            try:
                url = f"{FB_GRAPH_URL}/{object_id}"
                params = {"access_token": access_token, "status": status}

                result = await make_graph_api_post(url, params)

                if "error" in result:
                    failed_updates.append(
                        {"id": object_id, "error": result["error"], "type": object_type}
                    )
                else:
                    successful_updates.append(
                        {
                            "id": object_id,
                            "success": result.get("success", True),
                            "type": object_type,
                            "new_status": status,
                        }
                    )

            except Exception as exc:
                failed_updates.append(
                    {"id": object_id, "error": str(exc), "type": object_type}
                )

        # Prepare summary response
        response = {
            "summary": {
                "total_objects": len(object_ids),
                "successful_updates": len(successful_updates),
                "failed_updates": len(failed_updates),
                "object_type": object_type,
                "status_set": status,
            },
            "successful_updates": successful_updates,
            "failed_updates": failed_updates,
        }

        return json.dumps(response, indent=2, ensure_ascii=False)
