from datetime import date
from urllib.parse import urlparse
import re

_PLACEHOLDER_AUTHORS = {
    'unknown',
    'n/a',
    'na',
    'none',
    'null',
    'anonymous',
}

_KNOWN_DOMAIN_AUTHORS = {
    'wikipedia': 'Wikipedia contributors',
    'bbc': 'BBC',
    'cnn': 'CNN',
    'nasa': 'NASA',
    'nih': 'NIH',
    'ieee': 'IEEE',
    'acm': 'ACM',
    'arxiv': 'arXiv',
}


def _coerce_author(author: object) -> str:
    if isinstance(author, str):
        return author.strip()
    if isinstance(author, (list, tuple, set)):
        names = [str(item).strip() for item in author if str(item).strip()]
        return ', '.join(names)
    return ''


def _author_from_url(url: str) -> str:
    host = (urlparse(url).netloc or '').lower()
    if host.startswith('www.'):
        host = host[4:]
    if not host:
        return ''

    labels = [label for label in host.split('.') if label]
    if not labels:
        return ''

    second_level_suffixes = {'co', 'com', 'org', 'net', 'gov', 'edu', 'ac', 'uk'}
    if len(labels) >= 3 and labels[-2] in second_level_suffixes:
        brand = labels[-3]
    elif len(labels) >= 2:
        brand = labels[-2]
    else:
        brand = labels[0]

    if brand in _KNOWN_DOMAIN_AUTHORS:
        return _KNOWN_DOMAIN_AUTHORS[brand]

    brand = re.sub(r'[-_]+', ' ', brand).strip()
    return brand.title() if brand else ''


def _resolve_author(author: object, url: str) -> str:
    normalised = _coerce_author(author)
    if normalised and normalised.lower() not in _PLACEHOLDER_AUTHORS:
        return normalised

    guessed = _author_from_url(url)
    if guessed:
        return guessed

    return 'Unknown'

def format_citation(url: str, title: str, author: object = None) -> str:
    """Formats a basic APA-style citation with graceful fallback fields."""
    title = (title or 'Untitled').strip()
    url = (url or 'URL unavailable').strip()
    author_text = _resolve_author(author, url)

    today = date.today()
    year = today.year
    accessed = today.strftime('%B %d, %Y')
    return f'{author_text}. ({year}). {title}. Retrieved {accessed}, from {url}'