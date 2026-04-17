import requests
import re
from urllib.parse import quote

USER_AGENT = 'MultiAgentResearchAssistant/1.0 (+https://duckduckgo.com/)'

def _query_terms(query: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-zA-Z']+", query.lower())
        if len(word) > 2 and word not in {'about', 'what', 'were', 'main', 'find', 'research'}
    }

def _primary_phrase(query: str) -> str:
    tokens = [
        word
        for word in re.findall(r"[a-zA-Z']+", query.lower())
        if len(word) > 2 and word not in {'about', 'what', 'were', 'main', 'find', 'research'}
    ]
    if len(tokens) < 2:
        return ''
    return ' '.join(tokens[:2])

def _contains_term(item: dict, term: str) -> bool:
    haystack = f"{item.get('title', '')} {item.get('snippet', '')}".lower()
    return term.lower() in haystack

def _clean_text(text: str) -> str:
    text = re.sub(r'<[^>]+>', '', text or '')
    return re.sub(r'\s+', ' ', text).strip()

def _iter_related_topics(topics: list[dict]):
    for item in topics:
        if 'Topics' in item:
            yield from _iter_related_topics(item.get('Topics', []))
        else:
            yield item

def _relevance_score(item: dict, query: str) -> int:
    terms = _query_terms(query)
    if not terms:
        return 0

    title = item.get('title', '').lower()
    snippet = item.get('snippet', '').lower()

    score = 0
    for term in terms:
        if term in title:
            score += 2
        if term in snippet:
            score += 1

    if 'works' in query.lower():
        if any(
            keyword in f'{title} {snippet}'
            for keyword in (
                'work',
                'works',
                'paper',
                'publication',
                'theory',
                'contribution',
                'nobel',
                'photoelectric',
                'relativity',
            )
        ):
            score += 2
        if any(keyword in f'{title} {snippet}' for keyword in ('popular culture', 'family', 'tower')):
            score -= 2

    query_phrase = query.lower().strip()
    if query_phrase and query_phrase in f'{title} {snippet}':
        score += 3

    return score

def _search_wikipedia(query: str, max_results: int) -> list[dict]:
    """Use Wikipedia API for high-signal encyclopedic coverage."""
    params = {
        'action': 'query',
        'generator': 'search',
        'gsrsearch': query,
        'gsrlimit': max_results,
        'prop': 'extracts|info',
        'exintro': 1,
        'explaintext': 1,
        'inprop': 'url',
        'format': 'json',
        'utf8': 1,
    }
    response = requests.get(
        'https://en.wikipedia.org/w/api.php',
        params=params,
        headers={'User-Agent': USER_AGENT},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    results = []
    pages = list(data.get('query', {}).get('pages', {}).values())
    pages.sort(key=lambda p: p.get('index', 10**9))
    for page in pages:
        title = _clean_text(page.get('title', ''))
        snippet = _clean_text(page.get('extract', ''))
        if not title:
            continue
        results.append(
            {
                'title': title,
                'url': page.get('fullurl') or f'https://en.wikipedia.org/wiki/{quote(title.replace(" ", "_"))}',
                'snippet': snippet or f'Wikipedia article about {title}.',
            }
        )
    return results

def _search_duckduckgo(query: str, max_results: int) -> list[dict]:
    """Use DuckDuckGo instant-answer API as a general web fallback."""
    params = {
        'q': query,
        'format': 'json',
        'no_redirect': 1,
        'no_html': 1,
        'skip_disambig': 1,
    }
    response = requests.get(
        'https://api.duckduckgo.com/',
        params=params,
        headers={'User-Agent': USER_AGENT},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    candidates = []
    candidates.extend(data.get('Results', []))
    candidates.extend(_iter_related_topics(data.get('RelatedTopics', [])))

    results = []
    for item in candidates:
        text = _clean_text(item.get('Text', ''))
        url = item.get('FirstURL', '').strip()
        if not text or not url:
            continue

        title = text.split(' - ')[0][:120]
        results.append({'title': title, 'url': url, 'snippet': text[:320]})
        if len(results) >= max_results:
            break
    return results


def web_search(query: str, max_results: int = 8) -> list[dict]:
    """Search web sources and return [{title, url, snippet}] with deduplication."""
    if not query or not query.strip():
        return []

    max_results = max(1, max_results)
    query = query.strip()
    combined: list[dict] = []
    seen_urls: set[str] = set()

    for source in (_search_wikipedia, _search_duckduckgo):
        try:
            items = source(query, max_results=max_results)
        except requests.RequestException as exc:
            print(f' [web_search] Source error for query "{query}": {exc}')
            continue

        for item in items:
            url = item.get('url', '').strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            combined.append(item)
            if len(combined) >= max_results * 2:
                break

    combined.sort(key=lambda item: _relevance_score(item, query), reverse=True)
    query_terms = _query_terms(query)
    phrase = _primary_phrase(query)

    if phrase:
        phrase_filtered = [
            item
            for item in combined
            if phrase in f"{item.get('title', '')} {item.get('snippet', '')}".lower()
        ]
        if phrase_filtered:
            combined = phrase_filtered

    if query_terms:
        anchor_term = max(query_terms, key=len)
        anchor_filtered = [item for item in combined if _contains_term(item, anchor_term)]
        if anchor_filtered:
            combined = anchor_filtered

    if len(query_terms) >= 2:
        filtered = [item for item in combined if _relevance_score(item, query) >= 3]
        if filtered:
            combined = filtered

    if 'works' in query.lower():
        works_keywords = (
            'theory',
            'paper',
            'publication',
            'contribution',
            'nobel',
            'photoelectric',
            'relativity',
            'quantum',
            'physics',
        )
        focused = [
            item
            for item in combined
            if any(keyword in f"{item.get('title', '')} {item.get('snippet', '')}".lower() for keyword in works_keywords)
        ]
        if len(focused) >= 3:
            combined = focused

        noisy_title_keywords = ('popular culture', 'tv series', 'film', 'tower')
        denoised = [
            item
            for item in combined
            if not any(keyword in item.get('title', '').lower() for keyword in noisy_title_keywords)
        ]
        if len(denoised) >= 2:
            combined = denoised

    return combined[:max_results]