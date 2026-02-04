"""
Utility functions for Reels module
"""
import re
from typing import Optional, Tuple
from urllib.parse import urlparse, parse_qs


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
