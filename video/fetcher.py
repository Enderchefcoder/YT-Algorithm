"""
yt-dlp wrapper for fetching video metadata and stream URLs.

We never download videos to disk.  Everything is streamed.
"""

from __future__ import annotations

import re
from typing import Dict, Any, Optional

import yt_dlp


# yt-dlp options that apply to all operations
_BASE_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "extract_flat": False,
    # Prefer a format that browsers can play natively without transcoding.
    # 720p or lower for performance; falls back gracefully.
    "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best",
    "noplaylist": True,
}


def get_video_info(video_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch full metadata + stream URL for a single video.

    Returns a normalised dict or None on error.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    opts = {**_BASE_OPTS, "extract_flat": False}

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return _normalise_info(info)
    except yt_dlp.utils.DownloadError:
        return None
    except Exception:
        return None


def _normalise_info(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Map yt-dlp's raw info dict to our internal schema."""
    # Extract hashtags from tags, description, and categories
    tags = raw.get("tags") or []
    categories = raw.get("categories") or []
    hashtags = list({t.lower().lstrip("#") for t in tags + categories if t})

    return {
        "id": raw.get("id", ""),
        "title": raw.get("title", "Unknown"),
        "description": (raw.get("description") or "")[:500],  # Trim long descriptions
        "uploader": raw.get("uploader", "Unknown"),
        "uploader_id": raw.get("uploader_id", ""),
        "duration": raw.get("duration") or 0,
        "view_count": raw.get("view_count") or 0,
        "like_count": raw.get("like_count") or 0,
        "thumbnail": _best_thumbnail(raw.get("thumbnails") or []),
        "hashtags": hashtags,
        "hashtags_pipe": "|".join(hashtags),
        "stream_url": raw.get("url") or _find_best_url(raw),
        "webpage_url": raw.get("webpage_url", ""),
        "upload_date": raw.get("upload_date", ""),
    }


def _best_thumbnail(thumbnails: list) -> str:
    """Pick the highest-resolution thumbnail available."""
    if not thumbnails:
        return ""
    # yt-dlp orders thumbnails; pick last (usually highest res)
    for thumb in reversed(thumbnails):
        url = thumb.get("url", "")
        if url:
            return url
    return ""


def _find_best_url(raw: Dict[str, Any]) -> str:
    """Fall back to scanning the formats list for a direct URL."""
    formats = raw.get("formats") or []
    for fmt in reversed(formats):
        url = fmt.get("url", "")
        if url and url.startswith("http"):
            return url
    return ""
