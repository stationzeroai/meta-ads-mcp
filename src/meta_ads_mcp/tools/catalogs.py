import json
from typing import Optional, List, Dict, Any

from fastmcp import FastMCP

from meta_ads_mcp.config import config
from meta_ads_mcp.meta_api_client.client import make_graph_api_call
from meta_ads_mcp.meta_api_client.constants import FB_GRAPH_URL


def register_tools(mcp: FastMCP):
    @mcp.tool()
    async def list_catalogs(
        business_id: str,
        fields: Optional[List[str]] = None,
        limit: int = 25,
        after: Optional[str] = None,
        before: Optional[str] = None,
    ) -> str:
        """List product catalogs associated with a business.

        Args:
            business_id (str): The business ID (format: business_XXXXXXXXXX or just the numeric ID).
            fields (List[str]): Specific fields to retrieve. If not provided, default fields are used.
                Available fields include: id, name, business, product_count, vertical, 
                flight_catalog_settings, event_stats, is_catalog_segment.
            limit (int): Maximum number of results to return per page (default: 25, max: 100).
            after (str): Pagination cursor for next page.
            before (str): Pagination cursor for previous page.

        Returns:
            str: JSON string containing list of catalogs with 'data' and 'paging' keys.
        """
        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{business_id}/owned_product_catalogs"

        effective_fields = fields if fields else ["id", "name", "product_count", "vertical"]

        params = {
            "access_token": access_token,
            "fields": ",".join(effective_fields),
            "limit": limit,
        }

        if after:
            params["after"] = after

        if before:
            params["before"] = before

        data = await make_graph_api_call(url, params)

        return json.dumps(data, indent=2)

    @mcp.tool()
    async def get_catalog_details(
        catalog_id: str,
        fields: Optional[List[str]] = None,
    ) -> str:
        """Get details of a specific product catalog.

        Args:
            catalog_id (str): The product catalog ID.
            fields (List[str]): Specific fields to retrieve. If not provided, default fields are used.
                Available fields include: id, name, business, product_count, vertical,
                flight_catalog_settings, event_stats, is_catalog_segment, store_catalog_settings.

        Returns:
            str: JSON string containing the catalog details.
        """
        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{catalog_id}"

        effective_fields = fields if fields else [
            "id",
            "name",
            "business",
            "product_count",
            "vertical",
        ]

        params = {
            "access_token": access_token,
            "fields": ",".join(effective_fields),
        }

        data = await make_graph_api_call(url, params)

        return json.dumps(data, indent=2)

    @mcp.tool()
    async def fetch_products(
        catalog_id: str,
        fields: Optional[List[str]] = None,
        filtering: Optional[List[dict]] = None,
        limit: int = 25,
        after: Optional[str] = None,
        before: Optional[str] = None,
    ) -> str:
        """Fetch products from a product catalog.

        This tool retrieves products from a Meta Commerce catalog with support for
        filtering, pagination, and custom field selection.

        Args:
            catalog_id (str): The product catalog ID.
            fields (List[str]): Specific fields to retrieve. If not provided, default fields are used.
                Available fields include: id, name, description, price, url, image_url, 
                brand, availability, condition, retailer_id, product_type, custom_label_0,
                custom_label_1, custom_label_2, custom_label_3, custom_label_4, 
                inventory, sale_price, additional_image_urls, age_group, color, gender,
                material, pattern, size, gtin, mpn.
            filtering (List[dict]): Filter products. Each filter should have 'field', 'operator', 
                and 'value' keys. Example: [{"field": "availability", "operator": "EQUAL", "value": "in stock"}].
                Available operators: EQUAL, NOT_EQUAL, IN, NOT_IN, CONTAIN, NOT_CONTAIN,
                GREATER_THAN, GREATER_THAN_OR_EQUAL, LESS_THAN, LESS_THAN_OR_EQUAL.
            limit (int): Maximum number of results to return per page (default: 25, max: 100).
            after (str): Pagination cursor for next page.
            before (str): Pagination cursor for previous page.

        Returns:
            str: JSON string containing list of products with 'data' and 'paging' keys.
        
        Examples:
            Fetch products with custom fields:
            ```python
            result = await fetch_products(
                catalog_id="123456789",
                fields=["id", "name", "price", "availability", "image_url"],
                limit=50
            )
            ```

            Filter products by availability:
            ```python
            result = await fetch_products(
                catalog_id="123456789",
                filtering=[{"field": "availability", "operator": "EQUAL", "value": "in stock"}]
            )
            ```
        """
        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{catalog_id}/products"

        # Default fields for product information
        effective_fields = fields if fields else [
            "id",
            "name",
            "description",
            "price",
            "url",
            "image_url",
            "brand",
            "availability",
            "retailer_id",
        ]

        params = {
            "access_token": access_token,
            "fields": ",".join(effective_fields),
            "limit": limit,
        }

        if filtering:
            params["filter"] = json.dumps(filtering)

        if after:
            params["after"] = after

        if before:
            params["before"] = before

        data = await make_graph_api_call(url, params)

        return json.dumps(data, indent=2)

    @mcp.tool()
    async def get_product_details(
        product_id: str,
        fields: Optional[List[str]] = None,
    ) -> str:
        """Get details of a specific product from a catalog.

        Args:
            product_id (str): The product ID.
            fields (List[str]): Specific fields to retrieve. If not provided, all available fields are retrieved.
                Available fields include: id, name, description, price, url, image_url,
                brand, availability, condition, retailer_id, product_type, custom_label_0,
                custom_label_1, custom_label_2, custom_label_3, custom_label_4,
                inventory, sale_price, additional_image_urls, age_group, color, gender,
                material, pattern, size, gtin, mpn, sale_price_effective_date,
                shipping, shipping_weight, tax, title, commerce_insights.

        Returns:
            str: JSON string containing the product details.
        """
        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{product_id}"

        effective_fields = fields if fields else [
            "id",
            "name",
            "description",
            "price",
            "url",
            "image_url",
            "brand",
            "availability",
            "condition",
            "retailer_id",
            "product_type",
            "inventory",
            "sale_price",
        ]

        params = {
            "access_token": access_token,
            "fields": ",".join(effective_fields),
        }

        data = await make_graph_api_call(url, params)

        return json.dumps(data, indent=2)

    @mcp.tool()
    async def fetch_product_sets(
        catalog_id: str,
        fields: Optional[List[str]] = None,
        limit: int = 25,
        after: Optional[str] = None,
        before: Optional[str] = None,
    ) -> str:
        """Fetch product sets from a product catalog.

        Product sets are collections of products from a catalog that can be used for
        dynamic ads targeting. This tool retrieves all product sets with pagination support.

        Args:
            catalog_id (str): The product catalog ID.
            fields (List[str]): Specific fields to retrieve. If not provided, default fields are used.
                Available fields include: id, name, filter, product_count, product_catalog,
                retailer_id, auto_creation_url.
            limit (int): Maximum number of results to return per page (default: 25, max: 100).
            after (str): Pagination cursor for next page.
            before (str): Pagination cursor for previous page.

        Returns:
            str: JSON string containing list of product sets with 'data' and 'paging' keys.
        """
        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{catalog_id}/product_sets"

        effective_fields = fields if fields else [
            "id",
            "name",
            "filter",
            "product_count",
        ]

        params = {
            "access_token": access_token,
            "fields": ",".join(effective_fields),
            "limit": limit,
        }

        if after:
            params["after"] = after

        if before:
            params["before"] = before

        data = await make_graph_api_call(url, params)

        return json.dumps(data, indent=2)

    @mcp.tool()
    async def get_product_set_details(
        product_set_id: str,
        fields: Optional[List[str]] = None,
    ) -> str:
        """Get details of a specific product set.

        Args:
            product_set_id (str): The product set ID.
            fields (List[str]): Specific fields to retrieve. If not provided, default fields are used.
                Available fields include: id, name, filter, product_count, product_catalog,
                retailer_id, auto_creation_url.

        Returns:
            str: JSON string containing the product set details.
        """
        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{product_set_id}"

        effective_fields = fields if fields else [
            "id",
            "name",
            "filter",
            "product_count",
        ]

        params = {
            "access_token": access_token,
            "fields": ",".join(effective_fields),
        }

        data = await make_graph_api_call(url, params)

        return json.dumps(data, indent=2)

    @mcp.tool()
    async def fetch_products_in_product_set(
        product_set_id: str,
        fields: Optional[List[str]] = None,
        limit: int = 25,
        after: Optional[str] = None,
        before: Optional[str] = None,
    ) -> str:
        """Fetch products that belong to a specific product set.

        Args:
            product_set_id (str): The product set ID.
            fields (List[str]): Specific fields to retrieve from each product.
                Available fields include: id, name, description, price, url, image_url,
                brand, availability, condition, retailer_id, product_type.
            limit (int): Maximum number of results to return per page (default: 25, max: 100).
            after (str): Pagination cursor for next page.
            before (str): Pagination cursor for previous page.

        Returns:
            str: JSON string containing list of products in the set with 'data' and 'paging' keys.
        """
        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{product_set_id}/products"

        effective_fields = fields if fields else [
            "id",
            "name",
            "description",
            "price",
            "url",
            "image_url",
            "brand",
            "availability",
        ]

        params = {
            "access_token": access_token,
            "fields": ",".join(effective_fields),
            "limit": limit,
        }

        if after:
            params["after"] = after

        if before:
            params["before"] = before

        data = await make_graph_api_call(url, params)

        return json.dumps(data, indent=2)
