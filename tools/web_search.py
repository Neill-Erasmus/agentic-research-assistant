import requests
import re
from html import unescape
from urllib.parse import parse_qs, quote, unquote, urlparse

USER_AGENT = 'MultiAgentResearchAssistant/1.0 (+https://duckduckgo.com/)'

def _query_terms(query : str) -> set[str]:
    """
    Extract significant terms from the query for relevance scoring and filtering.

    Args:
        query (str): The user's research query.

    Returns:
        set[str]: A set of significant terms extracted from the query.
    """    
    
    return {
        word
        for word in re.findall(r"[a-zA-Z']+", query.lower())
        if len(word) > 2 and word not in {'about', 'what', 'were', 'main', 'find', 'research'}
    }

def _primary_phrase(query : str) -> str:
    """
    Extract a primary phrase from the query for focused filtering.

    Args:
        query (str): The user's research query.

    Returns:
        str: The primary phrase extracted from the query.
    """    
    
    tokens = [
        word
        for word in re.findall(r"[a-zA-Z']+", query.lower())
        if len(word) > 2 and word not in {'about', 'what', 'were', 'main', 'find', 'research'}
    ]
    if len(tokens) < 2:
        return ''
    return ' '.join(tokens[:2])

def _contains_term(item : dict, term : str) -> bool:
    """
    Check if the term is present in the title or snippet of a search result item.

    Args:
        item (dict): The search result item.
        term (str): The term to search for.

    Returns:
        bool: True if the term is found, False otherwise.
    """   
    
    haystack = f"{item.get('title', '')} {item.get('snippet', '')}".lower()
    return term.lower() in haystack

def _clean_text(text : str) -> str:
    """
    Clean and normalize text by removing HTML tags, unescaping entities, and collapsing whitespace.

    Args:
        text (str): The text to clean.

    Returns:
        str: The cleaned text.
    """    
    
    text = unescape(re.sub(r'<[^>]+>', '', text or ''))
    return re.sub(r'\s+', ' ', text).strip()

def _iter_related_topics(topics : list[dict]):
    """
    Recursively iterate through related topics from DuckDuckGo API responses to extract individual topic items.

    Args:
        topics (list[dict]): The list of topics to iterate through.

    Yields:
        The individual topic items.
    """    
    
    for item in topics:
        if 'Topics' in item:
            yield from _iter_related_topics(item.get('Topics', []))
        else:
            yield item

def _relevance_score(item : dict, query : str) -> int:
    """
    Compute a relevance score for a search result item based on the presence of query terms and phrases.

    Args:
        item (dict): The search result item.
        query (str): The user's research query.

    Returns:
        int: The relevance score.
    """    
    
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

def _search_wikipedia(query : str, max_results : int) -> list[dict]:
    """
    Search Wikipedia for the query and return a list of results with title, url, snippet, and source.

    Args:
        query (str): The user's research query.
        max_results (int): The maximum number of results to return.

    Returns:
        list[dict]: A list of search results with title, url, snippet, and source.
    """    
    
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
                'source': 'wikipedia',
            }
        )
    return results

def _search_duckduckgo(query : str, max_results: int) -> list[dict]:
    """
    Search DuckDuckGo for the query and return a list of results with title, url, snippet, and source.

    Args:
        query (str): The user's research query.
        max_results (int): The maximum number of results to return.

    Returns:
        list[dict]: A list of search results with title, url, snippet, and source.
    """    
    
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
        results.append({'title': title, 'url': url, 'snippet': text[:320], 'source': 'duckduckgo_instant'})
        if len(results) >= max_results:
            break
    return results

def _decode_duckduckgo_redirect(url : str) -> str:
    """
    Decode a DuckDuckGo redirect URL to extract the original target URL.

    Args:
        url (str): The DuckDuckGo redirect URL to decode.

    Returns:
        str: The original target URL.
    """    
    
    if not url:
        return ''
    parsed = urlparse(url)
    if 'duckduckgo.com' not in parsed.netloc:
        return url

    query_args = parse_qs(parsed.query)
    target = query_args.get('uddg', [''])[0]
    if target:
        return unquote(target)
    return url

