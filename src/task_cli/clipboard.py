import pyperclip

def get_clipboard_text() -> str:
    """Returns text from the clipboard."""
    try:
        return pyperclip.paste().strip()
    except Exception:
        return ""
