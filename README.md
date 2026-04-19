# Agentic Research Assistant

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Docker Ready](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![LLM Backend](https://img.shields.io/badge/LLM-Ollama-F97316)](https://ollama.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A modular, agent-based CLI assistant that turns a research topic into a structured report with:

- Web search results from multiple sources
- Concise bullet-point summaries
- Lightweight fact-checking cues
- APA-style citations

The system is designed for a local LLM workflow via Ollama and degrades gracefully with deterministic fallbacks when Ollama is unavailable.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Quick Start (Local)](#quick-start-local)
- [Run with Docker](#run-with-docker)
- [Configuration](#configuration)
- [Usage](#usage)
- [How the Pipeline Works](#how-the-pipeline-works)
- [Output Format](#output-format)
- [Reliability and Fallbacks](#reliability-and-fallbacks)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Overview

`ResearchOrchestrator` coordinates specialized agents to process a query end-to-end:

1. Finds relevant sources.
2. Summarizes key facts.
3. Flags potentially risky claims.
4. Formats APA-style citations.

The orchestrator also stores in-process session memory, so follow-up prompts such as "expand the first result" can reference previous outputs during the same runtime.

## Key Features

- Multi-agent orchestration with planner-driven execution order.
- Dependency-aware pipeline enforcement (for example, citation generation when search is used).
- Multi-source web retrieval:
  - Wikipedia API
  - DuckDuckGo Instant Answer API
  - DuckDuckGo HTML results parsing
- Deduplication, relevance ranking, and source-diversity balancing.
- LLM-backed summarization and fact-checking with deterministic fallback behavior.
- APA citation formatting with author inference from metadata and URL domains.
- CLI-based interactive workflow with follow-up query support.

## Project Structure

```text
.
|-- Dockerfile
|-- LICENSE
|-- README.md
|-- main.py
|-- orchestrator.py
|-- requirements.txt
|-- agents/
|   |-- ___init__.py
|   |-- base_agent.py
|   |-- citation_agent.py
|   |-- fact_checker_agent.py
|   |-- search_agent.py
|   `-- summariser_agent.py
`-- tools/
    |-- __init__.py
    |-- citation.py
    |-- fact_checker.py
    |-- summariser.py
    `-- web_search.py
```

## Prerequisites

- Python 3.10+
- pip
- Internet access (for web search sources)
- Optional but recommended: Ollama running locally for stronger summaries/fact-check output
- Optional: Docker (if running containerized)

## Quick Start (Local)

### 1) Clone the repository

```bash
git clone https://github.com/Neill-Erasmus/agentic-research-assistant.git

cd Multi-Agent-Research-Assistant
```

### 2) Create and activate a virtual environment

Windows (CMD):

```bat
python -m venv venv
venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

### 4) Start Ollama and pull model

```bash
ollama serve
ollama pull llama3
```

If Ollama is unavailable, the assistant still runs with fallback summarization and fact-check heuristics.

### 5) Run the application

```bash
python main.py
```

Expected startup:

```text
=== Research Assistant ===
Type a research topic and press Enter.
Type "quit" to exit.
```

## Run with Docker

The Docker image packages this application only. Ollama should run separately (typically on the host machine or another service).

### 1) Build image

```bash
docker build -t multi-agent-research-assistant .
```

### 2) Run container (Docker Desktop on Windows/macOS)

Use `host.docker.internal` so the container can reach host Ollama:

```bash
docker run --rm -it -e OLLAMA_URL=http://host.docker.internal:11434/api/chat -e OLLAMA_MODEL=llama3 multi-agent-research-assistant
```

### 3) Run container (Linux)

```bash
docker run --rm -it --add-host=host.docker.internal:host-gateway -e OLLAMA_URL=http://host.docker.internal:11434/api/chat -e OLLAMA_MODEL=llama3 multi-agent-research-assistant
```

### 4) Run without Ollama

```bash
docker run --rm -it multi-agent-research-assistant
```

This still works, but summary and fact-check quality may be lower due to fallback mode.

## Configuration

Configuration is environment-variable driven.

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_URL` | `http://localhost:11434/api/chat` | Ollama chat endpoint |
| `OLLAMA_MODEL` | `llama3` | Model name sent to Ollama |
| `OLLAMA_TIMEOUT_SECONDS` | `180` | Request timeout in seconds (minimum enforced: 15) |
| `OLLAMA_TIMEOUT` | `unset` | Backward-compatible timeout fallback when `OLLAMA_TIMEOUT_SECONDS` is not set |

Example (Windows CMD):

```bat
set OLLAMA_URL=http://localhost:11434/api/chat
set OLLAMA_MODEL=llama3
set OLLAMA_TIMEOUT_SECONDS=240
python main.py
```

## Usage

Run the CLI and enter a research prompt:

```text
Research topic: Albert Einstein main works
```

Useful prompt patterns:

- Broad topic: `Research renewable energy storage trends`
- Person-centric: `Who was Ada Lovelace and what were her main works?`
- Follow-up in same session: `Expand on the second result`
- Follow-up by index: `Use source number 1 and summarize again`

## How the Pipeline Works

### Orchestrator

`ResearchOrchestrator` handles planning, dependency enforcement, session memory, and final report assembly.

### Agent Responsibilities

| Agent | Responsibility | Input | Output |
|---|---|---|---|
| `SearchAgent` | Query normalization + web retrieval | User query | Search result list |
| `SummariserAgent` | Bullet summary generation | Aggregated snippets | Concise bullets |
| `FactCheckerAgent` | Risk-oriented claim review | Summary text | Concern bullets |
| `CitationAgent` | APA citation formatting | Search results | Citation list |

### Tool Layer

- `web_search(query, max_results=8)`
  - Aggregates multiple providers, deduplicates, relevance-ranks, and balances source diversity.
- `summarise_text(text, chat, max_sentences=...)`
  - Uses LLM with strict bullet normalization and deterministic fallback extraction.
- `fact_check_summary(summary, chat, ...)`
  - Uses LLM when available and heuristic checks for absolute/numeric claim risk otherwise.
- `format_citation(url, title, author=None)`
  - Formats APA-like references with inferred author/org fallbacks.

## Output Format

The CLI returns a structured plain-text report:

```text
RESEARCH REPORT
Query: <original query>
==================================================

AGENT PLAN
------------------------------
<executed agents>

SUMMARY
------------------------------
<bullets>

FACT CHECK
------------------------------
<bullets>

SOURCES
------------------------------
[1] <citation>
[2] <citation>
...
```

## Reliability and Fallbacks

- Planner parse failures revert to the default safe pipeline.
- Source-level search failures are handled independently to keep other sources available.
- Summarization uses:
  - primary LLM call
  - compression retry when output quality is poor
  - deterministic extraction fallback when LLM is unavailable
- Fact checking uses:
  - primary LLM call
  - heuristic fallback checks if model output is missing/unavailable
- Step-level exceptions are handled to avoid hard CLI crashes and return readable errors.

## Troubleshooting

- Ollama connection errors from container:
  - Ensure `OLLAMA_URL` points to `http://host.docker.internal:11434/api/chat` when using Docker Desktop.
  - Ensure Ollama is running on the host (`ollama serve`).
- Empty or weak search output:
  - Confirm internet connectivity.
  - Try a clearer query phrase with specific keywords.
- Slow LLM responses:
  - Increase `OLLAMA_TIMEOUT_SECONDS`.
  - Try a smaller/faster local model.
- No citations generated:
  - Ensure search returns results first; citation generation depends on search output.

## License

This project is licensed under the MIT License.
See [LICENSE](LICENSE) for full text.