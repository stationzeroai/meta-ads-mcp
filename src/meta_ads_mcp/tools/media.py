"""Media and creative tools for creating ads with S3-hosted media."""

import asyncio
import json
import os
import re
import io
import tempfile
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlparse

from fastmcp import FastMCP

from meta_ads_mcp.config import config
from meta_ads_mcp.meta_api_client.client import make_graph_api_post
from meta_ads_mcp.meta_api_client.constants import FB_GRAPH_URL

try:
    import boto3
    from botocore.exceptions import ClientError

    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False

try:
    from PIL import Image
    import cv2

    VIDEO_PROCESSING_AVAILABLE = True
except ImportError:
    try:
        from PIL import Image

        VIDEO_PROCESSING_AVAILABLE = False
    except ImportError:
        VIDEO_PROCESSING_AVAILABLE = False


def _extract_domain_from_url(url: str) -> str:
    """Extract domain from URL for use as caption.

    Args:
        url: Full URL (e.g., "https://www.example.com/path")

    Returns:
        Domain name (e.g., "example.com")
    """
    if not url:
        return ""

    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        # Remove 'www.' prefix if present
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def _validate_ad_creative_params(
    headline: str, caption: str, instagram_user_id: Optional[str]
) -> List[str]:
    """Validate ad creative parameters and return list of warnings.

    Args:
        headline: Ad headline text
        caption: Link caption text
        instagram_user_id: Instagram account ID (if targeting Instagram)

    Returns:
        List of warning messages (empty if no issues)
    """
    warnings = []

    # Headline validation
    if instagram_user_id and len(headline) > 40:
        warnings.append(
            f"Headline is {len(headline)} characters ('{headline}'). "
            f"Instagram recommends max 40 characters for optimal display."
        )
    elif len(headline) > 60:
        warnings.append(
            f"Headline is {len(headline)} characters ('{headline}'). "
            f"Facebook recommends max 60 characters for optimal display."
        )

    # Caption validation
    if caption and len(caption) > 30:
        warnings.append(
            f"Caption is {len(caption)} characters ('{caption}'). "
            f"Caption should be a short link caption (like 'example.com'), not a description. "
            f"Long captions may cause 'Invalid parameter' errors."
        )

    return warnings


def _parse_s3_url(s3_url: str) -> Tuple[str, str]:
    """Parse S3 URL to extract bucket and key.

    Args:
        s3_url: S3 URL in format https://bucket.s3.region.amazonaws.com/key
                or s3://bucket/key

    Returns:
        Tuple of (bucket_name, object_key)

    Raises:
        ValueError: If URL format is invalid
    """
    # Handle s3:// format
    if s3_url.startswith("s3://"):
        parts = s3_url[5:].split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid S3 URL format: {s3_url}")
        return parts[0], parts[1]

    # Handle https:// format
    if s3_url.startswith("https://"):
        # Pattern: https://bucket.s3.region.amazonaws.com/key
        pattern = r"https://([^.]+)\.s3\.([^.]+)\.amazonaws\.com/(.+)"
        match = re.match(pattern, s3_url)
        if match:
            bucket, region, key = match.groups()
            return bucket, key

        # Pattern: https://s3.region.amazonaws.com/bucket/key
        pattern = r"https://s3\.([^.]+)\.amazonaws\.com/([^/]+)/(.+)"
        match = re.match(pattern, s3_url)
        if match:
            region, bucket, key = match.groups()
            return bucket, key

    raise ValueError(f"Invalid S3 URL format: {s3_url}")


def _get_s3_client():
    """Create and return an S3 client with credentials from environment."""
    if not S3_AVAILABLE:
        raise ImportError("boto3 not installed. Install with: pip install boto3")

    session = boto3.Session(
        aws_access_key_id=config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
        region_name=config.AWS_S3_REGION or config.AWS_REGION,
    )
    return session.client("s3")


def _get_image_from_aws_s3_sync(s3_url: str) -> bytes:
    """Download image from AWS S3 (synchronous)."""
    try:
        bucket_name, object_key = _parse_s3_url(s3_url)
        s3_client = _get_s3_client()
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        return response["Body"].read()
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "NoSuchKey":
            raise ValueError(f"Image not found in S3: {s3_url}")
        elif error_code == "NoSuchBucket":
            raise ValueError(f"S3 bucket not found: {bucket_name}")
        else:
            raise ValueError(f"Error downloading image from S3: {e}")
    except Exception as e:
        raise ValueError(f"Error downloading image from S3: {e}")


