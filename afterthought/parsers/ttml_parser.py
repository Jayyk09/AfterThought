"""Parse Apple Podcasts TTML (Timed Text Markup Language) transcript files."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


# TTML namespace mappings
NAMESPACES = {
    "tt": "http://www.w3.org/ns/ttml",
    "ttm": "http://www.w3.org/ns/ttml#metadata",
    "podcasts": "http://podcasts.apple.com/transcript-ttml-internal",
}


@dataclass
class TranscriptSegment:
    """A segment of transcript text with optional speaker and timing."""

    text: str
    speaker: Optional[str] = None
    begin: Optional[float] = None
    end: Optional[float] = None


class TTMLParser:
    """Parser for Apple Podcasts TTML transcript files."""

    def __init__(self, preserve_speakers: bool = True):
        """
        Initialize TTML parser.

        Args:
            preserve_speakers: Whether to preserve speaker identification (default: True)
        """
        self.preserve_speakers = preserve_speakers

    def parse_file(self, ttml_path: Path) -> str:
        """
        Parse a TTML file and extract transcript text.

        Args:
            ttml_path: Path to TTML file

        Returns:
            Clean transcript text

        Raises:
            FileNotFoundError: If TTML file doesn't exist
            ET.ParseError: If TTML file is malformed
        """
        if not ttml_path.exists():
            raise FileNotFoundError(f"TTML file not found: {ttml_path}")

        try:
            tree = ET.parse(ttml_path)
            root = tree.getroot()
            return self.parse_root(root)
        except ET.ParseError as e:
            raise ET.ParseError(
                f"Failed to parse TTML file {ttml_path}: {e}"
            ) from e

    def parse_string(self, ttml_content: str) -> str:
        """
        Parse TTML content from a string.

        Args:
            ttml_content: TTML XML content as string

        Returns:
            Clean transcript text

        Raises:
            ET.ParseError: If TTML content is malformed
        """
        try:
            root = ET.fromstring(ttml_content)
            return self.parse_root(root)
        except ET.ParseError as e:
            raise ET.ParseError(f"Failed to parse TTML content: {e}") from e

    def parse_root(self, root: ET.Element) -> str:
        """
        Parse TTML root element and extract text.

        Args:
            root: TTML root element

        Returns:
            Clean transcript text
        """
        segments = self._extract_segments(root)
        return self._format_transcript(segments)

    def _extract_segments(self, root: ET.Element) -> List[TranscriptSegment]:
        """
        Extract transcript segments from TTML structure.

        TTML structure: <tt> → <body> → <div> → <p> → <span>*

        Args:
            root: TTML root element

        Returns:
            List of TranscriptSegment objects
        """
        segments = []

        # Find body element
        body = root.find(".//tt:body", NAMESPACES)
        if body is None:
            # Try without namespace
            body = root.find(".//body")
        if body is None:
            return segments

        # Find all paragraph (<p>) elements
        # Each paragraph typically represents a speaker turn
        for p_elem in body.findall(".//tt:p", NAMESPACES):
            speaker = self._extract_speaker(p_elem)
            begin = self._parse_time(p_elem.get("begin"))
            end = self._parse_time(p_elem.get("end"))

            # Extract text from all child spans
            paragraph_text = self._extract_paragraph_text(p_elem)

            if paragraph_text.strip():
                segment = TranscriptSegment(
                    text=paragraph_text.strip(),
                    speaker=speaker,
                    begin=begin,
                    end=end,
                )
                segments.append(segment)

        # Fallback: try without namespace if no segments found
        if not segments:
            for p_elem in body.findall(".//p"):
                paragraph_text = self._extract_paragraph_text(p_elem)
                if paragraph_text.strip():
                    segment = TranscriptSegment(text=paragraph_text.strip())
                    segments.append(segment)

        return segments

    def _extract_speaker(self, p_elem: ET.Element) -> Optional[str]:
        """
        Extract speaker identification from paragraph element.

        Args:
            p_elem: Paragraph element

        Returns:
            Speaker identifier (e.g., "SPEAKER_1") or None
        """
        if not self.preserve_speakers:
            return None

        # Check for ttm:agent attribute
        speaker = p_elem.get(f"{{{NAMESPACES['ttm']}}}agent")
        if speaker:
            return speaker

        # Try without namespace
        speaker = p_elem.get("agent")
        return speaker

    def _extract_paragraph_text(self, p_elem: ET.Element) -> str:
        """
        Extract all text from a paragraph element, including nested spans.

        Args:
            p_elem: Paragraph element

        Returns:
            Concatenated text from all child elements
        """
        # Use itertext() to get all text content, preserving order
        text_parts = []
        for text in p_elem.itertext():
            cleaned = text.strip()
            if cleaned:
                text_parts.append(cleaned)

        return " ".join(text_parts)

    def _parse_time(self, time_str: Optional[str]) -> Optional[float]:
        """
        Parse TTML time string to seconds.

        Supports formats:
        - "123.456" (seconds)
        - "1:23.456" (minutes:seconds)
        - "1:23:45.678" (hours:minutes:seconds)

        Args:
            time_str: Time string from TTML

        Returns:
            Time in seconds, or None if parsing fails
        """
        if not time_str:
            return None

        try:
            # Remove any 's' suffix (e.g., "123.456s")
            time_str = time_str.rstrip("s")

            parts = time_str.split(":")
            if len(parts) == 1:
                # Just seconds
                return float(parts[0])
            elif len(parts) == 2:
                # Minutes:seconds
                minutes, seconds = parts
                return float(minutes) * 60 + float(seconds)
            elif len(parts) == 3:
                # Hours:minutes:seconds
                hours, minutes, seconds = parts
                return float(hours) * 3600 + float(minutes) * 60 + float(seconds)
        except (ValueError, AttributeError):
            pass

        return None

    def _format_transcript(self, segments: List[TranscriptSegment]) -> str:
        """
        Format transcript segments into readable text.

        Args:
            segments: List of TranscriptSegment objects

        Returns:
            Formatted transcript text
        """
        if not segments:
            return ""

        lines = []
        current_speaker = None

        for segment in segments:
            if self.preserve_speakers and segment.speaker:
                if segment.speaker != current_speaker:
                    # New speaker, add speaker label
                    lines.append(f"\n[{segment.speaker}]")
                    current_speaker = segment.speaker
                lines.append(segment.text)
            else:
                # No speaker labels, just add text
                lines.append(segment.text)

        # Join with spaces, clean up extra whitespace
        transcript = " ".join(lines)
        transcript = " ".join(transcript.split())  # Normalize whitespace

        return transcript.strip()


def parse_ttml_file(
    ttml_path: Path, preserve_speakers: bool = True
) -> str:
    """
    Convenience function to parse a TTML file.

    Args:
        ttml_path: Path to TTML file
        preserve_speakers: Whether to preserve speaker identification

    Returns:
        Clean transcript text

    Raises:
        FileNotFoundError: If TTML file doesn't exist
        ET.ParseError: If TTML file is malformed
    """
    parser = TTMLParser(preserve_speakers=preserve_speakers)
    return parser.parse_file(ttml_path)


def get_ttml_duration(ttml_path: Path) -> Optional[float]:
    """
    Extract total duration from TTML file metadata.

    Args:
        ttml_path: Path to TTML file

    Returns:
        Duration in seconds, or None if not found
    """
    try:
        tree = ET.parse(ttml_path)
        root = tree.getroot()

        # Find body element and check for dur attribute
        body = root.find(".//tt:body", NAMESPACES)
        if body is None:
            body = root.find(".//body")

        if body is not None:
            dur = body.get("dur")
            if dur:
                # Parse duration (format: "123.456")
                try:
                    return float(dur)
                except ValueError:
                    pass

    except (ET.ParseError, FileNotFoundError):
        pass

    return None
