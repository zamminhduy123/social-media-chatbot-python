import re

def get_key_word_regex(key_word):
    """
    Generate a regex pattern for the given key word.
    """
    return re.compile(rf"^{key_word}(_\w+)*$")