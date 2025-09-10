from typing import List, Dict, Any, cast
import json
from langchain.schema import Document

def format_docs_structured(docs: List[Document]) -> str:
    """Return a compact JSON list of chunks with useful metadata."""
    items: List[Dict[str, Any]] = []
    for i, d in enumerate(docs, start=1):
        md = cast(dict[str, str], d.metadata) or {} #type: ignore
        items.append({
            "id": i,  # stable id for in-answer citations
            "source": md.get("source") or md.get("file_path"),
            "page": md.get("page_number"),
            "score": md.get("score"),  # may be None unless you add it (see below)
            "page_content": d.page_content
        })
    # Using separators reduces risk of JSON breakage if content includes braces
    return json.dumps({"chunks": items}, ensure_ascii=False)

def format_docs(docs: list[Document]):
    return "\n\n".join([doc.page_content for doc in docs])