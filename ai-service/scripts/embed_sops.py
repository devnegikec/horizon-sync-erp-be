"""One-shot script to ingest SOP / knowledge documents into pgvector.

Usage (inside ai-service container):
    python scripts/embed_sops.py /app/knowledge_base/sops/

Or with specific file:
    python scripts/embed_sops.py /app/knowledge_base/sops/receiving.md

Scans markdown / text / PDF files, chunks them, embeds, and writes to vector_chunks table.
"""

import argparse
import hashlib
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, ".")

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.vector_chunk import ChunkSource, VectorChunk
from app.services.doc_parser import get_parser
from app.services.embedding import get_embedding_service

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Chunking settings
CHUNK_SIZE = 512  # tokens ~ words; adjust as needed
CHUNK_OVERLAP = 64


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks by word count."""
    words = text.split()
    if len(words) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        start += chunk_size - overlap
    return chunks


def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def ingest_file(file_path: Path, source_type: ChunkSource, db: Session) -> int:
    """Parse, chunk, embed, and store a single file. Returns number of chunks created."""
    logger.info("Ingesting %s", file_path)

    parser = get_parser()
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    # Parse to raw text
    try:
        raw_text = parser.parse(file_bytes, file_path.name, None)
    except Exception as e:
        logger.error("Failed to parse %s: %s", file_path, e)
        return 0

    # Simple markdown heading extraction for section names
    import re
    heading_pattern = re.compile(r"^#{1,3}\s+(.+)$", re.MULTILINE)

    # Split by major headings if present, otherwise chunk raw text
    sections = []
    matches = list(heading_pattern.finditer(raw_text))
    if len(matches) >= 2:
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
            section_title = match.group(1).strip()
            section_text = raw_text[start:end].strip()
            sections.append((section_title, section_text))
    else:
        sections.append((file_path.stem, raw_text))

    embedding_service = get_embedding_service()
    total_chunks = 0

    for section_title, section_text in sections:
        chunks = chunk_text(section_text)
        for idx, chunk_text in enumerate(chunks):
            content_hash = compute_hash(chunk_text)

            # Deduplication check
            existing = (
                db.query(VectorChunk)
                .filter(VectorChunk.content_hash == content_hash)
                .first()
            )
            if existing:
                logger.debug("Skipping duplicate chunk hash %s", content_hash[:16])
                continue

            # Embed
            try:
                vector = await embedding_service.embed_single(chunk_text)
            except Exception as e:
                logger.error("Embedding failed for chunk in %s: %s", file_path, e)
                continue

            chunk = VectorChunk(
                source_type=source_type,
                source_id=str(file_path),
                source_title=file_path.stem,
                section=section_title,
                chunk_index=idx,
                content=chunk_text,
                content_hash=content_hash,
                embedding=vector,
            )
            db.add(chunk)
            total_chunks += 1

    db.commit()
    logger.info("Created %d chunks for %s", total_chunks, file_path.name)
    return total_chunks


async def main():
    parser = argparse.ArgumentParser(description="Ingest SOP documents into pgvector")
    parser.add_argument("path", help="File or directory to ingest")
    parser.add_argument(
        "--source-type",
        choices=["sop", "playbook", "put_away_rule", "location_hierarchy", "item_master"],
        default="sop",
        help="Type of knowledge source",
    )
    args = parser.parse_args()

    target = Path(args.path)
    source_type = ChunkSource(args.source_type)
    db = SessionLocal()

    try:
        if target.is_file():
            count = await ingest_file(target, source_type, db)
            logger.info("Done. %d chunks from single file.", count)
        elif target.is_dir():
            total = 0
            for ext in (".md", ".txt", ".pdf", ".docx"):
                for file_path in target.rglob(f"*{ext}"):
                    count = await ingest_file(file_path, source_type, db)
                    total += count
            logger.info("Done. %d total chunks from directory.", total)
        else:
            logger.error("Path not found: %s", target)
            sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
