"""Registration helpers — shared validation logic."""


def validate_text(text, min_length=1, max_length=500):
    """Validate text input"""
    if not text or not text.strip():
        return False, "Input cannot be empty."
    if len(text.strip()) < min_length:
        return False, f"Input must be at least {min_length} characters."
    if len(text) > max_length:
        return False, f"Input must not exceed {max_length} characters."
    return True, None
