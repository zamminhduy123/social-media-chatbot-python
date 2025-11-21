import re

def get_keyword_regex(keyword: str,
                       prefix: str = "://",
                       capture: str = r"([^\s]+)") -> re.Pattern:
    """
    Return a compiled regex that detects a directive of the form

        keyword + prefix + <capture group>

    By default it matches strings like:
        send_image://https://example.com/pic.jpg
    or
        IMAGE_SEND://file_id

    Parameters
    ----------
    keyword : str
        The directive keyword (e.g. 'send_image', 'IMAGE_SEND').
    prefix : str, optional
        The delimiter that follows the keyword (default '://').
    capture : str, optional
        Regex for what should be captured after the prefix
        (default group = one or more non‑whitespace chars).

    Returns
    -------
    re.Pattern
        A compiled regex with one capture group.
    """
    pattern = re.escape(keyword) + re.escape(prefix) + capture
    return re.compile(pattern, flags=re.IGNORECASE)

def strip_keyword_directives(text: str,
                             keyword: str,
                             prefix: str = "://",
                             capture: str = r"([^\s]+)"):
    """
    Remove every  “keyword://something”  directive from `text`.

    Returns
    -------
    tuple[list[str], str]
        • list of all captured strings (e.g. URLs, ids)  
        • the text with directives stripped and extra whitespace trimmed
    """
    pattern = get_keyword_regex(keyword, prefix, capture)
    matches = pattern.findall(text)           # list of captured parts
    cleaned  = pattern.sub("", text).strip()  # remove directives
    return matches, cleaned

def safe_cast(val, to_type, default):
    try:
        return to_type(val)
    except (ValueError, TypeError):
        return default