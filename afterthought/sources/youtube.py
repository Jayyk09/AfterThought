"""YouTube transcript fetching and parsing."""

import re
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from urllib.parse import parse_qs, urlparse

import requests

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        NoTranscriptFound,
        TranscriptsDisabled,
        VideoUnavailable,
    )
except ImportError:
    # Fallback for older versions
    from youtube_transcript_api import YouTubeTranscriptApi
    NoTranscriptFound = Exception
    TranscriptsDisabled = Exception
    VideoUnavailable = Exception


@dataclass
class YouTubeVideo:
    """YouTube video metadata for summarization."""

    video_id: str
    title: str
    channel: str
    url: str
    duration: int = 0
    publish_date: Optional[datetime] = None
    transcript: Optional[str] = None
    transcript_language: Optional[str] = None


class YouTubeClient:
    """Client for fetching YouTube transcripts."""

    def __init__(self, preserve_timestamps: bool = False):
        """
        Initialize YouTube client.

        Args:
            preserve_timestamps: Whether to include timestamps in transcript
        """
        self.preserve_timestamps = preserve_timestamps

    def fetch_video_metadata(self, video_id: str) -> dict:
        """
        Fetch video metadata (title, channel) from YouTube page.

        Args:
            video_id: YouTube video ID

        Returns:
            Dict with 'title' and 'channel' keys
        """
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            html = response.text

            # Try to extract from ytInitialPlayerResponse JSON
            match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});', html)
            if match:
                try:
                    data = json.loads(match.group(1))
                    title = data.get("videoDetails", {}).get("title", "")
                    channel = data.get("videoDetails", {}).get("author", "")
                    if title:
                        return {"title": title, "channel": channel}
                except (json.JSONDecodeError, KeyError):
                    pass

            # Fallback: extract from meta tags
            title_match = re.search(r'<meta name="title" content="([^"]+)"', html)
            if title_match:
                title = title_match.group(1)
                channel_match = re.search(r'<link itemprop="name" content="([^"]+)"', html)
                channel = channel_match.group(1) if channel_match else ""
                return {"title": title, "channel": channel}

            # Last resort: og:title
            og_title = re.search(r'<meta property="og:title" content="([^"]+)"', html)
            if og_title:
                return {"title": og_title.group(1), "channel": ""}

        except Exception:
            pass

        # Return empty if all methods fail
        return {"title": "", "channel": ""}

    def extract_video_id(self, url: str) -> Optional[str]:
        """
        Extract video ID from various YouTube URL formats.

        Supports:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/embed/VIDEO_ID
        - https://m.youtube.com/watch?v=VIDEO_ID

        Args:
            url: YouTube URL

        Returns:
            Video ID or None if not found
        """
        # Handle youtu.be short links
        if "youtu.be/" in url:
            match = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", url)
            if match:
                return match.group(1)

        # Handle youtube.com URLs
        parsed = urlparse(url)
        if parsed.hostname in ("www.youtube.com", "youtube.com", "m.youtube.com"):
            # Handle /watch?v=VIDEO_ID
            if parsed.path == "/watch":
                query_params = parse_qs(parsed.query)
                if "v" in query_params:
                    return query_params["v"][0]

            # Handle /embed/VIDEO_ID or /v/VIDEO_ID
            match = re.search(r"/(embed|v)/([a-zA-Z0-9_-]{11})", parsed.path)
            if match:
                return match.group(2)

        # Try direct video ID (11 characters)
        if re.match(r"^[a-zA-Z0-9_-]{11}$", url):
            return url

        return None

    def fetch_transcript(
        self,
        video_id: str,
        languages: Optional[list[str]] = None,
    ) -> tuple[str, str]:
        """
        Fetch transcript for a YouTube video.

        Args:
            video_id: YouTube video ID
            languages: Preferred languages (default: ['en'])

        Returns:
            Tuple of (transcript_text, language_code)

        Raises:
            NoTranscriptFound: No transcript available
            TranscriptsDisabled: Transcripts disabled for video
            VideoUnavailable: Video not accessible
        """
        if languages is None:
            languages = ["en"]

        try:
            # Create API instance
            api = YouTubeTranscriptApi()

            # Fetch transcript using the instance method
            fetched = api.fetch(video_id, languages=languages)

            # Get transcript entries from snippets
            transcript_entries = fetched.snippets

            # Format transcript
            if self.preserve_timestamps:
                lines = []
                for entry in transcript_entries:
                    timestamp = self._format_timestamp(entry.start)
                    text = entry.text
                    lines.append(f"[{timestamp}] {text}")
                transcript_text = "\n".join(lines)
            else:
                # Just concatenate text
                transcript_text = " ".join(entry.text for entry in transcript_entries)

            # Get language code from fetched transcript
            language_code = fetched.language_code

            return transcript_text, language_code

        except Exception as e:
            # Simplify error handling - all exceptions become ValueError
            raise ValueError(f"Failed to fetch transcript: {e}") from e

    def _format_timestamp(self, seconds: float) -> str:
        """
        Format timestamp in HH:MM:SS format.

        Args:
            seconds: Timestamp in seconds

        Returns:
            Formatted timestamp string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def get_video_info(
        self,
        url: str,
        fetch_transcript: bool = True,
    ) -> YouTubeVideo:
        """
        Get video information and transcript.

        Args:
            url: YouTube URL or video ID
            fetch_transcript: Whether to fetch transcript (default: True)

        Returns:
            YouTubeVideo object with metadata and transcript

        Raises:
            ValueError: If video ID cannot be extracted
            NoTranscriptFound: No transcript available
        """
        # Extract video ID
        video_id = self.extract_video_id(url)
        if not video_id:
            raise ValueError(f"Could not extract video ID from URL: {url}")

        # Construct standard URL
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        # Fetch metadata
        metadata = self.fetch_video_metadata(video_id)

        # Initialize video object
        video = YouTubeVideo(
            video_id=video_id,
            title=metadata.get("title", "") or video_id,  # Fallback to video_id
            channel=metadata.get("channel", ""),
            url=video_url,
        )

        # Fetch transcript if requested
        if fetch_transcript:
            transcript_text, language = self.fetch_transcript(video_id)
            video.transcript = transcript_text
            video.transcript_language = language

        return video


def fetch_youtube_transcript(url: str, preserve_timestamps: bool = False) -> YouTubeVideo:
    """
    Convenience function to fetch YouTube video transcript.

    Args:
        url: YouTube URL or video ID
        preserve_timestamps: Whether to include timestamps in transcript

    Returns:
        YouTubeVideo object with transcript

    Raises:
        ValueError: If video ID cannot be extracted or no transcript available
    """
    client = YouTubeClient(preserve_timestamps=preserve_timestamps)
    return client.get_video_info(url, fetch_transcript=True)
