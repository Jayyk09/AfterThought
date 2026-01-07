# AfterThought

**AI-Powered Podcast Summarization for Apple Podcasts**

AfterThought automatically extracts transcripts from Apple Podcasts, generates AI-powered summaries using Google Gemini, and outputs beautifully formatted Obsidian-compatible markdown files organized by podcast channel.

## Features

- 📊 **Smart Episode Discovery**: Automatically finds recently listened podcast episodes from Apple Podcasts
- 🎯 **Fuzzy Channel Matching**: Filter by podcast channel name with intelligent fuzzy matching
- 🤖 **AI Summarization**: Leverages Google Gemini API for high-quality episode summaries
- 📝 **Obsidian Integration**: Creates markdown files with frontmatter, organized by channel
- 🔍 **Tracking**: Avoids re-processing episodes you've already summarized
- ⚡ **Incremental Processing**: Run regularly to keep your podcast notes up-to-date
- 🔄 **Efficient**: Word-level TTML transcript parsing with speaker identification

## Requirements

- **Python 3.8+**
- **macOS** (for Apple Podcasts database access)
- **Google Gemini API key** ([Get one free here](https://aistudio.google.com/app/apikey))
- **Obsidian** (optional, but recommended for viewing summaries)

## Installation

### Quick Install (Recommended)

**Option 1: Using pipx (global access, isolated environment)**
```bash
git clone https://github.com/Jayyk09/AfterThought.git
cd AfterThought
brew install pipx
pipx install .
```

**Option 2: Using pip (editable install)**
```bash
git clone https://github.com/Jayyk09/AfterThought.git
cd AfterThought
pip install -e .
```

**Option 3: Traditional venv (manual activation)**
```bash
git clone https://github.com/Jayyk09/AfterThought.git
cd AfterThought
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

📖 **See [INSTALL.md](INSTALL.md) for detailed installation instructions and shell wrapper setup.**

### Configure

```bash
cp .env.example .env
# Edit .env with your settings
```

Required settings:
- `GEMINI_API_KEY` - Get free key at [Google AI Studio](https://aistudio.google.com/app/apikey)
- `OBSIDIAN_OUTPUT_PATH` - Path to your Obsidian vault

Apple Podcasts paths are auto-detected!

## Usage

### Basic Usage

Summarize episodes played in the last 7 days:

```bash
python -m afterthought
```

### Filter by Podcast Channel

Use fuzzy matching to filter by channel name:

```bash
python -m afterthought --channel "All-In"
python -m afterthought -c "Lex Fridman"
```

### Custom Date Range

Summarize episodes from the last 30 days:

```bash
python -m afterthought --days 30
python -m afterthought -d 14
```

### Force Re-processing

Re-process already summarized episodes:

```bash
python -m afterthought --force
python -m afterthought -c "All-In" --force
```

### Dry Run

Preview what would be processed without making changes:

```bash
python -m afterthought --dry-run
```

### Show Statistics

View processing statistics from your tracking database:

```bash
python -m afterthought --stats
```

### Verbose Output

Enable detailed logging:

```bash
python -m afterthought --verbose
```

### Auto-Fetch Missing Transcripts

Automatically trigger playback in Podcasts app to download missing transcripts:

```bash
python -m afterthought --fetch-missing
python -m afterthought -c "History of Rome" --fetch-missing
```

When enabled, AfterThought will:
1. Detect episodes without transcripts
2. Open the episode in Apple Podcasts app
3. Play it briefly to trigger transcript download
4. Wait 10 seconds for download
5. Retry processing the episode

This is useful for episodes you've played on iOS that don't have transcripts cached on your Mac yet.

### Combined Options

```bash
python -m afterthought -c "All-In" -d 30 -f -v
python -m afterthought --channel "History" --fetch-missing --verbose
```

## CLI Options

| Option | Short | Description |
|--------|-------|-------------|
| `--channel` | `-c` | Fuzzy match podcast channel name |
| `--days` | `-d` | Episodes played in last N days (default: 7) |
| `--force` | `-f` | Re-process already summarized episodes |
| `--fetch-missing` | | Auto-fetch missing transcripts by triggering playback |
| `--dry-run` | | Show what would be processed without executing |
| `--verbose` | `-v` | Enable verbose output |
| `--stats` | | Show processing statistics and exit |
| `--help` | `-h` | Show help message |

## Output Format

AfterThought creates markdown files organized by podcast channel:

```
~/Documents/Obsidian/Podcasts/
├── All-In Podcast/
│   ├── E150 Tech Trends 2026.md
│   └── E151 AI Regulation Debate.md
├── Lex Fridman Podcast/
│   ├── #123 - Sam Altman OpenAI.md
│   └── #124 - Andrew Huberman Neuroscience.md
└── ...
```

### Markdown File Structure

Each episode summary includes:

**Frontmatter (YAML):**
```yaml
---
type: podcast-summary
episode_title: "Episode Title"
podcast_channel: "Channel Name"
podcast_author: "Author Name"
publish_date: 2026-01-07
last_played: 2026-01-07 10:30:00
generated_date: 2026-01-07 15:45:23
duration: "45:30"
transcript_available: true
transcript_provider: "Apple"
input_tokens: 15234
output_tokens: 523
ai_model: "gemini-2.0-flash-exp"
episode_uuid: "ABC123..."
---
```

**Summary Content:**
- **Overview**: 2-3 sentence high-level summary
- **Key Topics**: Main topics discussed in bullet points
- **Notable Quotes or Insights**: 2-3 interesting highlights
- **Action Items or Takeaways**: Practical advice and conclusions

## Architecture

### Project Structure

```
AfterThought/
├── config.py                      # Pydantic configuration
├── afterthought/
│   ├── cli.py                    # CLI interface (Click)
│   ├── db/
│   │   ├── podcast_db.py         # Apple Podcasts SQLite queries
│   │   └── tracking_db.py        # Processed episodes tracking
│   ├── parsers/
│   │   └── ttml_parser.py        # TTML XML transcript parsing
│   ├── summarizer/
│   │   └── gemini_client.py      # Google Gemini API client
│   ├── output/
│   │   └── markdown_writer.py    # Obsidian markdown generation
│   └── utils/
│       ├── fuzzy_match.py        # Fuzzy string matching
│       ├── date_utils.py         # Date/time utilities
│       └── logging_config.py     # Logging setup
```

### Data Flow

```
Apple Podcasts DB → Filter (date/channel) → Check Tracking DB
                                                     ↓
                                              Not processed?
                                                     ↓
                                        Load TTML → Parse → Summarize (Gemini)
                                                                ↓
                                                    Write Markdown → Update Tracking
```

### Key Technologies

- **Pydantic**: Type-safe configuration with validation
- **Click**: Command-line interface framework
- **Google Gemini**: AI summarization (gemini-2.0-flash-exp)
- **thefuzz**: Fuzzy string matching for channel names
- **SQLite**: Apple Podcasts database (read-only) + tracking database

## Configuration

### Environment Variables

All configuration is managed via `.env` file:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | - | Google Gemini API key |
| `OBSIDIAN_OUTPUT_PATH` | Yes | - | Output directory for markdown files |
| `APPLE_PODCASTS_DB_PATH` | No | Auto-detected | Path to MTLibrary.sqlite |
| `TTML_CACHE_PATH` | No | Auto-detected | Path to TTML transcript cache |
| `TRACKING_DB_PATH` | No | `~/.afterthought/tracking.db` | Tracking database path |
| `GEMINI_MODEL` | No | `gemini-2.0-flash-exp` | Gemini model to use |
| `DEFAULT_DAYS_FILTER` | No | `7` | Default days to look back |
| `PRESERVE_SPEAKERS` | No | `true` | Preserve speaker IDs in transcripts |

### Apple Podcasts Database

AfterThought automatically detects the Apple Podcasts database location:

```
~/Library/Group Containers/[ID].groups.com.apple.podcasts/Documents/MTLibrary.sqlite
```

The `[ID]` varies by system but is auto-detected. The database is opened in **read-only** mode to ensure safety.

### Transcript Cache

TTML transcript files are cached by Apple Podcasts at:

```
~/Library/Group Containers/[ID].groups.com.apple.podcasts/Library/Cache/Assets/TTML/
```

**Note:** Only ~64% of episodes have transcripts available. Episodes without transcripts will be skipped.

## Troubleshooting

### "Could not auto-detect Apple Podcasts database"

**Solution:** Manually set the path in `.env`:

```bash
APPLE_PODCASTS_DB_PATH=~/Library/Group\ Containers/243LU875E5.groups.com.apple.podcasts/Documents/MTLibrary.sqlite
```

Find your actual path:
```bash
ls ~/Library/Group\ Containers/ | grep podcasts
```

### "Invalid API key"

**Solution:**
1. Get a new API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Update `.env` file with the new key
3. Ensure there are no quotes or spaces around the key

### "No transcript available"

**Cause:** Not all podcast episodes have transcripts. About 36% of episodes lack transcript data.

**Solution:** This is normal. The tool will skip these episodes and continue processing others.

### "Transcript file not found"

**Cause:** The transcript hasn't been downloaded by Apple Podcasts yet.

**Solution:** Play the episode for a few seconds in Apple Podcasts to trigger transcript download, then run AfterThought again.

### "Gemini API rate limit exceeded"

**Solution:** AfterThought includes automatic retry with exponential backoff. If rate limits persist:
- Wait a few minutes between runs
- Process fewer episodes at once (use `--days 1`)
- Check your API quota at [Google AI Studio](https://aistudio.google.com/)

### Permission Errors

**Solution:** Ensure AfterThought has permission to:
- Read Apple Podcasts database: `~/Library/Group Containers/...`
- Write to Obsidian directory: Your `OBSIDIAN_OUTPUT_PATH`
- Write tracking database: `~/.afterthought/`

## Development

### Running Tests

```bash
# Install dev dependencies
pip install pytest pytest-cov

# Run tests
pytest tests/
```

### Code Structure

- Each module is independent and testable
- Context managers for database connections
- Type hints throughout for better IDE support
- Pydantic for configuration validation

### Adding Custom Prompts

Edit `afterthought/summarizer/gemini_client.py` and modify `DEFAULT_PROMPT_TEMPLATE` to customize the summarization style.

## FAQ

### Q: Does this work with other podcast apps?

**A:** Currently only Apple Podcasts is supported, as it provides word-level TTML transcripts. Support for other apps would require different transcript sources.

### Q: Can I use a different AI model?

**A:** Yes! Set `GEMINI_MODEL` in your `.env` to any supported Gemini model:
- `gemini-2.0-flash-exp` (default, fast and cheap)
- `gemini-1.5-pro` (more capable, higher cost)
- `gemini-1.5-flash` (balanced)

### Q: How much does Gemini API cost?

**A:** Gemini 2.0 Flash has a generous free tier:
- 1,500 requests per day (free)
- ~4M tokens per day (free)

For most users, AfterThought stays within free limits.

### Q: Can I export to formats other than Markdown?

**A:** Currently only Markdown is supported. The Markdown files are plain text and can be easily converted to other formats using tools like Pandoc.

### Q: Does this modify my Apple Podcasts data?

**A:** No. AfterThought opens the Apple Podcasts database in **read-only** mode. It never modifies your podcast library.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Apple Podcasts for providing high-quality TTML transcripts
- Google Gemini for powerful AI summarization
- The Python community for excellent libraries

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/AfterThought/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/AfterThought/discussions)

## Changelog

### v0.1.0 (2026-01-07)
- Initial release
- Core functionality: discovery, parsing, summarization, markdown output
- Support for fuzzy channel matching
- Tracking database to avoid re-processing
- CLI with multiple options
- Comprehensive documentation

---

**Built with ❤️ for podcast enthusiasts who love taking notes**
