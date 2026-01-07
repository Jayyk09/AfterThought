"""Automate podcast playback to trigger transcript downloads."""

import subprocess
import time
from typing import Optional

from afterthought.db.podcast_db import Episode


class PodcastPlayerAutomation:
    """Automate Apple Podcasts app to trigger transcript downloads."""

    def __init__(self, wait_time: int = 10):
        """
        Initialize podcast player automation.

        Args:
            wait_time: Seconds to wait after triggering playback (default: 10)
        """
        self.wait_time = wait_time

    def trigger_transcript_download(self, episode: Episode) -> bool:
        """
        Trigger podcast playback to download transcript.

        This opens the episode in Apple Podcasts and briefly plays it to
        trigger transcript download from Apple's servers.

        Args:
            episode: Episode to trigger download for

        Returns:
            True if successful, False otherwise
        """
        # Extract episode ID from asset URL if available
        episode_id = self._extract_episode_id(episode)

        if not episode_id:
            print(f"    ⚠ Could not extract episode ID for: {episode.title}")
            return False

        print(f"    🎧 Triggering playback to fetch transcript...")

        # Build podcasts:// URL
        # Format: podcasts://podcasts.apple.com/us/podcast/NAME/idXXXXXX?i=EPISODE_ID
        podcast_url = self._build_podcast_url(episode, episode_id)

        # Execute AppleScript to open and play the episode
        success = self._run_applescript_playback(podcast_url)

        if success:
            print(f"    ⏳ Waiting {self.wait_time} seconds for transcript download...")
            time.sleep(self.wait_time)
            return True

        return False

    def _extract_episode_id(self, episode: Episode) -> Optional[str]:
        """
        Extract Apple episode ID from episode metadata.

        The episode ID is typically in the asset URL or can be derived from UUID.

        Args:
            episode: Episode metadata

        Returns:
            Episode ID string, or None if not found
        """
        # Try to extract from asset URL
        # Format: https://.../.../episode_XXXXXX.mp3 or similar
        if episode.asset_url:
            # Look for common patterns in asset URLs
            # Sometimes the ID is in the URL path
            asset_url = episode.asset_url

            # Try to find numeric ID in URL
            import re

            # Pattern 1: Look for /id followed by numbers
            match = re.search(r'/id(\d+)', asset_url)
            if match:
                return match.group(1)

            # Pattern 2: Look for i= parameter
            match = re.search(r'[?&]i=(\d+)', asset_url)
            if match:
                return match.group(1)

            # Pattern 3: Episode GUID might be usable
            # The UUID might be the episode ID in some cases
            if episode.uuid:
                # Try using UUID directly (Apple sometimes uses this)
                # Remove any non-numeric characters
                numeric_id = re.sub(r'\D', '', episode.uuid)
                if numeric_id:
                    return numeric_id

        # Fallback: use UUID as-is (might work for some episodes)
        return episode.uuid

    def _build_podcast_url(self, episode: Episode, episode_id: str) -> str:
        """
        Build podcasts:// URL for opening episode.

        Args:
            episode: Episode metadata
            episode_id: Episode ID

        Returns:
            podcasts:// URL string
        """
        # Sanitize podcast name for URL
        import urllib.parse
        podcast_name = urllib.parse.quote(episode.podcast_channel.replace(' ', '-').lower())

        # Build URL (we don't always have podcast ID, but episode ID is enough)
        # Format: podcasts://podcasts.apple.com/us/podcast/NAME?i=EPISODE_ID
        url = f"podcasts://podcasts.apple.com/us/podcast/{podcast_name}?i={episode_id}"

        return url

    def _run_applescript_playback(self, podcast_url: str) -> bool:
        """
        Run AppleScript to open and play podcast episode.

        This script:
        1. Activates Podcasts app
        2. Opens the episode URL
        3. Finds and clicks the Play button
        4. Plays for a few seconds to trigger transcript download

        Args:
            podcast_url: podcasts:// URL to open

        Returns:
            True if successful, False otherwise
        """
        applescript = f'''
        tell application "Podcasts" to activate
        open location "{podcast_url}"
        delay 4

        tell application "System Events"
            tell process "Podcasts"
                tell window 1
                    set allElements to entire contents
                    repeat with elem in allElements
                        try
                            set elemDesc to description of elem
                            if class of elem is button and (elemDesc contains "Replay" or (elemDesc starts with "Play" and elemDesc contains "minute")) then
                                click elem
                                delay 2
                                -- Stop playback after triggering
                                try
                                    key code 49 -- spacebar to pause
                                end try
                                exit repeat
                            end if
                        end try
                    end repeat
                end tell
            end tell
        end tell
        '''

        try:
            result = subprocess.run(
                ['osascript', '-e', applescript],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                print(f"    ⚠ AppleScript error: {result.stderr}")
                return False

            return True

        except subprocess.TimeoutExpired:
            print(f"    ⚠ AppleScript timed out")
            return False
        except Exception as e:
            print(f"    ⚠ Failed to run AppleScript: {e}")
            return False


def fetch_transcript_for_episode(
    episode: Episode,
    wait_time: int = 10
) -> bool:
    """
    Convenience function to fetch transcript for an episode.

    Args:
        episode: Episode to fetch transcript for
        wait_time: Seconds to wait after triggering playback

    Returns:
        True if fetch was triggered successfully, False otherwise
    """
    automation = PodcastPlayerAutomation(wait_time=wait_time)
    return automation.trigger_transcript_download(episode)
