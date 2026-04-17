def summarise_text(text: str, max_sentences: int = 5) -> str:
    """Extractive summariser using simple term-frequency sentence scoring."""

    if not text or not text.strip():
        return ''

    import re

    stopwords = {
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has',
        'he', 'in', 'is', 'it', 'its', 'of', 'on', 'or', 'that', 'the', 'to',
        'was', 'were', 'will', 'with', 'this', 'these', 'those', 'their', 'they',
        'his', 'her', 'them', 'also', 'into', 'which', 'who', 'what', 'when',
    }

    raw_sentences = [
        s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+', text.strip()) if s.strip()
    ]
    sentences = []
    for sentence in raw_sentences:
        cleaned = re.sub(r'(?i)^source\s+\d+:\s*', '', sentence).strip()
        if len(cleaned) >= 25:
            sentences.append(cleaned)

    if not sentences:
        return ''

    frequencies: dict[str, int] = {}
    tokenized_sentences: list[list[str]] = []
    for sentence in sentences:
        words = re.findall(r"[a-zA-Z']+", sentence.lower())
        filtered = [w for w in words if w not in stopwords and len(w) > 2]
        tokenized_sentences.append(filtered)
        for word in filtered:
            frequencies[word] = frequencies.get(word, 0) + 1

    if not frequencies:
        selected = sentences[:max_sentences]
        return '\n'.join(f'- {s}' for s in selected)

    scores: list[tuple[float, int, str]] = []
    for idx, sentence in enumerate(sentences):
        words = tokenized_sentences[idx]
        if not words:
            continue
        score = sum(frequencies[w] for w in words) / len(words)
        scores.append((score, idx, sentence))

    if not scores:
        selected = sentences[:max_sentences]
    else:
        top = sorted(scores, key=lambda x: x[0], reverse=True)[:max_sentences]
        top_sorted = sorted(top, key=lambda x: x[1])
        selected = [s for _, _, s in top_sorted]

    def is_similar(a: str, b: str) -> bool:
        a_words = set(re.findall(r"[a-zA-Z']+", a.lower()))
        b_words = set(re.findall(r"[a-zA-Z']+", b.lower()))
        if not a_words or not b_words:
            return False
        overlap = len(a_words & b_words) / min(len(a_words), len(b_words))
        return overlap >= 0.75

    unique_selected = []
    seen = set()
    for sentence in selected:
        key = sentence.lower()
        if key in seen:
            continue
        if any(is_similar(sentence, existing) for existing in unique_selected):
            continue
        seen.add(key)
        unique_selected.append(sentence)

    return '\n'.join(f'- {sentence}' for sentence in unique_selected)
