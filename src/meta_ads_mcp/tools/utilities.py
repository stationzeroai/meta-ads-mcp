import json
import re
from typing import Optional, List, Dict, Any, Union

from fastmcp import FastMCP

from meta_ads_mcp.config import config
from meta_ads_mcp.meta_api_client.client import make_graph_api_call
from meta_ads_mcp.meta_api_client.constants import FB_GRAPH_URL


def _decode_unicode_escapes(obj: Union[str, List, Dict]):
    """
    Recursively walk any str / list / dict and turn literal "\\uXXXX"
    sequences into real UTF-8 characters.
    """
    if isinstance(obj, str):
        try:
            # `unicode_escape` interprets the escape codes
            return obj.encode("utf-8").decode("unicode_escape")
        except UnicodeDecodeError:
            return obj  # leave untouched on failure
    if isinstance(obj, list):
        return [_decode_unicode_escapes(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _decode_unicode_escapes(v) for k, v in obj.items()}
    return obj


def register_tools(mcp: FastMCP):
    @mcp.tool()
    async def get_region_key_for_adsets(
        query: str,
    ) -> str:
        """
        Resolve Brazilian **state/region** geo-IDs (one request per token).

        Args:
            query (str):
                Region tokens separated by comma **or** pipe, e.g.
                ``"sao, rio de janeiro"`` or ``"sao|rio|minas"``.
                Case-insensitive; accents optional.

        Returns:
            str:
                Pretty JSON::

                    {
                      "regions": [
                        {"name": "São Paulo",      "key": "3448"},
                        {"name": "Rio de Janeiro", "key": "3451"}
                      ]
                    }
        """
        locale = "pt_BR"
        limit = 5
        url = f"{FB_GRAPH_URL}/search"
        access_token = config.META_ACCESS_TOKEN

        # Tokenise & deduplicate (case-insensitive)
        raw_tokens = [t.strip() for t in re.split(r"[,\|]", query) if t.strip()]

        seen, tokens = set(), []
        for tok in raw_tokens:
            lower = tok.lower()
            if lower not in seen:
                seen.add(lower)
                tokens.append(tok)

        # Query each token individually
        results: List[Dict[str, Any]] = []

        for token in tokens:
            params = {
                "access_token": access_token,
                "type": "adgeolocation",
                "location_types": json.dumps(["region"]),
                "country_code": "BR",
                "q": token,
                "limit": limit,
                "locale": locale,
            }

            try:
                data = (await make_graph_api_call(url, params)).get("data", [])
                top_match = data[0] if data else {"name": token.title(), "key": None}

                results.append({"name": top_match["name"], "key": top_match["key"]})
            except Exception as e:
                results.append({"name": token.title(), "key": None, "error": str(e)})

        return json.dumps({"regions": results}, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def list_pixels(account_id: str) -> str:
        """Return datasets/pixels associated with *account_id*.

        Args:
            account_id (str): Ad account (``act_<ID>``) **or** Business ID.

        Returns:
            str: JSON string containing list of pixels with id and name fields.
        """
        access_token = config.META_ACCESS_TOKEN
        url = f"{FB_GRAPH_URL}/{account_id}/adspixels"
        params = {"access_token": access_token, "fields": "id,name"}

        data = await make_graph_api_call(url, params)

        return json.dumps(data.get("data", []), indent=2, ensure_ascii=False)

    @mcp.tool()
    async def search_ad_interests(keywords: Union[List[str], str]) -> str:
        """
        Query Meta's *adinterest* catalog and return matching interest objects.

        Args:
            keywords (str | list[str]):
                A single search term (e.g. ``"futebol"``) **or** up to a maximum of 2 terms
                (e.g. ``["futebol", "esportes"]``). Empty strings are ignored.

        Returns:
            str:
                JSON payload of up to **5** interest objects, decoded so that
                accented characters (``á, ç, ê``) appear as human-readable text
                rather than ``\\uXXXX`` escape sequences.

        Notes:
            * The Marketing-API may return duplicate IDs when multiple terms are
              queried; deduplicate on the caller side if necessary.
            * Maximum 2 search terms allowed per query.
        """
        access_token = config.META_ACCESS_TOKEN

        # Parse keywords
        if isinstance(keywords, str):
            tokens = [t.strip() for t in re.split(r"[,\|]", keywords) if t.strip()]
        else:  # list[str]
            tokens = [t.strip() for t in keywords if t.strip()]

        # Enforce ≤ 2 tokens
        if len(tokens) > 2:
            return json.dumps(
                {
                    "error": "You can search at most two interest terms.",
                    "received_terms": tokens,
                },
                indent=2,
                ensure_ascii=False,
            )

        q_param = tokens[0] if len(tokens) == 1 else tokens

        # Make API call
        url = f"{FB_GRAPH_URL}/search"
        params = {
            "access_token": access_token,
            "q": json.dumps(q_param) if isinstance(q_param, list) else q_param,
            "type": "adinterest",
            "limit": 5,
            "locale": "pt_BR",
        }

        raw_data = await make_graph_api_call(url, params)

        # Clean up any "\\uXXXX" escapes
        clean_data = _decode_unicode_escapes(raw_data)

        return json.dumps(clean_data, indent=2, ensure_ascii=False)
