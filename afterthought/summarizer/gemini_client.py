"""Google Gemini API client for podcast summarization."""

import time
from dataclasses import dataclass
from typing import Optional

from google import genai
from google.genai import types


@dataclass
class SummaryResult:
    """Result from Gemini summarization."""

    summary: str
    input_tokens: int
    output_tokens: int
    model: str
    success: bool = True
    error: Optional[str] = None


class GeminiClient:
    """Client for Google Gemini API summarization."""

    YOUTUBE_PROMPT_TEMPLATE = """Summarize this video transcript as concise notes optimized for Obsidian's graph view.

**INSTRUCTIONS:**
- Only summarize what's actually in the transcript - don't add historical context or extra information
- Wrap important concepts, people, places, and technologies in [[double brackets]]
- Add relevant tags using #hashtag format
- Use bullet points, not paragraphs
- Be direct and information-dense

**STRUCTURE:**

## Summary
- 2-3 bullet points capturing the main points from the video
- Link key concepts mentioned: [[Person]], [[Technology]], [[Concept]]

## Key Points
- Main topics discussed in the transcript
- Nested bullets for details:
  - [[Topic]]
    - Important detail or insight
    - Related point

## Notable Quotes
- 2-3 significant quotes from the transcript (if any)

## Diagram (Optional)
If helpful, add ONE simple Mermaid diagram:
```mermaid
flowchart LR
    A[Topic] --> B[Subtopic]
```

**TAGS:**
Tags: #Topic #Category #Type

Transcript:
{transcript}"""

    DEFAULT_PROMPT_TEMPLATE = """You are an expert historian and Obsidian knowledge management specialist. Convert this podcast transcript into a concise, interconnected summary optimized for Obsidian's graph view.

**CRITICAL OBSIDIAN FORMATTING RULES:**

1. **Wiki Links for Connections:** Wrap ALL important concepts, people, places, events, and themes in [[double brackets]]
   - Examples: [[Roman Empire]], [[Julius Caesar]], [[Battle of Cannae]], [[Republicanism]]
   - This creates nodes in Obsidian's graph view

2. **Tags for Categories:** Add relevant tags using #hashtag format
   - Use tags for: periods (#AncientRome, #MedievalEurope), themes (#MilitaryHistory, #PoliticalPhilosophy), regions (#Mediterranean)

3. **Mermaid Diagrams:** Include ONE timeline or relationship diagram using Mermaid syntax
   - For historical episodes: use timeline format
   - For concept-heavy episodes: use flowchart or graph

4. **Concise Bullets:** Use nested bullet points, not paragraphs. Be direct and information-dense.

**REQUIRED STRUCTURE:**

## Summary
- 2-3 concise bullet points capturing the core historical narrative
- Link all key concepts: [[Person]], [[Event]], [[Place]], [[Concept]]

## Historical Context
- Background information with wiki links
- Nested structure showing relationships:
  - [[Major Event]]
    - [[Key Figure]] and their role
    - [[Political Context]]
    - [[Cultural Significance]]

## Key Events & Developments
- Chronological or thematic breakdown
- Each point should link entities: "[[Caesar]] crossed the [[Rubicon]] in [[49 BC]]"
- Deep nesting for cause-effect relationships

## Notable Quotes
- 2-3 significant quotes with speaker attribution
- Brief context or significance (1 line max)

## Visual Timeline/Diagram
```mermaid
timeline
    title [Episode Topic]
    [Period] : [Event 1]
             : [Event 2]
    [Period] : [Event 3]
```

**TAGS TO ADD:**
Add 5-10 relevant tags at the bottom in this format:
Tags: #HistoricalPeriod #Theme1 #Theme2 #Region #KeyConcept

**LINKING STRATEGY:**
- Link historical figures: [[Marcus Aurelius]], [[Cicero]]
- Link events: [[Punic Wars]], [[Fall of Rome]]
- Link places: [[Rome]], [[Carthage]], [[Mediterranean]]
- Link concepts: [[Stoicism]], [[Republic]], [[Empire]]
- Link time periods: [[Late Republic]], [[Pax Romana]]

Be CONCISE. No fluff. Dense information. Heavy linking for graph connectivity.

---

Transcript:
{transcript}"""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash-exp",
        max_retries: int = 3,
        prompt_template: Optional[str] = None,
    ):
        """
        Initialize Gemini client.

        Args:
            api_key: Google Gemini API key
            model: Model to use (default: gemini-2.0-flash-exp)
            max_retries: Maximum number of retry attempts (default: 3)
            prompt_template: Custom prompt template (default: use DEFAULT_PROMPT_TEMPLATE)

        Raises:
            ValueError: If API key is invalid
        """
        if not api_key or api_key == "your_api_key_here":
            raise ValueError(
                "Invalid API key. Get your API key from https://aistudio.google.com/app/apikey"
            )

        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.prompt_template = prompt_template or self.DEFAULT_PROMPT_TEMPLATE

        # Initialize Gemini client
        self.client = genai.Client(api_key=api_key)

    def summarize(self, transcript: str, episode_title: Optional[str] = None) -> SummaryResult:
        """
        Summarize a podcast transcript using Gemini API.

        Args:
            transcript: The podcast transcript text
            episode_title: Optional episode title for context

        Returns:
            SummaryResult with summary and token usage

        Raises:
            Exception: If summarization fails after all retries
        """
        if not transcript or not transcript.strip():
            return SummaryResult(
                summary="",
                input_tokens=0,
                output_tokens=0,
                model=self.model,
                success=False,
                error="Empty transcript provided",
            )

        # Build prompt
        prompt = self.prompt_template.format(transcript=transcript)

        # Add episode title context if provided
        if episode_title:
            context = f"Episode Title: {episode_title}\n\n"
            prompt = context + prompt

        # Attempt summarization with retries
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = self._call_api(prompt)
                return response
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    # Exponential backoff: 2^attempt seconds
                    wait_time = 2 ** attempt
                    print(
                        f"  ⚠ API error (attempt {attempt + 1}/{self.max_retries}): {e}"
                    )
                    print(f"  ⏳ Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    # Final attempt failed
                    print(f"  ✗ Failed after {self.max_retries} attempts: {e}")

        # All retries exhausted
        return SummaryResult(
            summary="",
            input_tokens=0,
            output_tokens=0,
            model=self.model,
            success=False,
            error=str(last_error),
        )

    def _call_api(self, prompt: str) -> SummaryResult:
        """
        Make API call to Gemini.

        Args:
            prompt: The full prompt to send

        Returns:
            SummaryResult with response and token usage

        Raises:
            Exception: If API call fails
        """
        try:
            # Generate content using the Gemini API
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,  # Lower temperature for more focused summaries
                    max_output_tokens=8192,  # Increased for detailed historical summaries with diagrams
                ),
            )

            # Extract text from response
            summary_text = response.text

            # Extract token usage
            input_tokens = 0
            output_tokens = 0

            if hasattr(response, "usage_metadata"):
                usage = response.usage_metadata
                input_tokens = getattr(usage, "prompt_token_count", 0)
                output_tokens = getattr(usage, "candidates_token_count", 0)

            return SummaryResult(
                summary=summary_text.strip(),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=self.model,
                success=True,
            )

        except Exception as e:
            # Re-raise with more context
            raise Exception(f"Gemini API error: {e}") from e

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for a given text.

        This is a rough estimate: ~4 characters per token on average.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        return len(text) // 4

    def check_transcript_length(self, transcript: str) -> tuple[bool, int]:
        """
        Check if transcript length is within model limits.

        Args:
            transcript: The transcript text

        Returns:
            Tuple of (is_valid, estimated_tokens)
        """
        estimated = self.estimate_tokens(transcript)

        # Gemini 2.0 Flash has a large context window (1M tokens for 2.0-flash-exp)
        # But we'll set a conservative limit of 500K tokens for safety
        max_tokens = 500_000

        return (estimated <= max_tokens, estimated)


def summarize_transcript(
    transcript: str,
    api_key: str,
    model: str = "gemini-2.0-flash-exp",
    episode_title: Optional[str] = None,
) -> SummaryResult:
    """
    Convenience function to summarize a transcript.

    Args:
        transcript: The podcast transcript text
        api_key: Google Gemini API key
        model: Model to use (default: gemini-2.0-flash-exp)
        episode_title: Optional episode title for context

    Returns:
        SummaryResult with summary and token usage
    """
    client = GeminiClient(api_key=api_key, model=model)
    return client.summarize(transcript, episode_title)
