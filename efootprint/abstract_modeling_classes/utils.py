import re


def css_escape(input_string):
    """
    Escape a string to be used as a CSS identifier.
    """
    def escape_char(c):
        if re.match(r'[a-zA-Z0-9_-]', c):
            return c
        elif c == ' ':
            return '-'
        else:
            return f'{ord(c):x}'

    return ''.join(escape_char(c) for c in input_string)
