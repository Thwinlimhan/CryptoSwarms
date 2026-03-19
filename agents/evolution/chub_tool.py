# agents/evolution/chub_tool.py
import subprocess

def chub_get(api: str, endpoint: str, lang: str = "py") -> str:
    """Fetch Chub docs for a given API endpoint. Returns Markdown string."""
    result = subprocess.run(
        ["chub", "get", f"{api}/{endpoint}", "--lang", lang],
        capture_output=True, text=True, timeout=10,
    )
    return result.stdout if result.returncode == 0 else ""

def chub_annotate(api: str, endpoint: str, note: str) -> None:
    """Persist a workaround note for an API endpoint."""
    subprocess.run(
        ["chub", "annotate", f"{api}/{endpoint}", note],
        capture_output=True, timeout=5,
    )
