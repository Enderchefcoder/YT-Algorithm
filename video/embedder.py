"""
Builds embed configurations for the video player.

We use the direct stream URL from yt-dlp rather than an iframe embed
so that we can intercept playback events (watch time, completion)
entirely client-side via our player.js.

The HTML5 <video> element is used with controls disabled — our custom
player UI sits on top of it.
"""

from __future__ import annotations

from typing import Dict, Any, Optional

from video.fetcher import get_video_info


def build_embed(video_id: str) -> Optional[Dict[str, Any]]:
    """
    Return everything the watch.html template needs to render the player.

    {
        "video_id": str,
        "title": str,
        "uploader": str,
        "duration": int,          # seconds
        "stream_url": str,        # direct mp4/m3u8 URL
        "thumbnail": str,
        "hashtags": [str, ...],
        "hashtags_pipe": str,     # for passing to the backend on watch end
        "description": str,
        "view_count": int,
        "like_count": int,
    }
    """
    info = get_video_info(video_id)
    if info is None:
        return None

    return {
        "video_id": info["id"],
        "title": info["title"],
        "uploader": info["uploader"],
        "duration": info["duration"],
        "stream_url": info["stream_url"],
        "thumbnail": info["thumbnail"],
        "hashtags": info["hashtags"],
        "hashtags_pipe": info["hashtags_pipe"],
        "description": info["description"],
        "view_count": info["view_count"],
        "like_count": info["like_count"],
    }
