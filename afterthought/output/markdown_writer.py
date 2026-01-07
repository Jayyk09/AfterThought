"""Write Obsidian-compatible markdown files with podcast summaries."""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from afterthought.db.podcast_db import Episode
from afterthought.summarizer.gemini_client import SummaryResult


class MarkdownWriter:
    """Writer for Obsidian-compatible markdown files."""

    def __init__(self, output_path: Path):
        """
        Initialize markdown writer.

        Args:
            output_path: Base output directory for markdown files
        """
        self.output_path = output_path

    def write_summary(
        self,
        episode: Episode,
        summary: SummaryResult,
        transcript_available: bool = True,
    ) -> Path:
        """
        Write episode summary to markdown file.

        Args:
            episode: Episode metadata
            summary: Summary result from Gemini
            transcript_available: Whether transcript was available

        Returns:
            Path to created markdown file

        Raises:
            IOError: If file cannot be written
        """
        # Create channel directory
        channel_dir = self._get_channel_directory(episode.podcast_channel)
        channel_dir.mkdir(parents=True, exist_ok=True)

        # Generate markdown content
        content = self._generate_markdown(episode, summary, transcript_available)

        # Create filename
        filename = self._sanitize_filename(episode.title)
        filepath = channel_dir / f"{filename}.md"

        # Handle name collisions
        filepath = self._handle_collision(filepath)

        # Write file
        try:
            filepath.write_text(content, encoding="utf-8")
            return filepath
        except Exception as e:
            raise IOError(f"Failed to write markdown file {filepath}: {e}") from e

    def _get_channel_directory(self, channel_name: str) -> Path:
        """
        Get directory path for a podcast channel.

        Args:
            channel_name: Name of the podcast channel

        Returns:
            Path to channel directory
        """
        sanitized = self._sanitize_filename(channel_name)
        return self.output_path / sanitized

    def _sanitize_filename(self, filename: str, max_length: int = 100) -> str:
        """
        Sanitize filename by removing invalid characters and limiting length.

        Args:
            filename: Original filename
            max_length: Maximum filename length (default: 100)

        Returns:
            Sanitized filename
        """
        # Remove or replace invalid characters
        # Invalid: / \ : * ? " < > |
        sanitized = re.sub(r'[/\\:*?"<>|]', "", filename)

        # Replace multiple spaces with single space
        sanitized = re.sub(r"\s+", " ", sanitized)

        # Strip leading/trailing whitespace and dots
        sanitized = sanitized.strip(". ")

        # Limit length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length].strip()

        # Fallback if empty
        if not sanitized:
            sanitized = "untitled"

        return sanitized

    def _handle_collision(self, filepath: Path) -> Path:
        """
        Handle filename collisions by appending a number.

        Args:
            filepath: Desired file path

        Returns:
            Available file path (may have number appended)
        """
        if not filepath.exists():
            return filepath

        # File exists, append number
        base = filepath.stem
        ext = filepath.suffix
        parent = filepath.parent
        counter = 1

        while True:
            new_path = parent / f"{base}_{counter}{ext}"
            if not new_path.exists():
                return new_path
            counter += 1

    def _generate_markdown(
        self,
        episode: Episode,
        summary: SummaryResult,
        transcript_available: bool,
    ) -> str:
        """
        Generate markdown content with frontmatter and summary.

        Args:
            episode: Episode metadata
            summary: Summary result
            transcript_available: Whether transcript was available

        Returns:
            Formatted markdown content
        """
        # Generate frontmatter
        frontmatter = self._generate_frontmatter(
            episode, summary, transcript_available
        )

        # Format summary content
        if summary.success and summary.summary:
            summary_content = summary.summary
        else:
            summary_content = self._generate_fallback_content(
                episode, transcript_available, summary.error
            )

        # Combine frontmatter and content
        markdown = f"{frontmatter}\n\n{summary_content}\n"
        return markdown

    def _generate_frontmatter(
        self,
        episode: Episode,
        summary: SummaryResult,
        transcript_available: bool,
    ) -> str:
        """
        Generate YAML frontmatter for Obsidian.

        Args:
            episode: Episode metadata
            summary: Summary result
            transcript_available: Whether transcript was available

        Returns:
            YAML frontmatter string
        """
        lines = ["---"]

        # Core metadata
        lines.append("type: podcast-summary")
        lines.append("cssclass: podcast")

        # Title and aliases for better linking
        lines.append(f'title: "{self._escape_yaml(episode.title)}"')
        lines.append("aliases:")
        lines.append(f'  - "{self._escape_yaml(episode.title)}"')

        # Podcast info
        lines.append(f'podcast: "[[{self._escape_yaml(episode.podcast_channel)}]]"')

        if episode.podcast_author:
            lines.append(f'author: "{self._escape_yaml(episode.podcast_author)}"')

        # Dates
        if episode.publish_date:
            lines.append(f"date: {episode.publish_date.strftime('%Y-%m-%d')}")

        if episode.last_played:
            lines.append(f"listened: {episode.last_played.strftime('%Y-%m-%d')}")

        # Duration
        if episode.duration > 0:
            lines.append(f'duration: "{episode.duration_formatted}"')

        # Tags placeholder (AI will add more in content)
        lines.append("tags:")
        lines.append("  - podcast")
        lines.append(f"  - {self._sanitize_tag(episode.podcast_channel)}")

        # Status tracking
        lines.append(f"transcript_available: {str(transcript_available).lower()}")

        if episode.transcript_provider:
            lines.append(f'transcript_provider: "{episode.transcript_provider}"')

        # Token usage (if available)
        if summary.success:
            lines.append(f"input_tokens: {summary.input_tokens}")
            lines.append(f"output_tokens: {summary.output_tokens}")
            lines.append(f'ai_model: "{summary.model}"')

        # UUID for tracking
        lines.append(f'episode_uuid: "{episode.uuid}"')

        lines.append("---")
        return "\n".join(lines)

    def _escape_yaml(self, text: str) -> str:
        """
        Escape special characters for YAML strings.

        Args:
            text: Text to escape

        Returns:
            Escaped text
        """
        # Escape double quotes
        return text.replace('"', '\\"')

    def _sanitize_tag(self, text: str) -> str:
        """
        Sanitize text for use as an Obsidian tag.

        Args:
            text: Text to convert to tag format

        Returns:
            Tag-safe string
        """
        # Remove special characters, replace spaces with hyphens
        import re
        tag = re.sub(r'[^\w\s-]', '', text)
        tag = re.sub(r'\s+', '-', tag)
        return tag.lower()

    def _generate_fallback_content(
        self,
        episode: Episode,
        transcript_available: bool,
        error: Optional[str] = None,
    ) -> str:
        """
        Generate fallback content when summary is not available.

        Args:
            episode: Episode metadata
            transcript_available: Whether transcript was available
            error: Optional error message

        Returns:
            Fallback markdown content
        """
        content = f"# {episode.title}\n\n"

        if not transcript_available:
            content += (
                "**Note:** Transcript not available for this episode. "
                "Summaries require transcript data from Apple Podcasts.\n\n"
            )
        elif error:
            content += (
                f"**Note:** Failed to generate summary. Error: {error}\n\n"
            )

        content += "## Episode Information\n\n"
        content += f"- **Podcast:** {episode.podcast_channel}\n"

        if episode.podcast_author:
            content += f"- **Author:** {episode.podcast_author}\n"

        if episode.publish_date:
            content += f"- **Published:** {episode.publish_date.strftime('%Y-%m-%d')}\n"

        if episode.duration > 0:
            content += f"- **Duration:** {episode.duration_formatted}\n"

        if episode.last_played:
            content += f"- **Last Played:** {episode.last_played.strftime('%Y-%m-%d %H:%M:%S')}\n"

        return content


def write_episode_summary(
    episode: Episode,
    summary: SummaryResult,
    output_path: Path,
    transcript_available: bool = True,
) -> Path:
    """
    Convenience function to write an episode summary.

    Args:
        episode: Episode metadata
        summary: Summary result
        output_path: Output directory
        transcript_available: Whether transcript was available

    Returns:
        Path to created markdown file
    """
    writer = MarkdownWriter(output_path)
    return writer.write_summary(episode, summary, transcript_available)
