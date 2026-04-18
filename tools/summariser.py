import re
from typing import Callable

MAX_WORDS_PER_BULLET = 22
RETRY_INPUT_CHAR_LIMIT = 6000

def _clean_text_fragment(text : str) -> str:
    """
    Clean a text fragment by removing source labels, reference markers, and excessive whitespace.

    Args:
        text (str): The text fragment to clean.

    Returns:
        str: The cleaned text fragment.
    """    
    
    cleaned = re.sub(r'(?i)^source\s+\d+:\s*', '', text).strip()
    cleaned = re.sub(r'\[[0-9,\s]+\]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip(' -')

def _is_meta_line(text : str) -> bool:
    """
    Check if a text line is a meta line (e.g., summary, key points).

    Args:
        text (str): The text line to check.

    Returns:
        bool: True if the line is a meta line, False otherwise.
    """    
    
    line = text.strip().strip('-*• ').strip()
    if not line:
        return True

    if re.match(r'(?i)^(here|below)\s+(are|is)\b', line):
        return True
    if re.match(r'(?i)^(summary|key\s*-?points?|rewritten\s+notes?)\b', line):
        return True
    if re.match(r'(?i)^these\s+points\b', line):
        return True
    if line.endswith(':') and len(line.split()) <= 10:
        return True

    return False

def _is_source_commentary_line(text : str) -> bool:
    """
    Check if a text line is a source commentary line (e.g., mentions sources or articles).

    Args:
        text (str): The text line to check.

    Returns:
        bool: True if the line is a source commentary line, False otherwise.
    """    
    
    line = text.lower()
    patterns = (
        r'\b(this|that|another|the)\s+(source|article|biography|book|page)\b',
        r'^\s*(one|two|three|several|multiple)\s+(sources|articles|biographies|books)\b',
        r'\b(sources?|articles?|biographies|books)\s+(say|state|cover|offer|provide|examine|discuss|compare)\b',
        r'\bbiograph(?:y|ies)\s+(covers|examines|describes|offers|compares)\b',
        r'\baccording\s+to\s+(the\s+)?(source|article|biography|book)\b',
    )
    return any(re.search(pattern, line) for pattern in patterns)

def _clip_words(text : str, max_words : int) -> str:
    """
    Clip a text fragment to a maximum number of words, adding an ellipsis if it exceeds the limit.

    Args:
        text (str): The text fragment to clip.
        max_words (int): The maximum number of words to include.

    Returns:
        str: The clipped text fragment.
    """    
    
    words = text.split()
    if len(words) <= max_words:
        return text
    return ' '.join(words[:max_words]).rstrip('.,;:') + '...'

def _extract_candidate_sentences(text : str) -> list[str]:
    """
    Extract candidate sentences from a text fragment by splitting on punctuation and newlines, while filtering out short or meta lines.

    Args:
        text (str): The text fragment to process.

    Returns:
        list[str]: A list of candidate sentences.
    """    
    
    candidates = []
    parts = re.split(r'(?<=[.!?])\s+|\n+', text.strip())
    for part in parts:
        cleaned = _clean_text_fragment(part)
        if len(cleaned) < 25:
            continue
        if _is_meta_line(cleaned):
            continue
        candidates.append(cleaned)
    return candidates

def _normalise_similarity_tokens(text : str) -> set[str]:
    """
    Normalise the tokens in a text string for similarity comparison.

    Args:
        text (str): The text string to normalise.

    Returns:
        set[str]: A set of normalised tokens.
    """
    
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9']+", text.lower())
        if len(token) > 2
    }

def _is_similar_sentence(left : str, right : str) -> bool:
    """
    Determine if two sentences are similar based on cleaned text and token overlap.

    Args:
        left (str): The first sentence to compare.
        right (str): The second sentence to compare.

    Returns:
        bool: True if the sentences are similar, False otherwise.
    """    
    
    left_clean = re.sub(r'[^a-z0-9 ]', '', left.lower()).strip()
    right_clean = re.sub(r'[^a-z0-9 ]', '', right.lower()).strip()
    if not left_clean or not right_clean:
        return False
    if left_clean == right_clean:
        return True

    if (left_clean in right_clean or right_clean in left_clean) and min(len(left_clean), len(right_clean)) >= 25:
        return True

    left_tokens = _normalise_similarity_tokens(left_clean)
    right_tokens = _normalise_similarity_tokens(right_clean)
    if not left_tokens or not right_tokens:
        return False

    overlap = len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))
    return overlap >= 0.8

