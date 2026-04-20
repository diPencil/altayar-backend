"""
Utility functions for Reels module
"""
import logging
import os
import re
import subprocess
import tempfile
from typing import Optional, Tuple
from urllib.parse import urlparse

from PIL import Image

try:
    from imageio_ffmpeg import get_ffmpeg_exe
except Exception:  # pragma: no cover - optional during install/bootstrap
    get_ffmpeg_exe = None


logger = logging.getLogger(__name__)


def validate_video_url(url: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate video URL and determine video type.
    
    Returns:
        (is_valid, video_type, error_message)
        video_type: 'YOUTUBE', 'DIRECT', or None if invalid
    """
    if not url or not isinstance(url, str):
        return False, None, "URL is required"
    
    url = url.strip()
    
    # Check for YouTube URLs
    youtube_patterns = [
        r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in youtube_patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            return True, 'YOUTUBE', None
    
    # Check for direct video URLs (MP4, MOV, etc.)
    parsed = urlparse(url)
    
    # Must be http or https
    if parsed.scheme not in ['http', 'https']:
        return False, None, "URL must use http or https protocol"
    
    # Check file extension
    path = parsed.path.lower()
    video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.3gp']
    
    if any(path.endswith(ext) for ext in video_extensions):
        return True, 'URL', None  # Changed from 'DIRECT' to 'URL' to match frontend expectations
    
    # Allow URLs without extension if they're direct links (could be CDN URLs)
    # This is more permissive but allows for various hosting platforms
    if parsed.netloc and parsed.path:
        return True, 'URL', None  # Changed from 'DIRECT' to 'URL'
    
    return False, None, "Invalid video URL. Must be YouTube link or direct video file (MP4, MOV, etc.)"


def extract_youtube_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL."""
    patterns = [
        r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


def get_youtube_thumbnail_url(video_url: str) -> Optional[str]:
    """
    Generate YouTube thumbnail URL from video URL.
    YouTube provides thumbnails at: https://img.youtube.com/vi/{VIDEO_ID}/maxresdefault.jpg
    """
    video_id = extract_youtube_video_id(video_url)
    if video_id:
        return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    return None


def generate_video_thumbnail(video_source: str, output_path: str, seek_seconds: float = 0.5) -> bool:
    """Extract a thumbnail from the first visible frame of a video."""
    if not video_source:
        return False

    if not get_ffmpeg_exe:
        logger.warning("imageio-ffmpeg is not available; skipping thumbnail generation")
        return False

    ffmpeg_exe = get_ffmpeg_exe()
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    temp_output = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
            temp_output = temp_file.name

        command = [
            ffmpeg_exe,
            "-y",
            "-ss",
            str(seek_seconds),
            "-i",
            video_source,
            "-frames:v",
            "1",
            "-q:v",
            "2",
            temp_output,
        ]

        result = subprocess.run(command, capture_output=True, text=True, timeout=90)
        if result.returncode != 0 or not os.path.exists(temp_output):
            logger.warning("Failed to extract video thumbnail: %s", result.stderr.strip() if result.stderr else "unknown error")
            return False

        with Image.open(temp_output) as image:
            rgb_image = image.convert("RGB")
            rgb_image.thumbnail((1280, 1280))
            rgb_image.save(output_path, format="JPEG", quality=88, optimize=True)

        return os.path.exists(output_path)

    except Exception as exc:
        logger.warning("Thumbnail generation failed for %s: %s", video_source, exc)
        return False
    finally:
        if temp_output and os.path.exists(temp_output):
            try:
                os.remove(temp_output)
            except OSError:
                pass
