# Support Triage Agent CLI

A powerful terminal-based Python agent designed for hackathons to triage support tickets from multiple companies (HackerRank, Claude, Visa) using LLMs and semantic search.

## Features

- **Multi-Source Scraping**: Automated crawling of support documentation from HackerRank, Claude, and Visa.
- **Semantic Retrieval**: Powered by `sentence-transformers` and `FAISS` for high-precision document grounding.
- **Intelligent Triage**: Claude-powered categorization and response generation with strict escalation logic for security and sensitive issues.
- **Fast Mode**: Keyword-based fallback for rapid testing without heavy model loading.
- **Rich CLI**: Beautiful terminal output with progress bars, status highlights, and summary reports.

## Project Structure

```text
support_agent/
├── code/
│   ├── main.py              # CLI entry point
│   ├── scraper.py           # Web scraper for support docs
│   ├── retriever.py         # Semantic search engine (FAISS)
│   ├── agent.py             # Triage logic (Claude API)
│   ├── logger.py            # Detailed interaction logging
│   └── requirements.txt
├── data/
│   └── corpus/              # Scraped content and search indices
└── support_issues/
    ├── support_issues.csv   # Input tickets
    └── output.csv           # Structured triage results
```

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r support_agent/code/requirements.txt
   ```

2. **Configure Environment**:
   Create a `.env` file in `support_agent/code/` and add your Anthropic API key:
   ```text
   ANTHROPIC_API_KEY=your_key_here
   ```

## Usage

### 1. Build the Corpus
Scrape the support sites to build the knowledge base:
```bash
python support_agent/code/main.py scrape
```

### 2. Run Triage
Process your support issues:
```bash
python support_agent/code/main.py run \
  --input support_agent/support_issues/support_issues.csv \
  --output support_agent/support_issues/output.csv
```

### 3. Fast Mode (Testing)
To run without loading the heavy semantic model (uses keyword search):
```bash
python support_agent/code/main.py run \
  --input ... --output ... --fast
```

## Triage Logic
The agent automatically escalates cases involving:
- Security breaches or locked accounts
- Financial disputes or chargebacks
- Legal/Privacy requests (GDPR, etc.)
- Cheating or plagiarism
- Threats or abuse
