from datetime import date

def format_citation(url: str, title: str, author: str = 'Unknown') -> str:
    """Formats a basic APA-style citation with graceful fallback fields."""
    title = (title or 'Untitled').strip()
    author = (author or 'Unknown').strip()
    url = (url or 'URL unavailable').strip()

    today = date.today()
    year = today.year
    accessed = today.strftime('%B %d, %Y')
    return f'{author}. ({year}). {title}. Retrieved {accessed}, from {url}'