async def _get_image_from_aws_s3(s3_url: str) -> bytes:
    """Async wrapper for downloading image from AWS S3."""
    return await asyncio.to_thread(_get_image_from_aws_s3_sync, s3_url)


def _get_video_from_aws_s3_sync(s3_url: str) -> bytes:
    """Download video from AWS S3 (synchronous)."""
    try:
        bucket_name, object_key = _parse_s3_url(s3_url)
        s3_client = _get_s3_client()
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        return response["Body"].read()
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "NoSuchKey":
            raise ValueError(f"Video not found in S3: {s3_url}")
        elif error_code == "NoSuchBucket":
            raise ValueError(f"S3 bucket not found: {bucket_name}")
        else:
            raise ValueError(f"Error downloading video from S3: {e}")
    except Exception as e:
        raise ValueError(f"Error downloading video from S3: {e}")


async def _get_video_from_aws_s3(s3_url: str) -> bytes:
    """Async wrapper for downloading video from AWS S3."""
    return await asyncio.to_thread(_get_video_from_aws_s3_sync, s3_url)


def _list_s3_folder_contents_sync(s3_folder_url: str) -> List[Dict[str, Any]]:
    """List all media files in an S3 folder (synchronous)."""
    try:
        bucket_name, prefix = _parse_s3_url(s3_folder_url)

        if not prefix.endswith("/"):
            prefix += "/"

        s3_client = _get_s3_client()
        response = s3_client.list_objects_v2(
            Bucket=bucket_name, Prefix=prefix, Delimiter="/"
        )

        media_files = []
        region_name = config.AWS_S3_REGION or config.AWS_REGION

        for obj in response.get("Contents", []):
            key = obj["Key"]
            if key == prefix:
                continue

            file_extension = os.path.splitext(key)[1].lower()
            image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]
            video_extensions = [".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mkv"]

            mime_type = None
            if file_extension in image_extensions:
                mime_type = f"image/{file_extension[1:]}"
                if file_extension == ".jpg":
                    mime_type = "image/jpeg"
            elif file_extension in video_extensions:
                mime_type = f"video/{file_extension[1:]}"
                if file_extension == ".mov":
                    mime_type = "video/quicktime"

            if mime_type:
                file_url = f"https://{bucket_name}.s3.{region_name}.amazonaws.com/{key}"
                media_files.append(
                    {
                        "id": key,
                        "name": os.path.basename(key),
                        "mimeType": mime_type,
                        "size": obj["Size"],
                        "s3_url": file_url,
                        "source": "s3",
                        "key": key,
                        "bucket": bucket_name,
                    }
                )

        return media_files
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "NoSuchBucket":
            raise ValueError(f"S3 bucket not found: {bucket_name}")
        else:
            raise ValueError(f"Error listing S3 folder: {e}")
    except Exception as e:
        raise ValueError(f"Error listing S3 folder: {e}")


async def _list_s3_folder_contents(s3_folder_url: str) -> List[Dict[str, Any]]:
    """Async wrapper for listing all media files in an S3 folder."""
    return await asyncio.to_thread(_list_s3_folder_contents_sync, s3_folder_url)


def _extract_video_thumbnail_sync(video_data: bytes, frame_time: float = 1.0) -> bytes:
    """Extract thumbnail from video data (synchronous)."""
    if not VIDEO_PROCESSING_AVAILABLE:
        raise ImportError(
            "opencv-python not installed. Install with: pip install opencv-python"
        )

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_video:
        temp_video.write(video_data)
        temp_video_path = temp_video.name

    try:
        cap = cv2.VideoCapture(temp_video_path)
        if not cap.isOpened():
            raise ValueError("Could not open video file")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_number = min(int(frame_time * fps), total_frames - 1)

        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            raise ValueError("Could not read frame from video")

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=85, optimize=True)
        return output.getvalue()
    finally:
        try:
            os.unlink(temp_video_path)
        except Exception:
            pass


async def _extract_video_thumbnail(video_data: bytes, frame_time: float = 1.0) -> bytes:
    """Extract a thumbnail from video data."""
    return await asyncio.to_thread(
        _extract_video_thumbnail_sync, video_data, frame_time
    )


