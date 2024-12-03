def safe_str_cmp(a: str, b: str) -> bool:
    """
    A replacement for Werkzeug's removed safe_str_cmp function.
    Performs a constant-time comparison of two strings.
    """
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)
    return result == 0

# Remove the monkey patching
# import flask_login.utils
# flask_login.utils.safe_str_cmp = safe_str_cmp