def summarise_text(text: str, max_sentences: int = 5) -> str:
    """ Very lightweight extractive summariser. Selects the first max_sentences sentences from the text. (In production you would call an LLM here instead.) """
    
    import re
    sentences = re.split(r'(?<=[.!?]) +', text.strip())
    selected = sentences[:max_sentences]
    return ' '.join(selected)