def _trim_text_for_retry(text : str, max_chars : int = RETRY_INPUT_CHAR_LIMIT) -> str:
    """
    Trim a text string to a maximum number of characters, attempting to preserve whole sentences and adding a truncation notice if necessary.

    Args:
        text (str): The text string to trim.
        max_chars (int, optional): The maximum number of characters to include. Defaults to RETRY_INPUT_CHAR_LIMIT.

    Returns:
        str: The trimmed text string.
    """    
    
    stripped = text.strip()
    if len(stripped) <= max_chars:
        return stripped

    clipped = stripped[:max_chars]
    sentence_break = max(clipped.rfind('\n'), clipped.rfind('. '))
    if sentence_break > max_chars // 2:
        clipped = clipped[:sentence_break + 1]

    return clipped.strip() + '\n\n[truncated for faster summarisation]'

def _fallback_summary(text : str, max_sentences : int) -> str:
    """
    Generate a fallback summary by extracting candidate sentences and normalising them into bullet points, ensuring a concise output even when the LLM summarisation fails.

    Args:
        text (str): The text to summarise.
        max_sentences (int): The maximum number of sentences to include in the summary.

    Returns:
        str: The fallback summary.
    """    
    
    lines: list[str] = []
    seen: set[str] = set()

    for sentence in _extract_candidate_sentences(text):
        key = re.sub(r'[^a-z0-9 ]', '', sentence.lower())
        if key in seen:
            continue
        seen.add(key)
        lines.append(_clip_words(sentence, MAX_WORDS_PER_BULLET))
        if len(lines) >= max_sentences:
            break

    return '\n'.join(f'- {line}' for line in lines)

def _extract_chat_content(response : dict | None) -> str:
    """
    Extract the content from an Ollama chat response, handling cases where the response may be None or not in the expected format.

    Args:
        response (dict | None): The Ollama chat response to extract content from.

    Returns:
        str: The extracted content, or an empty string if the response is invalid.
    """    
    
    if not response or not isinstance(response, dict):
        return ''
    return str(response.get('message', {}).get('content', '')).strip()

def _normalise_to_bullets(text : str, max_sentences : int) -> str:
    """
    Normalise a text string into bullet points by extracting lines, filtering out meta and commentary lines, and ensuring uniqueness and brevity.

    Args:
        text (str): The text string to normalise.
        max_sentences (int): The maximum number of sentences to include in the summary.

    Returns:
        str: The normalised text as bullet points.
    """    
    
    if not text or not text.strip():
        return ''

    explicit_bullets: list[str] = []
    plain_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if _is_meta_line(line):
            continue

        has_bullet_marker = bool(re.match(r'^\s*(?:[-*•]|\d+[.)])\s+', line))
        line = re.sub(r'^\s*(?:[-*•]|\d+[.)])\s+', '', line)
        line = _clean_text_fragment(line)
        if not line or _is_meta_line(line) or _is_source_commentary_line(line):
            continue

        if has_bullet_marker:
            explicit_bullets.append(line)
        else:
            plain_lines.append(line)

    lines = explicit_bullets if explicit_bullets else plain_lines

    if not lines:
        lines = _extract_candidate_sentences(text)

    if len(lines) == 1 and len(lines[0].split()) > MAX_WORDS_PER_BULLET * 2:
        split_lines = [
            _clean_text_fragment(p)
            for p in re.split(r'(?<=[.;])\s+', lines[0])
            if _clean_text_fragment(p)
        ]
        if split_lines:
            lines = split_lines

    unique: list[str] = []
    seen: set[str] = set()
    for line in lines:
        if _is_source_commentary_line(line):
            continue
        key = re.sub(r'[^a-z0-9 ]', '', line.lower())
        if key in seen:
            continue
        if any(_is_similar_sentence(line, existing) for existing in unique):
            continue
        seen.add(key)
        unique.append(_clip_words(line, MAX_WORDS_PER_BULLET))
        if len(unique) >= max_sentences:
            break

    return '\n'.join(f'- {line}' for line in unique)

