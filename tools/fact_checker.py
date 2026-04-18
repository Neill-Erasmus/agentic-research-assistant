import re
from typing import Callable


ABSOLUTE_CLAIM_PATTERN = re.compile(
    r'\b(always|never|everyone|nobody|universally|guaranteed|guarantees|proves?|undeniably)\b',
    flags=re.IGNORECASE,
)
NUMERIC_CLAIM_PATTERN = re.compile(
    r'\b\d+(?:\.\d+)?(?:%|\s+percent|\s+million|\s+billion|\s+trillion)\b',
    flags=re.IGNORECASE,
)


def _extract_chat_content(response: dict | None) -> str:
    if not response or not isinstance(response, dict):
        return ''
    return str(response.get('message', {}).get('content', '')).strip()


def _normalise_bullets(text: str) -> str:
    if not text or not text.strip():
        return ''

    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        line = re.sub(r'^\s*(?:[-*•]|\d+[.)])\s*', '', line).strip()
        if not line:
            continue

        lines.append(f'- {line}')

    if lines:
        return '\n'.join(lines)

    sentence_chunks = [chunk.strip() for chunk in re.split(r'(?<=[.!?])\s+', text) if chunk.strip()]
    return '\n'.join(f'- {chunk}' for chunk in sentence_chunks)


def _fallback_fact_check(summary: str) -> str:
    if not summary or not summary.strip():
        return '- No summary provided for fact checking.'

    summary_text = summary.lower()
    concerns: list[str] = []

    if 'summary generation failed' in summary_text:
        concerns.append('Fact-check is limited because summary generation failed; review source snippets directly.')

    if ABSOLUTE_CLAIM_PATTERN.search(summary):
        concerns.append('Contains absolute wording that may overstate certainty and should be verified against primary sources.')

    if NUMERIC_CLAIM_PATTERN.search(summary):
        concerns.append('Includes percentages or numeric claims that should be checked against an original publication or dataset.')

    if not concerns:
        concerns.append('No obvious likely false claims detected from wording alone, but factual verification still requires source-by-source checking.')

    return '\n'.join(f'- {concern}' for concern in concerns)


def fact_check_summary(
    summary: str,
    chat: Callable[[list[dict]], dict | None],
    system_prompt: str | None = None,
) -> str:
    """Ask the model to identify likely false claims in a generated summary."""
    if not summary or not summary.strip():
        return '- No summary provided for fact checking.'
    if not callable(chat):
        raise TypeError('chat must be a callable that accepts messages and returns an Ollama response dict.')

    prompt = system_prompt or (
        'You are a careful fact-checking assistant. '
        'Review a summary and flag any likely false or suspicious claims.'
    )
    prompt = (
        f'{prompt}\n\n'
        'Strict output rules:\n'
        '- Return concise bullet points only.\n'
        '- If concerns exist, list each concern in a separate bullet.\n'
        '- If no concerns exist, return exactly one bullet saying no likely false claims were found.\n'
        '- Do not invent new facts; only assess the provided summary text.'
    )

    messages = [
        {'role': 'system', 'content': prompt},
        {
            'role': 'user',
            'content': (
                'Does this summary contain any likely false claims? List any concerns.\n\n'
                f'Summary:\n{summary.strip()}'
            ),
        },
    ]

    response = chat(messages)
    raw_assessment = _extract_chat_content(response)
    normalised = _normalise_bullets(raw_assessment)
    if normalised:
        return normalised

    if response is None:
        return '- Fact-check model unavailable; using heuristic checks only.\n' + _fallback_fact_check(summary)

    return _fallback_fact_check(summary)
