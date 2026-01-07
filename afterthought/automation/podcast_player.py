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
        print(f"    📍 Episode Store ID: {episode_id}")
        if episode.podcast_store_id:
            print(f"    📍 Podcast Store ID: {episode.podcast_store_id}")

        # Build podcasts:// URL
        # Format: podcasts://podcasts.apple.com/us/podcast/NAME/idXXXXXX?i=EPISODE_ID
        podcast_url = self._build_podcast_url(episode, episode_id)
        print(f"    🔗 Opening: {podcast_url}")

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

        Uses ZSTORETRACKID from the database, which is the official Apple Store track ID.

        Args:
            episode: Episode metadata

        Returns:
            Episode ID string, or None if not found
        """
        # Use the store_track_id from the database (this is the correct Apple Store ID)
        if episode.store_track_id:
            return str(episode.store_track_id)

        # Fallback: try GUID if available
        if episode.guid:
            return episode.guid

        # Last resort: use UUID
        return episode.uuid

    def _build_podcast_url(self, episode: Episode, episode_id: str) -> str:
        """
        Build podcasts:// URL for opening episode.

        Format: podcasts://podcasts.apple.com/us/podcast/NAME/idPODCAST_ID?i=EPISODE_ID

        Args:
            episode: Episode metadata
            episode_id: Episode ID

        Returns:
            podcasts:// URL string
        """
        # Sanitize podcast name for URL
        import urllib.parse
        podcast_name = episode.podcast_channel.replace(' ', '-').lower()
        podcast_name = urllib.parse.quote(podcast_name)

        # Build URL with podcast store ID if available
        # Format: podcasts://podcasts.apple.com/us/podcast/the-history-of-rome/id261654474?i=EPISODE_ID
        if episode.podcast_store_id:
            url = f"podcasts://podcasts.apple.com/us/podcast/{podcast_name}/id{episode.podcast_store_id}?i={episode_id}"
        else:
            # Fallback without podcast ID (less reliable)
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