def _needs_compression_retry(text: str, max_sentences: int) -> bool:
    """
    Determine if a retry with compression is needed based on the presence of bullet markers and the overall word count, which can indicate that the initial summary is too verbose or not properly formatted.

    Args:
        text (str): The text string to evaluate.
        max_sentences (int): The maximum number of sentences to include in the summary.

    Returns:
        bool: True if a retry with compression is needed, False otherwise.
    """    
    
    if not text or not text.strip():
        return True

    bullet_lines = [
        line for line in text.splitlines()
        if re.match(r'^\s*(?:[-*•]|\d+[.)])\s+', line)
    ]
    word_count = len(re.findall(r"[a-zA-Z0-9']+", text))

    if len(bullet_lines) < 2:
        return True
    if word_count > max_sentences * 35:
        return True
    return False

def summarise_text(
    text : str,
    chat : Callable[[list[dict]], dict | None],
    max_sentences : int = 5,
    system_prompt : str | None = None,
) -> str:
    """
    Summarise a text string into concise bullet points using an Ollama chat function, with fallback mechanisms to ensure a summary is produced even if the LLM fails to generate a suitable output.

    Args:
        text (str): The text to summarise.
        chat (Callable[[list[dict]], dict  |  None]): The chat function to use for summarisation.
        max_sentences (int, optional): The maximum number of sentences to include in the summary. Defaults to 5.
        system_prompt (str | None, optional): The system prompt to use for the chat function. Defaults to None.

    Raises:
        TypeError: If the chat function is not callable.

    Returns:
        str: The summarised text in bullet point format.
    """    
    
    if not text or not text.strip():
        return ''
    if not callable(chat):
        raise TypeError('chat must be a callable that accepts messages and returns an Ollama response dict.')

    max_sentences = max(1, max_sentences)
    raw_text = text.strip()

    prompt = system_prompt or (
        'You are a research summarisation expert. '
        'Condense the provided text into clear, concise bullet points.'
    )
    prompt = (
        f'{prompt}\n\n'
        'Strict output rules:\n'
        f'- Return ONLY 3 to {max_sentences} bullet points.\n'
        '- Start every line with "- ".\n'
        '- Each bullet must contain one key point only.\n'
        f'- Keep each bullet to <= {MAX_WORDS_PER_BULLET} words.\n'
        '- No intro, no conclusion, no markdown headings, and no paragraphs.\n'
        '- Do not include lead-in text like "Here are the key points".'
    )

    messages = [
        {'role': 'system', 'content': prompt},
        {'role': 'user', 'content': (
            'Summarise the following raw research notes. '
            'Highlight only the most important factual points and remove minor details.\n\n'
            f'{raw_text}'
        )}
    ]

    raw_response = chat(messages)
    raw_summary = _extract_chat_content(raw_response)
    normalised = _normalise_to_bullets(raw_summary, max_sentences)
    min_bullets = min(3, max_sentences)
    normalised_count = len([line for line in normalised.splitlines() if line.strip()])
    if normalised and normalised_count >= min_bullets and not _needs_compression_retry(raw_summary, max_sentences):
        return normalised

    if raw_response is None and len(raw_text) <= RETRY_INPUT_CHAR_LIMIT:
        return _fallback_summary(raw_text, max_sentences)

    retry_seed_text = raw_summary or _trim_text_for_retry(raw_text)

    compression_messages = [
        {
            'role': 'system',
            'content': (
                'You compress summaries. Return ONLY concise bullet points. '
                f'Provide 3 to {max_sentences} bullets and keep each bullet <= {MAX_WORDS_PER_BULLET} words.'
                ' Start every line with "- " and never include preamble text.'
            ),
        },
        {
            'role': 'user',
            'content': (
                'Rewrite this into short key-point bullets only:\n\n'
                f'{retry_seed_text}'
            ),
        },
    ]

    retry_response = chat(compression_messages)
    retry_summary = _extract_chat_content(retry_response)
    retry_normalised = _normalise_to_bullets(retry_summary, max_sentences)
    retry_count = len([line for line in retry_normalised.splitlines() if line.strip()])
    if retry_normalised and retry_count >= min_bullets:
        return retry_normalised

    if raw_response is None and retry_response is None:
        return _fallback_summary(raw_text, max_sentences)

    if normalised:
        return normalised

    return _fallback_summary(raw_text, max_sentences)