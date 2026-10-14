"""Public docs must not link directly to private ChatGPT conversations.

Only release-safe, sanitized fingerprints and case reports belong in this
public repository. Direct conversation URLs remain private even if the author
can open them when signed into the originating account.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONVERSATION_LINK = re.compile(
    r"https?://(?:www\.)?chatgpt\.com/c/[a-f0-9]{8}-[a-f0-9]{4}-"
    r"[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b",
    re.IGNORECASE,
)


def test_public_docs_never_expose_real_chat_conversation_links() -> None:
    documents = [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]
    documents.extend(sorted((ROOT / "docs").rglob("*.json")))
    leaked_paths = [
        path.relative_to(ROOT).as_posix()
        for path in documents
        if CONVERSATION_LINK.search(path.read_text(encoding="utf-8"))
    ]
    assert not leaked_paths, (
        "Replace private ChatGPT conversation links with sanitized, SHA-only "
        f"evidence in these public files: {leaked_paths}"
    )
