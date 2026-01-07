"""Query Apple Podcasts SQLite database for episode metadata."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

from thefuzz import fuzz, process


# Core Data reference date: January 1, 2001 00:00:00 UTC
CORE_DATA_EPOCH = datetime(2001, 1, 1, 0, 0, 0)


@dataclass
class Episode:
    """Podcast episode metadata from Apple Podcasts database."""

    uuid: str
    title: str
    podcast_channel: str
    podcast_author: str
    duration: int  # seconds
    publish_date: datetime
    last_played: Optional[datetime]
    transcript_identifier: Optional[str]
    transcript_provider: Optional[str]
    asset_url: Optional[str]
    store_track_id: Optional[int] = None  # Apple Store episode ID
    podcast_store_id: Optional[int] = None  # Apple Store podcast ID
    guid: Optional[str] = None  # Episode GUID

    @property
    def duration_formatted(self) -> str:
        """Format duration as HH:MM:SS or MM:SS."""
        hours = self.duration // 3600
        minutes = (self.duration % 3600) // 60
        seconds = self.duration % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"


def core_data_timestamp_to_datetime(timestamp: Optional[float]) -> Optional[datetime]:
    """
    Convert Core Data timestamp to Python datetime.

    Core Data timestamps are seconds since January 1, 2001 00:00:00 UTC.

    Args:
        timestamp: Core Data timestamp (seconds since 2001-01-01)

    Returns:
        Python datetime object, or None if timestamp is None
    """
    if timestamp is None or timestamp == 0:
        return None

    return CORE_DATA_EPOCH + timedelta(seconds=timestamp)


def datetime_to_core_data_timestamp(dt: datetime) -> float:
    """
    Convert Python datetime to Core Data timestamp.

    Args:
        dt: Python datetime object

    Returns:
        Core Data timestamp (seconds since 2001-01-01)
    """
    delta = dt - CORE_DATA_EPOCH
    return delta.total_seconds()


class PodcastDatabase:
    """Interface to Apple Podcasts SQLite database."""

    def __init__(self, db_path: Path):
        """
        Initialize database connection.

        Args:
            db_path: Path to MTLibrary.sqlite database

        Raises:
            FileNotFoundError: If database doesn't exist
            sqlite3.Error: If database cannot be opened
        """
        if not db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")

        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def connect(self) -> None:
        """Open database connection (read-only)."""
        if self._conn is None:
            # Open in read-only mode with URI
            uri = f"file:{self.db_path}?mode=ro"
            self._conn = sqlite3.connect(uri, uri=True)
            self._conn.row_factory = sqlite3.Row

    def close(self) -> None:
        """Close database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def get_all_podcast_channels(self) -> List[Tuple[str, str]]:
        """
        Get list of all podcast channels in the database.

        Returns:
            List of (channel_name, author) tuples
        """
        if self._conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        query = """
            SELECT ZTITLE, ZAUTHOR
            FROM ZMTPODCAST
            WHERE ZTITLE IS NOT NULL
            ORDER BY ZTITLE
        """

        cursor = self._conn.execute(query)
        return [(row["ZTITLE"], row["ZAUTHOR"] or "") for row in cursor.fetchall()]

    def fuzzy_match_channel(
        self, query: str, threshold: int = 60
    ) -> List[Tuple[str, int]]:
        """
        Fuzzy match a channel name against available channels.

        Args:
            query: Channel name to search for
            threshold: Minimum match score (0-100), default 60

        Returns:
            List of (channel_name, score) tuples, sorted by score descending
        """
        channels = [name for name, _ in self.get_all_podcast_channels()]
        matches = process.extract(query, channels, scorer=fuzz.token_sort_ratio)

        # Filter by threshold and return
        # process.extract returns (match, score) tuples
        return [(match, score) for match, score in matches if score >= threshold]

    def get_episodes_by_date(
        self,
        days: int = 7,
        channel_filter: Optional[str] = None,
    ) -> List[Episode]:
        """
        Get episodes played within the last N days.

        Args:
            days: Number of days to look back (default: 7)
            channel_filter: Optional channel name for fuzzy matching

        Returns:
            List of Episode objects sorted by last played date (most recent first)

        Raises:
            ValueError: If channel_filter doesn't match any channels
        """
        if self._conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        # Calculate cutoff timestamp
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_timestamp = datetime_to_core_data_timestamp(cutoff_date)

        # Build query
        query = """
            SELECT
                e.ZUUID,
                e.ZTITLE,
                p.ZTITLE as podcast_channel,
                p.ZAUTHOR as podcast_author,
                e.ZDURATION,
                e.ZPUBDATE,
                e.ZLASTDATEPLAYED,
                e.ZENTITLEDTRANSCRIPTIDENTIFIER,
                e.ZENTITLEDTRANSCRIPTPROVIDER,
                e.ZFREETRANSCRIPTIDENTIFIER,
                e.ZFREETRANSCRIPTPROVIDER,
                e.ZASSETURL,
                e.ZSTORETRACKID,
                e.ZGUID,
                p.ZSTORECOLLECTIONID as podcast_store_id
            FROM ZMTEPISODE e
            JOIN ZMTPODCAST p ON e.ZPODCAST = p.Z_PK
            WHERE e.ZLASTDATEPLAYED > ?
        """

        params = [cutoff_timestamp]

        # Add channel filter if specified
        if channel_filter:
            matches = self.fuzzy_match_channel(channel_filter, threshold=60)
            if not matches:
                raise ValueError(
                    f"No channels found matching '{channel_filter}'. "
                    f"Try a different search term."
                )

            # Use the best match
            best_match, score = matches[0]
            if score < 80:
                # Warn if match quality is low
                print(
                    f"Warning: Low confidence match for '{channel_filter}' -> '{best_match}' "
                    f"(score: {score}/100)"
                )

            query += " AND p.ZTITLE = ?"
            params.append(best_match)

        query += " ORDER BY e.ZLASTDATEPLAYED DESC"

        cursor = self._conn.execute(query, params)
        episodes = []

        for row in cursor.fetchall():
            # Prefer entitled transcript, fall back to free transcript
            transcript_id = row["ZENTITLEDTRANSCRIPTIDENTIFIER"] or row[
                "ZFREETRANSCRIPTIDENTIFIER"
            ]
            transcript_provider = row["ZENTITLEDTRANSCRIPTPROVIDER"] or row[
                "ZFREETRANSCRIPTPROVIDER"
            ]

            episode = Episode(
                uuid=row["ZUUID"],
                title=row["ZTITLE"] or "Untitled Episode",
                podcast_channel=row["podcast_channel"] or "Unknown Podcast",
                podcast_author=row["podcast_author"] or "",
                duration=int(row["ZDURATION"] or 0),
                publish_date=core_data_timestamp_to_datetime(row["ZPUBDATE"]),
                last_played=core_data_timestamp_to_datetime(row["ZLASTDATEPLAYED"]),
                transcript_identifier=transcript_id,
                transcript_provider=transcript_provider,
                asset_url=row["ZASSETURL"],
                store_track_id=row["ZSTORETRACKID"],
                podcast_store_id=row["podcast_store_id"],
                guid=row["ZGUID"],
            )
            episodes.append(episode)

        return episodes

    def get_episode_by_uuid(self, uuid: str) -> Optional[Episode]:
        """
        Get a single episode by its UUID.

        Args:
            uuid: Episode UUID

        Returns:
            Episode object, or None if not found
        """
        episodes = self.get_episodes_by_date(days=9999)  # Get all episodes
        for episode in episodes:
            if episode.uuid == uuid:
                return episode
        return None

    def get_database_stats(self) -> dict:
        """
        Get statistics about the podcast database.

        Returns:
            Dictionary with stats (total episodes, total podcasts, episodes with transcripts)
        """
        if self._conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        stats = {}

        # Total episodes
        cursor = self._conn.execute("SELECT COUNT(*) as count FROM ZMTEPISODE")
        stats["total_episodes"] = cursor.fetchone()["count"]

        # Total podcasts
        cursor = self._conn.execute("SELECT COUNT(*) as count FROM ZMTPODCAST")
        stats["total_podcasts"] = cursor.fetchone()["count"]

        # Episodes with transcripts
        cursor = self._conn.execute(
            """
            SELECT COUNT(*) as count FROM ZMTEPISODE
            WHERE ZENTITLEDTRANSCRIPTIDENTIFIER IS NOT NULL
               OR ZFREETRANSCRIPTIDENTIFIER IS NOT NULL
        """
        )
        stats["episodes_with_transcripts"] = cursor.fetchone()["count"]

        # Recently played (last 30 days)
        cutoff = datetime_to_core_data_timestamp(datetime.now() - timedelta(days=30))
        cursor = self._conn.execute(
            "SELECT COUNT(*) as count FROM ZMTEPISODE WHERE ZLASTDATEPLAYED > ?",
            [cutoff],
        )
        stats["recently_played_30d"] = cursor.fetchone()["count"]

        return stats