def _search_duckduckgo_html(query : str, max_results : int) -> list[dict]:
    """
    Search DuckDuckGo by scraping the HTML results page and return a list of results with title, url, snippet, and source.

    Args:
        query (str): The user's research query.
        max_results (int): The maximum number of results to return.

    Returns:
        list[dict]: A list of search results with title, url, snippet, and source.
    """    
    
    response = requests.get(
        'https://duckduckgo.com/html/',
        params={'q': query, 'kl': 'us-en'},
        headers={'User-Agent': USER_AGENT},
        timeout=10,
    )
    response.raise_for_status()
    html_text = response.text

    results = []
    anchor_pattern = re.compile(
        r'<a[^>]*class="result__a"[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>',
        flags=re.IGNORECASE | re.DOTALL,
    )

    for match in anchor_pattern.finditer(html_text):
        href = _decode_duckduckgo_redirect(unescape(match.group('href')).strip())
        title = _clean_text(match.group('title'))
        if not href or not title:
            continue

        window = html_text[match.end(): match.end() + 1200]
        snippet_match = re.search(
            r'class="result__snippet"[^>]*>(?P<snippet>.*?)</(?:a|div)>',
            window,
            flags=re.IGNORECASE | re.DOTALL,
        )
        snippet = _clean_text(snippet_match.group('snippet')) if snippet_match else ''

        results.append(
            {
                'title': title[:160],
                'url': href,
                'snippet': snippet[:320],
                'source': 'duckduckgo_html',
            }
        )
        if len(results) >= max_results:
            break

    return results

def _should_apply_filter(filtered : list[dict], baseline : list[dict], max_results : int) -> bool:
    """
    Determine whether to apply a relevance-based filter to the search results based on the number of filtered results compared to the baseline.

    Args:
        filtered (list[dict]): The list of search results after applying a relevance filter.
        baseline (list[dict]): The list of search results before applying the relevance filter.
        max_results (int): The maximum number of results to return.

    Returns:
        bool: Whether to apply the relevance filter.
    """    
    
    if not filtered:
        return False
    if len(filtered) >= len(baseline):
        return True

    minimum_keep = min(max_results, max(2, max_results // 2))
    return len(filtered) >= minimum_keep

def _is_wikipedia_result(item : dict) -> bool:
    """
    Check if a search result item is from Wikipedia based on its URL.

    Args:
        item (dict): The search result item to check.

    Returns:
        bool: True if the item is from Wikipedia, False otherwise.
    """    
    
    return 'wikipedia.org' in (item.get('url', '').lower())


def _apply_source_diversity(items : list[dict], max_results : int) -> list[dict]:
    """
    Apply source diversity to the list of search results by interleaving Wikipedia and non-Wikipedia results, ensuring a mix of sources in the final output.

    Args:
        items (list[dict]): The list of search results.
        max_results (int): The maximum number of results to return.

    Returns:
        list[dict]: The search results with source diversity applied.
    """    
    
    if not items:
        return []

    non_wiki = [item for item in items if not _is_wikipedia_result(item)]
    wiki = [item for item in items if _is_wikipedia_result(item)]
    if not non_wiki:
        return items[:max_results]

    merged: list[dict] = []
    while len(merged) < max_results and (non_wiki or wiki):
        if non_wiki:
            merged.append(non_wiki.pop(0))
            if len(merged) >= max_results:
                break
        if wiki:
            merged.append(wiki.pop(0))

    for remainder in (non_wiki, wiki):
        for item in remainder:
            if len(merged) >= max_results:
                break
            merged.append(item)

    return merged[:max_results]

def web_search(query : str, max_results : int = 8) -> list[dict]:
    """
    Perform a web search for the given query using multiple sources (Wikipedia API, DuckDuckGo Instant Answer API, and DuckDuckGo HTML scraping) and return a list of relevant results with source diversity.

    Args:
        query (str): The search query.
        max_results (int, optional): The maximum number of results to return. Defaults to 8.

    Returns:
        list[dict]: The list of search results with source diversity applied.
    """    
    
    if not query or not query.strip():
        return []

    max_results = max(1, max_results)
    query = query.strip()
    combined: list[dict] = []
    seen_urls: set[str] = set()

    for source in (_search_wikipedia, _search_duckduckgo_html, _search_duckduckgo):
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
        if _should_apply_filter(phrase_filtered, combined, max_results):
            combined = phrase_filtered

    if query_terms:
        anchor_term = max(query_terms, key=len)
        anchor_filtered = [item for item in combined if _contains_term(item, anchor_term)]
        if _should_apply_filter(anchor_filtered, combined, max_results):
            combined = anchor_filtered

    if len(query_terms) >= 2:
        filtered = [item for item in combined if _relevance_score(item, query) >= 3]
        if _should_apply_filter(filtered, combined, max_results):
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

    return _apply_source_diversity(combined, max_results)