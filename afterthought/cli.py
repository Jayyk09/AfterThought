"""Command-line interface for AfterThought podcast summarization tool."""

import glob
import sys
from pathlib import Path
from typing import Optional

import click

from afterthought.config import get_settings
from afterthought.db.podcast_db import PodcastDatabase, Episode
from afterthought.db.tracking_db import TrackingDatabase
from afterthought.parsers.ttml_parser import parse_ttml_file
from afterthought.summarizer.gemini_client import GeminiClient
from afterthought.output.markdown_writer import MarkdownWriter
from afterthought.automation.podcast_player import PodcastPlayerAutomation


@click.command()
@click.option(
    "--channel",
    "-c",
    default=None,
    help="Fuzzy match podcast channel name (e.g., 'All-In', 'Lex Fridman')",
)
@click.option(
    "--days",
    "-d",
    default=None,
    type=int,
    help="Episodes played in last N days (default: from config, usually 7)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Re-process already summarized episodes",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be processed without executing",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
@click.option(
    "--stats",
    is_flag=True,
    help="Show processing statistics and exit",
)
@click.option(
    "--fetch-missing",
    is_flag=True,
    help="Automatically fetch missing transcripts by triggering playback in Podcasts app",
)
def main(
    channel: Optional[str],
    days: Optional[int],
    force: bool,
    dry_run: bool,
    verbose: bool,
    stats: bool,
    fetch_missing: bool,
):
    """
    AfterThought - Summarize your podcast episodes.

    Automatically extracts transcripts from Apple Podcasts, generates AI-powered
    summaries using Google Gemini, and outputs Obsidian-compatible markdown files.

    Examples:

        \b
        # Summarize all episodes from last 7 days
        afterthought

        \b
        # Summarize specific channel
        afterthought --channel "All-In Podcast"

        \b
        # Custom date range and force re-process
        afterthought --days 30 --force

        \b
        # Dry run to preview what would be processed
        afterthought --dry-run
    """
    try:
        # Load configuration
        settings = get_settings()

        # Use days from CLI or fall back to config
        days_filter = days if days is not None else settings.default_days_filter

        # Show statistics if requested
        if stats:
            show_statistics(settings)
            return

        # Print header
        click.echo("\n" + "=" * 60)
        click.echo("  AfterThought - Podcast Summarization Tool")
        click.echo("=" * 60 + "\n")

        # Show configuration
        click.echo("Configuration:")
        click.echo(f"  Output Path: {settings.obsidian_output_path}")
        click.echo(f"  Date Filter: Last {days_filter} days")
        if channel:
            click.echo(f"  Channel Filter: {channel} (fuzzy match)")
        if force:
            click.echo(f"  Force Re-process: Enabled")
        if fetch_missing:
            click.echo(f"  Auto-Fetch Transcripts: Enabled")
        if dry_run:
            click.echo(f"  Dry Run: Enabled (no changes will be made)")
        click.echo()

        # Query episodes
        click.echo("Querying Apple Podcasts database...")
        with PodcastDatabase(settings.apple_podcasts_db_path) as db:
            try:
                episodes = db.get_episodes_by_date(
                    days=days_filter,
                    channel_filter=channel,
                )
            except ValueError as e:
                click.echo(f"✗ Error: {e}", err=True)
                sys.exit(1)

        if not episodes:
            click.echo("✗ No episodes found matching criteria.")
            sys.exit(0)

        click.echo(f"✓ Found {len(episodes)} episode(s) matching criteria\n")

        # Filter by tracking database
        with TrackingDatabase(settings.tracking_db_path) as tracking_db:
            if not force:
                already_processed = []
                new_episodes = []

                for ep in episodes:
                    if tracking_db.is_processed(ep.uuid):
                        already_processed.append(ep)
                    else:
                        new_episodes.append(ep)

                if already_processed:
                    click.echo(
                        f"  - {len(already_processed)} already processed "
                        f"(use --force to re-process)"
                    )

                if not new_episodes:
                    click.echo("\n✓ All episodes already processed!")
                    sys.exit(0)

                episodes = new_episodes
                click.echo(f"  - {len(episodes)} new episode(s) to summarize\n")
            else:
                click.echo(f"  - Force mode: processing all {len(episodes)} episode(s)\n")

        if dry_run:
            click.echo("Dry run - episodes that would be processed:\n")
            for i, ep in enumerate(episodes, 1):
                click.echo(f"  [{i}/{len(episodes)}] {ep.podcast_channel}")
                click.echo(f"      Title: {ep.title}")
                click.echo(f"      Transcript: {'Yes' if ep.transcript_identifier else 'No'}")
            click.echo("\nDry run complete. No changes made.")
            return

        # Process episodes
        click.echo(f"Processing {len(episodes)} episode(s):\n")
        stats_data = {
            "processed": 0,
            "skipped": 0,
            "errors": 0,
            "total_tokens": 0,
        }

        # Initialize clients
        gemini_client = GeminiClient(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            max_retries=settings.max_retries,
        )
        markdown_writer = MarkdownWriter(settings.obsidian_output_path)

        # Initialize automation if fetch_missing is enabled
        automation = PodcastPlayerAutomation() if fetch_missing else None

        with TrackingDatabase(settings.tracking_db_path) as tracking_db:
            for i, episode in enumerate(episodes, 1):
                click.echo(f"[{i}/{len(episodes)}] {episode.podcast_channel}")
                click.echo(f"    Title: {episode.title}")

                try:
                    # Process episode
                    result = process_episode(
                        episode,
                        gemini_client,
                        markdown_writer,
                        settings,
                        verbose,
                        automation,
                    )

                    if result["success"]:
                        # Mark as processed in tracking DB
                        tracking_db.mark_processed(
                            episode_uuid=episode.uuid,
                            episode_title=episode.title,
                            podcast_channel=episode.podcast_channel,
                            output_file_path=result["output_path"],
                            gemini_tokens_used=result["tokens_used"],
                            success=True,
                        )
                        stats_data["processed"] += 1
                        stats_data["total_tokens"] += result["tokens_used"]
                        click.echo(f"    ✓ Saved: {result['output_path']}\n")
                    else:
                        stats_data["skipped"] += 1
                        click.echo(f"    ⚠ {result['message']}\n")

                except Exception as e:
                    stats_data["errors"] += 1
                    click.echo(f"    ✗ Error: {e}\n", err=True)
                    if verbose:
                        import traceback
                        traceback.print_exc()

        # Print summary
        click.echo("=" * 60)
        click.echo("\nSummary:")
        click.echo(f"  Processed: {stats_data['processed']}/{len(episodes)} episodes")
        if stats_data["skipped"] > 0:
            click.echo(f"  Skipped: {stats_data['skipped']} (no transcript)")
        if stats_data["errors"] > 0:
            click.echo(f"  Errors: {stats_data['errors']}")
        click.echo(f"  Gemini Tokens Used: {stats_data['total_tokens']:,}")
        click.echo(f"  Output Directory: {settings.obsidian_output_path}")
        click.echo("\n✨ Done!\n")

    except KeyboardInterrupt:
        click.echo("\n\n✗ Interrupted by user", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"\n✗ Fatal error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def process_episode(
    episode: Episode,
    gemini_client: GeminiClient,
    markdown_writer: MarkdownWriter,
    settings,
    verbose: bool,
    automation: Optional[PodcastPlayerAutomation] = None,
) -> dict:
    """
    Process a single episode: load transcript, summarize, write markdown.

    Args:
        episode: Episode metadata
        gemini_client: Gemini API client
        markdown_writer: Markdown writer
        settings: Application settings
        verbose: Verbose output flag
        automation: Optional podcast player automation for fetching missing transcripts

    Returns:
        Dict with success status, message, output_path, and tokens_used
    """
    # Check for transcript
    transcript_missing = not episode.transcript_identifier

    # Try to fetch transcript if missing and automation is enabled
    if transcript_missing and automation:
        click.echo("    ⚠ No transcript identifier found")
        if automation.trigger_transcript_download(episode):
            click.echo("    ✓ Playback triggered, checking for transcript...")
            # Note: transcript_identifier might still be None after fetch
            # This is expected - we'll check the file system below
            transcript_missing = False  # Allow to continue and check file system
        else:
            return {
                "success": False,
                "message": "No transcript available (fetch failed)",
                "output_path": None,
                "tokens_used": 0,
            }
    elif transcript_missing:
        return {
            "success": False,
            "message": "No transcript available",
            "output_path": None,
            "tokens_used": 0,
        }

    # Find TTML file
    if episode.transcript_identifier:
        ttml_pattern = str(settings.ttml_cache_path / "**" / f"*{episode.transcript_identifier}*")
    else:
        # If we just fetched it, search for any new TTML files for this episode
        # Use episode UUID as fallback search
        ttml_pattern = str(settings.ttml_cache_path / "**" / f"*{episode.uuid}*")

    matches = glob.glob(ttml_pattern, recursive=True)

    if not matches:
        # If automation is enabled and we haven't tried yet, try to fetch
        if automation and not transcript_missing:
            click.echo("    ⚠ Transcript file not found in cache")
            if automation.trigger_transcript_download(episode):
                click.echo("    ✓ Playback triggered, rechecking...")
                # Retry finding the file
                matches = glob.glob(ttml_pattern, recursive=True)
                if not matches:
                    return {
                        "success": False,
                        "message": "Transcript file not found after fetch attempt",
                        "output_path": None,
                        "tokens_used": 0,
                    }
            else:
                return {
                    "success": False,
                    "message": "Transcript file not found (fetch failed)",
                    "output_path": None,
                    "tokens_used": 0,
                }
        else:
            return {
                "success": False,
                "message": f"Transcript file not found: {episode.transcript_identifier}",
                "output_path": None,
                "tokens_used": 0,
            }

    ttml_path = Path(matches[0])
    if verbose:
        click.echo(f"    📄 Transcript: {ttml_path}")

    # Parse TTML
    click.echo("    ⏳ Fetching transcript...")
    try:
        transcript = parse_ttml_file(ttml_path, preserve_speakers=settings.preserve_speakers)
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to parse transcript: {e}",
            "output_path": None,
            "tokens_used": 0,
        }

    word_count = len(transcript.split())
    if verbose:
        click.echo(f"    ✓ Transcript loaded ({word_count:,} words)")

    # Check length
    is_valid, estimated_tokens = gemini_client.check_transcript_length(transcript)
    if not is_valid:
        return {
            "success": False,
            "message": f"Transcript too long ({estimated_tokens:,} tokens)",
            "output_path": None,
            "tokens_used": 0,
        }

    # Summarize
    click.echo("    ⏳ Summarizing with Gemini API...")
    summary = gemini_client.summarize(transcript, episode_title=episode.title)

    if not summary.success:
        return {
            "success": False,
            "message": f"Summarization failed: {summary.error}",
            "output_path": None,
            "tokens_used": 0,
        }

    total_tokens = summary.input_tokens + summary.output_tokens
    if verbose:
        click.echo(f"    ✓ Summary generated ({total_tokens:,} tokens)")

    # Write markdown
    click.echo("    ⏳ Writing markdown...")
    try:
        output_path = markdown_writer.write_summary(
            episode=episode,
            summary=summary,
            transcript_available=True,
        )
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to write markdown: {e}",
            "output_path": None,
            "tokens_used": total_tokens,
        }

    return {
        "success": True,
        "message": "Processed successfully",
        "output_path": output_path,
        "tokens_used": total_tokens,
    }


def show_statistics(settings):
    """Show processing statistics from tracking database."""
    with TrackingDatabase(settings.tracking_db_path) as tracking_db:
        stats = tracking_db.get_stats()

    click.echo("\n" + "=" * 60)
    click.echo("  AfterThought - Processing Statistics")
    click.echo("=" * 60 + "\n")

    click.echo(f"Total Episodes Processed: {stats['total_processed']}")
    click.echo(f"Total Tokens Used: {stats['total_tokens_used']:,}")
    click.echo(f"Unique Channels: {stats['unique_channels']}")
    click.echo(f"Failed Episodes: {stats['failed_episodes']}")

    if stats['latest_processed']:
        click.echo(f"Latest Processing: {stats['latest_processed']}")

    if stats['episodes_per_channel']:
        click.echo("\nEpisodes per Channel:")
        for channel, count in sorted(
            stats['episodes_per_channel'].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            click.echo(f"  - {channel}: {count}")

    click.echo()


if __name__ == "__main__":
    main()
