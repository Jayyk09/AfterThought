# AfterThought

**Podcast Summarization Tool for Apple Podcasts**

AfterThought automatically extracts transcripts from Apple Podcasts, generates AI-powered summaries using Google Gemini, and outputs beautifully formatted Obsidian-compatible markdown files organized by podcast channel.

## Features

- 📊 **Smart Episode Discovery**: Automatically finds recently listened podcast episodes from Apple Podcasts
- 🎯 **Fuzzy Channel Matching**: Filter by podcast channel name with intelligent fuzzy matching
- 🤖 **AI Summarization**: Leverages Google Gemini API for high-quality episode summaries
- 📝 **Obsidian Integration**: Creates markdown files with frontmatter, organized by channel
- 🔍 **Tracking**: Avoids re-processing episodes you've already summarized
- ⚡ **Incremental Processing**: Run regularly to keep your podcast notes up-to-date

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure:**
   ```bash
   cp .env.example .env
   # Edit .env and add your GEMINI_API_KEY and OBSIDIAN_OUTPUT_PATH
   ```

3. **Run:**
   ```bash
   python -m afterthought.cli
   ```

## Project Status

🚧 **In Development** - This project is currently under active development. Core functionality is being implemented in incremental commits.

## Requirements

- Python 3.8+
- macOS (for Apple Podcasts database access)
- Google Gemini API key ([Get one here](https://aistudio.google.com/app/apikey))
- Obsidian (optional, but recommended for viewing summaries)

## License

MIT
