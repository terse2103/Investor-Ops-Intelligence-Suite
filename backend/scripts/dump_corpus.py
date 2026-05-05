"""One-shot: export the local Chroma index into ``data/corpus.jsonl``.

Run from the ``backend/`` directory whenever the local index is in the
desired state. The output file is committed and shipped with the repo so
deployment environments that cannot reach indmoney.com (HF Spaces,
GitHub Actions runners) can rebuild the index without network access.

Usage:
    cd backend
    uv run python -m scripts.dump_corpus
"""
from __future__ import annotations

import json
from pathlib import Path

from app.core.retriever import get_retriever


def main() -> None:
    out_path = Path(__file__).resolve().parent.parent / "data" / "corpus.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    retriever = get_retriever()
    blob = retriever._collection.get(include=["documents", "metadatas"])
    ids = blob.get("ids") or []
    docs = blob.get("documents") or []
    metas = blob.get("metadatas") or []

    n = 0
    with out_path.open("w", encoding="utf-8") as f:
        for cid, text, meta in zip(ids, docs, metas):
            record = {
                "id": cid,
                "text": text,
                "metadata": dict(meta) if meta else {},
            }
            f.write(json.dumps(record, ensure_ascii=False))
            f.write("\n")
            n += 1

    print(f"Wrote {n} records to {out_path}")


if __name__ == "__main__":
    main()
