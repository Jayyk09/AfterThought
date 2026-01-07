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

    DEFAULT_PROMPT_TEMPLATE = """You are summarizing a podcast episode transcript. Your goal is to create a comprehensive yet concise summary that captures the key information from the episode.

Please provide:

1. **Overview** (2-3 sentences): A high-level summary of what the episode is about and the main themes discussed.

2. **Key Topics**: List the main topics discussed in bullet point format. Be specific and include important details.

3. **Notable Quotes or Insights**: Highlight 2-3 interesting quotes, insights, or key points that stood out in the discussion.

4. **Action Items or Takeaways**: If applicable, list any practical advice, recommendations, or conclusions that listeners should remember.

Keep your summary informative but concise. Focus on substance over length.

---

## Transcript:

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
                    max_output_tokens=2048,  # Reasonable limit for summaries
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