async def _upload_image_to_facebook(
    access_token: str, act_id: str, image_data: bytes, image_name: str
) -> Dict[str, Any]:
    """Upload image to Facebook Ad Images API."""
    try:
        import httpx
    except ImportError:
        raise ImportError("httpx not installed. Install with: pip install httpx")

    url = f"{FB_GRAPH_URL}/{act_id}/adimages"
    files = {"filename": (image_name, image_data, "image/jpeg")}
    data = {"access_token": access_token}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, files=files, data=data, timeout=30)

    response.raise_for_status()

    return response.json()


async def _upload_video_to_facebook(
    access_token: str, act_id: str, video_data: bytes, video_name: str
) -> Dict[str, Any]:
    """Upload video to Facebook Ad Videos API."""
    try:
        import httpx
    except ImportError:
        raise ImportError("httpx not installed. Install with: pip install httpx")

    url = f"{FB_GRAPH_URL}/{act_id}/advideos"
    files = {"source": (video_name, io.BytesIO(video_data), "video/mp4")}
    data = {"access_token": access_token}

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, data=data, files=files, timeout=300)

    resp.raise_for_status()

    out = resp.json()

    if "id" not in out:
        raise RuntimeError(f"Upload response missing id: {json.dumps(out)}")

    return out


async def _create_single_image_creative(
    access_token: str,
    act_id: str,
    page_id: str,
    ig_id: Optional[str],
    image_item: Dict[str, Any],
    message: str,
    headline: str,
    caption: str,
    call_to_action: str,
    link_url: str,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a single image ad creative."""
    link_data = {
        "message": message,
        "name": headline,
        "call_to_action": {"type": call_to_action, "value": {"link": link_url}},
        "link": link_url,
        "image_hash": image_item["hash"],
    }

    # Only add caption if it's provided and not empty
    if caption:
        link_data["caption"] = caption

    # Add description if provided (may not work on all placements)
    if description:
        link_data["description"] = description

    object_story_spec = {
        "page_id": page_id,
        "link_data": link_data,
    }
    if ig_id:
        object_story_spec["instagram_user_id"] = ig_id

    creative_params = {
        "access_token": access_token,
        "name": f"{image_item['name']} - Single Image Creative",
        "object_story_spec": json.dumps(object_story_spec),
    }
    creative_url = f"{FB_GRAPH_URL}/{act_id}/adcreatives"
    return await make_graph_api_post(creative_url, creative_params)


async def _create_carousel_creative(
    access_token: str,
    act_id: str,
    page_id: str,
    ig_id: Optional[str],
    media_items: List[Dict[str, Any]],
    message: str,
    headline: str,
    caption: str,
    call_to_action: str,
    link_url: str,
    folder_name: str,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a carousel ad creative."""
    child_attachments = []
    for media_item in media_items:
        if media_item["type"] == "image":
            child_attachment = {
                "image_hash": media_item["hash"],
                "link": link_url,
                "name": headline,
            }
            # Only add caption if provided
            if caption:
                child_attachment["caption"] = caption
            # Add description if provided
            if description:
                child_attachment["description"] = description
            child_attachments.append(child_attachment)

    link_data = {
        "message": message,
        "link": link_url,
        "child_attachments": child_attachments,
        "call_to_action": {"type": call_to_action, "value": {"link": link_url}},
    }

    object_story_spec = {
        "page_id": page_id,
        "link_data": link_data,
    }
    if ig_id:
        object_story_spec["instagram_user_id"] = ig_id

    creative_params = {
        "access_token": access_token,
        "name": f"{folder_name} - Carousel Creative",
        "object_story_spec": json.dumps(object_story_spec),
    }
    creative_url = f"{FB_GRAPH_URL}/{act_id}/adcreatives"
    return await make_graph_api_post(creative_url, creative_params)


async def _create_video_creative(
    access_token: str,
    act_id: str,
    page_id: str,
    ig_id: Optional[str],
    video_info: Dict[str, Any],
    message: str,
    headline: str,
    caption: str,
    call_to_action: str,
    link_url: str,
    thumbnail_hash: Optional[str],
) -> Dict[str, Any]:
    """Create a video creative."""
    if not thumbnail_hash:
        return {"error": "Thumbnail is required for video ads."}

    video_data = {
        "message": message,
        "title": headline,
        "call_to_action": {"type": call_to_action, "value": {"link": link_url}},
        "video_id": video_info["id"],
        "image_hash": thumbnail_hash,
    }
    object_story_spec = {"page_id": page_id, "video_data": video_data}
    if caption:
        object_story_spec["video_data"]["caption"] = caption
    if ig_id:
        object_story_spec["instagram_user_id"] = ig_id

    creative_params = {
        "access_token": access_token,
        "name": f"{headline} - Video Creative",
        "object_story_spec": json.dumps(object_story_spec),
    }
    creative_url = f"{FB_GRAPH_URL}/{act_id}/adcreatives"
    return await make_graph_api_post(creative_url, creative_params)


def register_tools(mcp: FastMCP):
    @mcp.tool()
    async def create_ad_with_media_creative_from_s3_folder_link(
        act_id: str,
        name: str,
        adset_id: str,
        s3_folder_url: str,
        message: str,
        headline: str,
        page_id: str,
        link_url: str = "",
        caption: str = "",
        description: str = "",
        call_to_action: str = "LEARN_MORE",
        status: str = "PAUSED",
        instagram_user_id: Optional[str] = None,
        tracking_specs: Optional[List[Dict[str, Any]]] = None,
        max_files: int = 20,
    ) -> str:
        """Create ads from all media files in an S3 folder.

        Downloads all media files (images and videos) from an S3 folder and creates
        appropriate Facebook/Instagram ads based on the content:
        - Single image: Creates one single image ad
        - Multiple images (no videos): Creates one carousel ad with all images
        - Multiple videos (no images): Creates individual video ads
        - Mixed content: Creates carousel for images + individual video ads

        Args:
            act_id (str): The Facebook Ads Ad Account ID (format: act_XXXXXXXXXX)
            name (str): Name for the ad(s).
            adset_id (str): ID of the ad set that will contain the ad(s).
            s3_folder_url (str): S3 URL pointing to the folder containing media files
                (e.g., "https://my-bucket.s3.us-east-1.amazonaws.com/campaign-assets/" or
                "s3://my-bucket/campaign-assets/").
            message (str): Primary ad text/body that appears above the creative.
            headline (str): Ad headline text (recommended max 40 chars for Instagram, 60 for Facebook).
            page_id (str): Facebook Page ID for the ad.
            link_url (str): Destination URL for the ad.
            caption (str): Optional SHORT link caption (e.g., "example.com"). If empty, domain
                will be auto-extracted from link_url. If provided and too long (>30 chars),
                will be replaced with auto-extracted domain.
            description (str): Optional longer description text. May not display on all placements.
                For primary ad text, use the 'message' parameter instead.
            call_to_action (str): CTA button type (default "LEARN_MORE").
            status (str): Initial delivery status (default "PAUSED").
            instagram_user_id (str): Optional Instagram account ID for Instagram placement.
            tracking_specs (List[Dict]): Optional custom tracking specifications.
            max_files (int): Maximum number of files to process (default 20).

        Returns:
            str: JSON string with created ad IDs and summary, or error details.

        Note:
            Requires AWS credentials (validated at application startup):
            - AWS_ACCESS_KEY_ID (required)
            - AWS_SECRET_ACCESS_KEY (required)
            - AWS_REGION (optional, defaults to us-west-2)
            - AWS_S3_REGION (deprecated, use AWS_REGION instead)
        """
        if not S3_AVAILABLE:
            return json.dumps(
                {"error": "S3 support not available. Install with: pip install boto3"},
                indent=2,
            )

        access_token = config.META_ACCESS_TOKEN

        missing = [
            field
            for field, val in {
                "act_id": act_id,
                "name": name,
                "adset_id": adset_id,
                "s3_folder_url": s3_folder_url,
                "message": message,
                "headline": headline,
                "page_id": page_id,
            }.items()
            if not val
        ]
        if missing:
            return json.dumps(
                {"error": f"Missing required fields: {', '.join(missing)}"}, indent=2
            )

        # Validate and fix caption parameter
        original_caption = caption
        warnings = []

        # Auto-extract domain from link_url if caption is empty or too long
        if not caption or len(caption) > 30:
            auto_caption = _extract_domain_from_url(link_url)
            if len(caption) > 30:
                warnings.append(
                    f"Caption too long ({len(caption)} chars): '{caption[:50]}...'. "
                    f"Using auto-extracted domain '{auto_caption}' instead. "
                    f"Caption should be a short link caption (e.g., 'example.com'), not a description. "
                    f"Use the 'description' parameter for longer text."
                )
            caption = auto_caption

        # Validate parameters and collect warnings
        param_warnings = _validate_ad_creative_params(
            headline, caption, instagram_user_id
        )
        warnings.extend(param_warnings)

        try:
            media_files = await _list_s3_folder_contents(s3_folder_url)
            if not media_files:
                return json.dumps(
                    {"error": "No media files found in S3 folder"}, indent=2
                )

            media_files = media_files[:max_files]
            carousel_items = []
            processing_errors = []

            for file_info in media_files:
                file_name = file_info.get("name", "Unknown")
                mime_type = file_info.get("mimeType", "")
                s3_url = file_info.get("s3_url")

                try:
                    if mime_type.startswith("image/"):
                        image_data = await _get_image_from_aws_s3(s3_url)
                        try:
                            base_name = os.path.splitext(file_name)[0]
                            fb_file_name = f"{base_name}.jpg"
                            upload_res = await _upload_image_to_facebook(
                                access_token, act_id, image_data, fb_file_name
                            )
                            if "images" not in upload_res:
                                error_details = upload_res.get("error", {})
                                error_message = error_details.get(
                                    "message", "Unknown error"
                                )
                                processing_errors.append(
                                    f"Failed to upload image {file_name}: {error_message}"
                                )
                                continue
                            img_hash = next(iter(upload_res["images"].values()))["hash"]
                            carousel_items.append(
                                {
                                    "type": "image",
                                    "hash": img_hash,
                                    "name": file_name,
                                    "id": file_info["id"],
                                }
                            )
                        except Exception as upload_error:
                            processing_errors.append(
                                f"Error uploading image {file_name}: {upload_error}"
                            )
                            continue

                    elif mime_type.startswith("video/"):
                        video_data = await _get_video_from_aws_s3(s3_url)
                        try:
                            thumb = await _extract_video_thumbnail(video_data)
                            thumb_res = await _upload_image_to_facebook(
                                access_token,
                                act_id,
                                thumb,
                                f"thumb_{file_name}.jpg",
                            )
                            if "images" not in thumb_res:
                                processing_errors.append(
                                    f"Thumbnail upload error for {file_name}"
                                )
                                continue
                            thumb_hash = next(iter(thumb_res["images"].values()))[
                                "hash"
                            ]
                        except Exception as e:
                            processing_errors.append(
                                f"Thumbnail error for {file_name}: {e}"
                            )
                            continue

                        vid_res = await _upload_video_to_facebook(
                            access_token, act_id, video_data, file_name
                        )
                        vid_id = vid_res.get("id")
                        if not vid_id:
                            processing_errors.append(f"No video ID for {file_name}")
                            continue
                        carousel_items.append(
                            {
                                "type": "video",
                                "id": vid_id,
                                "name": file_name,
                                "thumbnail_hash": thumb_hash,
                            }
                        )
                    else:
                        processing_errors.append(
                            f"Unsupported mimeType {mime_type} for {file_name}"
                        )
                except Exception as e:
                    processing_errors.append(f"Error processing {file_name}: {e}")

            if not carousel_items:
                return json.dumps(
                    {
                        "error": "No media processed",
                        "processing_errors": processing_errors,
                    },
                    indent=2,
                )

            imgs = [i for i in carousel_items if i["type"] == "image"]
            vids = [i for i in carousel_items if i["type"] == "video"]
            created = []

            # Determine creative type
            if len(imgs) == 1 and len(vids) == 0:
                creative_type = "single_image"
            elif len(imgs) > 1 and len(vids) == 0:
                creative_type = "carousel"
            elif len(imgs) == 0 and len(vids) > 1:
                creative_type = "video_carousel"
            elif len(imgs) > 0 and len(vids) > 0:
                creative_type = "mixed"
            else:
                creative_type = "single_video"

            # Handle images
            if imgs:
                if creative_type == "single_image":
                    img = imgs[0]
                    single_img_creative = await _create_single_image_creative(
                        access_token,
                        act_id,
                        page_id,
                        instagram_user_id,
                        img,
                        message,
                        headline,
                        caption,
                        call_to_action,
                        link_url,
                        description,
                    )
                    if "error" not in single_img_creative:
                        adp = {
                            "access_token": access_token,
                            "name": f"{name}",
                            "adset_id": adset_id,
                            "status": status,
                            "creative": json.dumps(
                                {"creative_id": single_img_creative["id"]}
                            ),
                        }
                        if tracking_specs:
                            adp["tracking_specs"] = json.dumps(tracking_specs)
                        resp = await make_graph_api_post(
                            f"{FB_GRAPH_URL}/{act_id}/ads", adp
                        )
                        if "id" in resp:
                            resp.update(
                                {
                                    "creative_type": "single_image",
                                    "media_type": "image",
                                    "image_name": img["name"],
                                }
                            )
                            created.append(resp)
                        else:
                            processing_errors.append(
                                f"No ad ID for single image: {resp}"
                            )
                    else:
                        processing_errors.append(
                            f"Single image creative error: {single_img_creative.get('error')}"
                        )

                elif creative_type in ["carousel", "mixed"]:
                    carr = await _create_carousel_creative(
                        access_token,
                        act_id,
                        page_id,
                        instagram_user_id,
                        imgs,
                        message,
                        headline,
                        caption,
                        call_to_action,
                        link_url,
                        name,
                        description,
                    )
                    if "error" not in carr:
                        adp = {
                            "access_token": access_token,
                            "name": f"{name}",
                            "adset_id": adset_id,
                            "status": status,
                            "creative": json.dumps({"creative_id": carr["id"]}),
                        }
                        if tracking_specs:
                            adp["tracking_specs"] = json.dumps(tracking_specs)
                        resp = await make_graph_api_post(
                            f"{FB_GRAPH_URL}/{act_id}/ads", adp
                        )
                        if "id" in resp:
                            resp.update(
                                {
                                    "creative_type": "carousel",
                                    "media_count": len(imgs),
                                    "media_type": "images",
                                }
                            )
                            created.append(resp)
                        else:
                            processing_errors.append(f"No ad ID for carousel: {resp}")
                    else:
                        processing_errors.append(
                            f"Carousel creative error: {carr.get('error')}"
                        )

            # Handle videos
            if vids:
                for v in vids:
                    vc = await _create_video_creative(
                        access_token,
                        act_id,
                        page_id,
                        instagram_user_id,
                        {"id": v["id"]},
                        message,
                        headline,
                        caption,
                        call_to_action,
                        link_url,
                        v["thumbnail_hash"],
                    )
                    if "error" in vc:
                        processing_errors.append(
                            f"Video creative error {v['name']}: {vc['error']}"
                        )
                        continue
                    adp = {
                        "access_token": access_token,
                        "name": f"{name} - {v['name']}",
                        "adset_id": adset_id,
                        "status": status,
                        "creative": json.dumps({"creative_id": vc["id"]}),
                    }
                    if tracking_specs:
                        adp["tracking_specs"] = json.dumps(tracking_specs)
                    resp = await make_graph_api_post(
                        f"{FB_GRAPH_URL}/{act_id}/ads", adp
                    )
                    if "id" in resp:
                        resp.update(
                            {
                                "creative_type": "video",
                                "media_type": "video",
                                "video_name": v["name"],
                            }
                        )
                        created.append(resp)
                    else:
                        processing_errors.append(
                            f"No ad ID for video {v['name']}: {resp}"
                        )

            result = {
                "s3_folder_url": s3_folder_url,
                "total_files": len(media_files),
                "processed_files": len(carousel_items),
                "ads_created": len(created),
                "created_ads": created,
                "images": len(imgs),
                "videos": len(vids),
                "creative_type": creative_type,
            }
            if warnings:
                result["warnings"] = warnings
            if processing_errors:
                result["errors"] = processing_errors
            if not created:
                result["error"] = "No ads created"
            return json.dumps(result, indent=2)

        except Exception as exc:
            return json.dumps(
                {
                    "error": f"Failed to create ads from S3 folder: {exc}",
                    "details": str(exc),
                    "s3_folder_url": s3_folder_url,
                },
                indent=2,
            )
