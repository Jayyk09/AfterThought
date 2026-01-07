"""Tracking database for processed podcast episodes."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


class TrackingDatabase:
    """Database for tracking processed podcast episodes."""

    SCHEMA = """
        CREATE TABLE IF NOT EXISTS processed_episodes (
            episode_uuid TEXT PRIMARY KEY,
            episode_title TEXT NOT NULL,
            podcast_channel TEXT NOT NULL,
            processed_timestamp TEXT NOT NULL,
            output_file_path TEXT NOT NULL,
            gemini_tokens_used INTEGER,
            success BOOLEAN NOT NULL DEFAULT 1
        );

        CREATE INDEX IF NOT EXISTS idx_podcast_channel
        ON processed_episodes(podcast_channel);

        CREATE INDEX IF NOT EXISTS idx_processed_timestamp
        ON processed_episodes(processed_timestamp);

        CREATE INDEX IF NOT EXISTS idx_success
        ON processed_episodes(success);
    """

    def __init__(self, db_path: Path):
        """
        Initialize tracking database.

        Args:
            db_path: Path to tracking database file
        """
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

        # Ensure directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize schema on first use
        self._initialize_schema()

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def _initialize_schema(self) -> None:
        """Create database schema if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executescript(self.SCHEMA)
            conn.commit()
        finally:
            conn.close()

    def connect(self) -> None:
        """Open database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row

    def close(self) -> None:
        """Close database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def is_processed(self, episode_uuid: str) -> bool:
        """
        Check if an episode has been processed.

        Args:
            episode_uuid: Episode UUID from Apple Podcasts

        Returns:
            True if episode has been processed, False otherwise
        """
        if self._conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        cursor = self._conn.execute(
            "SELECT 1 FROM processed_episodes WHERE episode_uuid = ? AND success = 1",
            [episode_uuid],
        )
        return cursor.fetchone() is not None

    def mark_processed(
        self,
        episode_uuid: str,
        episode_title: str,
        podcast_channel: str,
        output_file_path: Path,
        gemini_tokens_used: int,
        success: bool = True,
    ) -> None:
        """
        Mark an episode as processed.

        Args:
            episode_uuid: Episode UUID from Apple Podcasts
            episode_title: Episode title
            podcast_channel: Podcast channel name
            output_file_path: Path to generated markdown file
            gemini_tokens_used: Total tokens used by Gemini API
            success: Whether processing was successful (default: True)
        """
        if self._conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        timestamp = datetime.now().isoformat()

        try:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO processed_episodes
                (episode_uuid, episode_title, podcast_channel, processed_timestamp,
                 output_file_path, gemini_tokens_used, success)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    episode_uuid,
                    episode_title,
                    podcast_channel,
                    timestamp,
                    str(output_file_path),
                    gemini_tokens_used,
                    1 if success else 0,
                ],
            )
            self._conn.commit()
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to mark episode as processed: {e}") from e

    def get_processed_episodes(
        self, channel_filter: Optional[str] = None
    ) -> List[Tuple[str, str, str, str]]:
        """
        Get list of processed episodes.

        Args:
            channel_filter: Optional channel name filter

        Returns:
            List of (uuid, title, channel, timestamp) tuples
        """
        if self._conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        query = """
            SELECT episode_uuid, episode_title, podcast_channel, processed_timestamp
            FROM processed_episodes
            WHERE success = 1
        """
        params = []

        if channel_filter:
            query += " AND podcast_channel = ?"
            params.append(channel_filter)

        query += " ORDER BY processed_timestamp DESC"

        cursor = self._conn.execute(query, params)
        return [
            (row["episode_uuid"], row["episode_title"], row["podcast_channel"], row["processed_timestamp"])
            for row in cursor.fetchall()
        ]

    def get_stats(self) -> dict:
        """
        Get statistics about processed episodes.

        Returns:
            Dictionary with stats (total_processed, total_tokens, unique_channels, etc.)
        """
        if self._conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        stats = {}

        # Total processed episodes
        cursor = self._conn.execute(
            "SELECT COUNT(*) as count FROM processed_episodes WHERE success = 1"
        )
        stats["total_processed"] = cursor.fetchone()["count"]

        # Total tokens used
        cursor = self._conn.execute(
            "SELECT SUM(gemini_tokens_used) as total FROM processed_episodes WHERE success = 1"
        )
        total_tokens = cursor.fetchone()["total"]
        stats["total_tokens_used"] = total_tokens if total_tokens else 0

        # Unique channels
        cursor = self._conn.execute(
            "SELECT COUNT(DISTINCT podcast_channel) as count FROM processed_episodes WHERE success = 1"
        )
        stats["unique_channels"] = cursor.fetchone()["count"]

        # Episodes per channel
        cursor = self._conn.execute(
            """
            SELECT podcast_channel, COUNT(*) as count
            FROM processed_episodes
            WHERE success = 1
            GROUP BY podcast_channel
            ORDER BY count DESC
            """
        )
        stats["episodes_per_channel"] = {
            row["podcast_channel"]: row["count"] for row in cursor.fetchall()
        }

        # Failed episodes
        cursor = self._conn.execute(
            "SELECT COUNT(*) as count FROM processed_episodes WHERE success = 0"
        )
        stats["failed_episodes"] = cursor.fetchone()["count"]

        # Most recent processing timestamp
        cursor = self._conn.execute(
            "SELECT MAX(processed_timestamp) as latest FROM processed_episodes WHERE success = 1"
        )
        latest = cursor.fetchone()["latest"]
        stats["latest_processed"] = latest if latest else None

        return stats

    def remove_episode(self, episode_uuid: str) -> bool:
        """
        Remove an episode from the tracking database.

        Args:
            episode_uuid: Episode UUID to remove

        Returns:
            True if episode was removed, False if not found
        """
        if self._conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        cursor = self._conn.execute(
            "DELETE FROM processed_episodes WHERE episode_uuid = ?",
            [episode_uuid],
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def clear_channel(self, podcast_channel: str) -> int:
        """
        Remove all episodes for a specific channel from tracking.

        Args:
            podcast_channel: Channel name to clear

        Returns:
            Number of episodes removed
        """
        if self._conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        cursor = self._conn.execute(
            "DELETE FROM processed_episodes WHERE podcast_channel = ?",
            [podcast_channel],
        )
        self._conn.commit()
        return cursor.rowcount

    def clear_all(self) -> int:
        """
        Clear all tracking data.

        Returns:
            Number of episodes removed
        """
        if self._conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        cursor = self._conn.execute("DELETE FROM processed_episodes")
        self._conn.commit()
        return cursor.rowcount


def is_episode_processed(db_path: Path, episode_uuid: str) -> bool:
    """
    Convenience function to check if an episode is processed.

    Args:
        db_path: Path to tracking database
        episode_uuid: Episode UUID

    Returns:
        True if processed, False otherwise
    """
    with TrackingDatabase(db_path) as db:
        return db.is_processed(episode_uuid)


def mark_episode_processed(
    db_path: Path,
    episode_uuid: str,
    episode_title: str,
    podcast_channel: str,
    output_file_path: Path,
    gemini_tokens_used: int,
    success: bool = True,
) -> None:
    """
    Convenience function to mark an episode as processed.

    Args:
        db_path: Path to tracking database
        episode_uuid: Episode UUID
        episode_title: Episode title
        podcast_channel: Podcast channel name
        output_file_path: Path to generated markdown file
        gemini_tokens_used: Total tokens used
        success: Whether processing was successful
    """
    with TrackingDatabase(db_path) as db:
        db.mark_processed(
            episode_uuid,
            episode_title,
            podcast_channel,
            output_file_path,
            gemini_tokens_used,
            success,
        )
