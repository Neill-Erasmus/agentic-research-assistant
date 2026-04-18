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

def _coerce_author(author : object) -> str:
    """
    Coerces an author field into a clean string format.
    Handles various input types gracefully, including strings, lists, tuples, and sets.
    If the input is a collection, it joins non-empty items with commas.
    If the input is not a string or collection, it returns an empty string.

    Args:
        author (object): The author information to be coerced, which can be a string, list, tuple, set, or other object type.

    Returns:
        str: The coerced author string.
    """    
    
    if isinstance(author, str):
        return author.strip()
    if isinstance(author, (list, tuple, set)):
        names = [str(item).strip() for item in author if str(item).strip()]
        return ', '.join(names)
    return ''


def _author_from_url(url : str) -> str:
    """
    Attempts to infer an author or organization name from a given URL by extracting the domain and applying heuristics.
    It normalizes the domain to remove common prefixes and suffixes, then checks against a known mapping of domains to author names.
    If no known mapping is found, it formats the domain as a title-cased string.

    Args:
        url (str): The URL from which to infer the author or organization name.

    Returns:
        str: The inferred author or organization name.
    """    
    
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


def _resolve_author(author : object, url : str) -> str:
    """
    Resolves an author name by first attempting to coerce a provided author field, then falling back to inferring from the URL if the author is missing or a known placeholder.
    If both methods fail to produce a valid author name, it returns 'Unknown'.

    Args:
        author (object): The author information to be resolved.
        url (str): The URL from which to infer the author or organization name.

    Returns:
        str: The resolved author name, or 'Unknown' if unable to resolve.
    """    
    
    normalised = _coerce_author(author)
    if normalised and normalised.lower() not in _PLACEHOLDER_AUTHORS:
        return normalised

    guessed = _author_from_url(url)
    if guessed:
        return guessed

    return 'Unknown'

def format_citation(url : str, title : str, author : object = None) -> str:
    """
    Format a citation string in a consistent style, using the provided URL, title, and optional author information.
    The function attempts to resolve the author name using the provided author field and URL, then constructs a citation string that includes the author, publication year, title, and access information.
    If the author cannot be resolved, it defaults to 'Unknown'. The publication year is set to the current year, and the access date is formatted as 'Month Day, Year'.

    Args:
        url (str): The URL of the cited work.
        title (str): The title of the cited work.
        author (object, optional): The author information. Defaults to None.

    Returns:
        str: The formatted citation string.
    """    
    
    title = (title or 'Untitled').strip()
    url = (url or 'URL unavailable').strip()
    author_text = _resolve_author(author, url)

    today = date.today()
    year = today.year
    accessed = today.strftime('%B %d, %Y')
    return f'{author_text}. ({year}). {title}. Retrieved {accessed}, from {url}'