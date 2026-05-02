# Contributing to Agentic Research Assistant

Thank you for your interest in contributing to the Agentic Research Assistant! We welcome contributions from developers of all skill levels. This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Enhancements](#suggesting-enhancements)
- [Questions or Need Help?](#questions-or-need-help)

## Code of Conduct

This project adheres to a code of conduct that we expect all contributors to follow. By participating, you are expected to:

- Be respectful and inclusive of all participants
- Refrain from harassment, discrimination, or offensive language
- Provide constructive feedback and criticism
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

### Prerequisites

- Python 3.10 or higher
- pip
- Git
- A GitHub account
- Ollama (optional, but recommended for development)
- Docker (optional, for containerized testing)

### Fork and Clone the Repository

1. Fork the repository on GitHub by clicking the "Fork" button
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/agentic-research-assistant.git
   cd agentic-research-assistant
   ```
3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/Neill-Erasmus/agentic-research-assistant.git
   ```

## Development Setup

### 1. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Verify Installation

```bash
python main.py
```

You should see the Research Assistant prompt. Type `quit` to exit.

## Making Changes

### Create a Branch

For each feature or bug fix, create a descriptive branch:

```bash
git checkout -b feature/add-new-agent
# or
git checkout -b fix/search-result-deduplication
```

Use clear, descriptive branch names:
- `feature/` for new features
- `fix/` for bug fixes
- `docs/` for documentation updates
- `refactor/` for code refactoring
- `test/` for test improvements

### Keep Your Branch Updated

Before submitting a pull request, ensure your branch is up-to-date with the main branch:

```bash
git fetch upstream
git rebase upstream/main
```

## Code Standards

### Python Style

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use meaningful variable and function names
- Keep functions focused and single-purpose
- Maintain code readability over brevity

### Docstrings

All modules, classes, and functions should have docstrings following Google-style format:

```python
def search_web(query: str, num_results: int = 5) -> list[dict]:
    """
    Performs a web search for the given query.
    
    Args:
        query: The search query string.
        num_results: Maximum number of results to return (default: 5).
    
    Returns:
        A list of dictionaries containing search results with keys:
        - title: The result title
        - url: The result URL
        - snippet: The result snippet/description
    
    Raises:
        ValueError: If query is empty or None.
    """
    pass
```

### Type Hints

Use type hints for function parameters and return types:

```python
def process_text(content: str, max_length: int = 500) -> str:
    """Process and truncate text."""
    pass

def fetch_sources(query: str) -> list[dict]:
    """Fetch research sources."""
    pass
```

### Comments

- Use comments to explain the "why", not the "what"
- Keep comments up-to-date with code changes
- Use TODO comments for planned improvements:
  ```python
  # TODO: Implement caching for frequently searched topics
  ```

### Imports

- Group imports: standard library, third-party, local
- Use absolute imports
- Remove unused imports

```python
import json
import re
from typing import Optional

import requests

from agents.base_agent import BaseAgent
from tools.web_search import search_web
```

## Testing

### Manual Testing

1. Test your changes with the CLI:
   ```bash
   python main.py
   ```
2. Test with various queries to ensure robustness
3. Test edge cases:
   - Empty queries
   - Very long queries
   - Special characters
   - Non-English text

### Testing with Docker

Test your changes in the Docker environment:

```bash
docker build -t agentic-research-assistant .
docker run -it agentic-research-assistant
```

### Testing with Ollama

If modifying summarization or fact-checking logic:

1. Ensure Ollama is running locally:
   ```bash
   ollama serve
   ```
2. Test with Ollama enabled and disabled to verify fallback behavior

## Submitting Changes

### Before Submitting

1. Verify your code follows the style guidelines
2. Update documentation and README if needed
3. Add or update docstrings
4. Test your changes thoroughly
5. Ensure your branch is up-to-date with `main`

### Create a Pull Request

1. Push your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Open a Pull Request on GitHub:
   - Clear, descriptive title
   - Detailed description of changes
   - Reference any related issues (e.g., "Fixes #42")
   - Screenshots or examples if applicable

### Pull Request Guidelines

Your PR should:

- Have a clear, concise title
- Include a description of what was changed and why
- Reference any related issues
- Include testing information
- Be focused on a single feature or fix
- Have a minimal commit history (consider squashing related commits)

Example PR description:

```markdown
## Description
This PR improves search result deduplication by implementing a fuzzy matching algorithm.

## Type of Change
- [x] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)
- [ ] Breaking change
- [ ] Documentation update

## Testing
- Tested with 50+ unique queries
- Verified deduplication rate improved from 15% to 45%
- Verified no performance regression

## Related Issues
Closes #123
```

### Code Review

- Be open to feedback and suggestions
- Respond to review comments promptly
- Make requested changes in new commits (don't force push after review starts)
- Re-request review after addressing feedback

## Reporting Bugs

### Before Reporting

- Check existing issues to avoid duplicates
- Verify the bug with the latest code
- Try to reproduce the issue consistently

### How to Report

Open an issue on GitHub with:

1. **Clear title**: Summarize the bug in the title
2. **Description**: Explain what you were trying to do
3. **Steps to reproduce**: Detailed steps to reproduce the issue
4. **Expected behavior**: What you expected to happen
5. **Actual behavior**: What actually happened
6. **Environment**:
   - Python version
   - OS (Windows, macOS, Linux)
   - Whether Ollama is enabled/disabled
   - Relevant output or error messages
7. **Screenshots or logs**: If applicable

Example bug report:

```markdown
## Summary
Search fails when query contains special characters

## Steps to Reproduce
1. Run `python main.py`
2. Enter query: "What is AI?"
3. Observe error

## Expected Behavior
Search should handle special characters gracefully

## Actual Behavior
TypeError: unsupported operand type(s) for +: 'str' and 'NoneType'

## Environment
- Python: 3.10.4
- OS: Windows 11
- Ollama: Disabled
```

## Suggesting Enhancements

### Before Suggesting

- Check existing issues for similar suggestions
- Ensure your idea aligns with project goals

### How to Suggest

1. Use a clear, descriptive title
2. Provide a detailed description of the enhancement
3. Explain the motivation and use case
4. Describe how it would work
5. Provide examples if applicable

Example enhancement suggestion:

```markdown
## Summary
Support for saving research reports to PDF format

## Motivation
Currently reports are only displayed in terminal. PDF export would allow:
- Easy sharing with colleagues
- Archive and backup
- Professional formatting

## Proposed Implementation
Add a `--export pdf` flag to save reports in PDF format using reportlab

## Example Usage
python main.py --export pdf --output report.pdf
```

## Questions or Need Help?

- Check the [README](README.md) for documentation
- Review existing issues and discussions
- Open a discussion or issue with your question
- Be respectful and provide context

## Additional Resources

- [Python Style Guide (PEP 8)](https://pep8.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Git Documentation](https://git-scm.com/doc)
- [GitHub Help](https://docs.github.com)