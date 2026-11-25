import os

import tiktoken
from docling.document_converter import DocumentConverter

CHUNK_TOKENS = int(os.getenv("CHUNK_TOKENS", "400"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

_enc = tiktoken.get_encoding("cl100k_base")
_converter = DocumentConverter()


def _split_text(text: str) -> list[str]:
    """Split text into ~CHUNK_TOKENS token chunks with CHUNK_OVERLAP overlap."""
    tokens = _enc.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = start + CHUNK_TOKENS
        chunks.append(_enc.decode(tokens[start:end]))
        start += CHUNK_TOKENS - CHUNK_OVERLAP
    return [c.strip() for c in chunks if c.strip()]


def parse_and_chunk(path: str) -> list[dict]:
    """Parse any supported file and return [{"text": ..., "page": N|None}]."""
    result = _converter.convert(path)
    doc = result.document

    chunks = []
    for item, _level in doc.iterate_items():
        text = getattr(item, "text", None)
        if not text or not text.strip():
            continue
        page = None
        if getattr(item, "prov", None):
            page = item.prov[0].page_no
        for piece in _split_text(text):
            chunks.append({"text": piece, "page": page})
    return chunks