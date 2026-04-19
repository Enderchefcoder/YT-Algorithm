"""
YouTube search via yt-dlp.

Returns lightweight result dicts (metadata only, no stream URL).
Stream URLs are only fetched when a user actually clicks a video.
"""

from __future__ import annotations

from typing import List, Dict, Any

import yt_dlp


def search_videos(query: str, max_results: int = 8) -> List[Dict[str, Any]]:
    """
    Search YouTube for `query` and return up to `max_results` video cards.

    Uses yt-dlp's ytsearch extractor so no API key is needed.
    """
    search_query = f"ytsearch{max_results}:{query}"

    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,       # Don't fetch stream URLs — just metadata
        "noplaylist": False,
        "skip_download": True,
    }

    results: List[Dict[str, Any]] = []

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            entries = info.get("entries") or []
            for entry in entries:
                if not entry:
                    continue
                tags = entry.get("tags") or []
                results.append({
                    "id": entry.get("id", ""),
                    "title": entry.get("title", "Unknown"),
                    "uploader": entry.get("uploader", "Unknown"),
                    "duration": entry.get("duration") or 0,
                    "view_count": entry.get("view_count") or 0,
                    "thumbnail": _pick_thumbnail(entry),
                    "hashtags": [t.lower().lstrip("#") for t in tags],
                    "hashtags_pipe": "|".join(
                        t.lower().lstrip("#") for t in tags
                    ),
                    "description": (entry.get("description") or "")[:200],
                })
    except Exception:
        pass  # Return whatever we have so far

    return results


def _pick_thumbnail(entry: Dict[str, Any]) -> str:
    thumbs = entry.get("thumbnails") or []
    for t in reversed(thumbs):
        url = t.get("url", "")
        if url:
            return url
    # Fallback to standard YouTube thumbnail URL
    vid_id = entry.get("id", "")
    if vid_id:
        return f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"
    return ""
