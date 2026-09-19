#!/usr/bin/env python3
"""
Benchmark script for Lab 07 - runs 5 evaluation queries against the corpus
using the implemented chunking + embedding store + agent pipeline.
"""

import json
import yaml
import re
from pathlib import Path
from typing import Optional

from src.chunking import FixedSizeChunker, SentenceChunker, RecursiveChunker
from src.store import EmbeddingStore
from src.agent import KnowledgeBaseAgent
from src.embeddings import MockEmbedder, LocalEmbedder
from src.models import Document


# ============================================================
# CHUNKER SELECTION - Change this line to test different strategies
# ============================================================
CHUNKER_TYPE = "recursive"  # Options: "fixed", "sentence", "recursive", "heading"

# ============================================================
# EMBEDDING BACKEND - Change to use real embeddings
# ============================================================
EMBEDDING_BACKEND = "mock"  # Options: "mock", "local"

# ============================================================


class HeadingChunker:
    """Chunk by markdown headings (##, ###), keeping heading with each section."""
    
    def __init__(self, chunk_size: int = 500) -> None:
        self.chunk_size = chunk_size
    
    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        
        heading_pattern = r'(^#{2,3}\s+.+$)'
        parts = re.split(heading_pattern, text, flags=re.MULTILINE)
        
        chunks = []
        current_chunk = ""
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            if re.match(r'^#{2,3}\s+', part):
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = part
            else:
                if current_chunk:
                    current_chunk += "\n\n" + part
                else:
                    current_chunk = part
            
            while len(current_chunk) > self.chunk_size:
                split_idx = current_chunk.rfind("\n\n", 0, self.chunk_size)
                if split_idx == -1:
                    split_idx = current_chunk.rfind("\n", 0, self.chunk_size)
                if split_idx == -1:
                    split_idx = self.chunk_size
                chunks.append(current_chunk[:split_idx].strip())
                current_chunk = current_chunk[split_idx:].strip()
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks


def get_chunker(chunker_type: str):
    """Get chunker instance by type."""
    if chunker_type == "fixed":
        return FixedSizeChunker(chunk_size=500, overlap=50)
    elif chunker_type == "sentence":
        return SentenceChunker(max_sentences_per_chunk=3)
    elif chunker_type == "recursive":
        return RecursiveChunker(chunk_size=500)
    elif chunker_type == "heading":
        return HeadingChunker(chunk_size=500)
    else:
        raise ValueError(f"Unknown chunker type: {chunker_type}")


def get_embedder(backend: str):
    """Get embedder instance by backend."""
    if backend == "mock":
        return MockEmbedder()
    elif backend == "local":
        return LocalEmbedder()
    else:
        raise ValueError(f"Unknown embedding backend: {backend}")


def load_documents(data_dir: Path):
    """Load all .md files from data directory, parse frontmatter and content."""
    docs = []
    for f in sorted(data_dir.glob("*.md")):
        content = f.read_text(encoding="utf-8")
        
        # Parse frontmatter
        metadata = {}
        body = content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                fm_text = parts[1].strip()
                body = parts[2].strip()
                for line in fm_text.split("\n"):
                    if ":" in line:
                        key, val = line.split(":", 1)
                        metadata[key.strip()] = val.strip().strip('"')
        
        doc_id = metadata.get("doc_id", f.stem)
        docs.append({
            "doc_id": doc_id,
            "title": metadata.get("title", f.stem),
            "content": body,
            "metadata": metadata,
        })
    return docs


def main():
    import sys
    # Redirect stdout to file to avoid encoding issues
    original_stdout = sys.stdout
    sys.stdout = open("bench_output.txt", "w", encoding="utf-8")
    
    try:
        _main()
    finally:
        sys.stdout.close()
        sys.stdout = original_stdout
        # Print summary to console
        with open("bench_output.txt", "r", encoding="utf-8") as f:
            print(f.read())


def _main():
    print(f"=== Lab 07 Benchmark ===")
    print(f"Chunker: {CHUNKER_TYPE}")
    print(f"Embedding: {EMBEDDING_BACKEND}")
    print()
    
    # Load documents from both folders
    all_raw_docs = []
    for data_dir_name in ["dang-ky-hoc-phan", "thu-vien"]:
        data_dir = Path(f"data/{data_dir_name}")
        if data_dir.exists():
            raw_docs = load_documents(data_dir)
            all_raw_docs.extend(raw_docs)
            print(f"Loaded {len(raw_docs)} documents from {data_dir_name}")
    
    print(f"Total documents: {len(all_raw_docs)}")
    
    # Load benchmark queries
    with open("data/benchmark_queries.json", "r", encoding="utf-8") as f:
        queries = json.load(f)
    
    # Initialize components
    chunker = get_chunker(CHUNKER_TYPE)
    embedder = get_embedder(EMBEDDING_BACKEND)
    store = EmbeddingStore(embedding_fn=embedder)
    
    # Chunk and ingest all documents
    print(f"\nChunking and ingesting documents...")
    all_docs = []
    for raw_doc in all_raw_docs:
        chunks = chunker.chunk(raw_doc["content"])
        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
            doc = Document(
                id=f"{raw_doc['doc_id']}#{i}",
                content=chunk,
                metadata={**raw_doc["metadata"], "doc_id": raw_doc["doc_id"]}
            )
            all_docs.append(doc)
    
    store.add_documents(all_docs)
    print(f"Stored {store.get_collection_size()} chunks")
    
    # Initialize agent (using mock LLM for now)
    def mock_llm(prompt: str) -> str:
        return "[MOCK LLM] Answer based on context above."
    
    agent = KnowledgeBaseAgent(store, mock_llm)
    
    # Run benchmark queries
    print(f"\n=== Running {len(queries)} Benchmark Queries ===\n")
    
    results = []
    for q in queries:
        query = q["query"]
        gold_answer = q["gold_answer"]
        gold_doc_id = q["gold_doc_id"]
        metadata_filter = q.get("metadata_filter")
        
        print(f"Query: {query}")
        if metadata_filter:
            print(f"  Filter: {metadata_filter}")
            search_results = store.search_with_filter(query, top_k=3, metadata_filter=metadata_filter)
        else:
            search_results = store.search(query, top_k=3)
        
        # Check if gold doc is in top-3
        found_in_top3 = any(r["metadata"].get("doc_id") == gold_doc_id for r in search_results)
        found_in_top1 = search_results[0]["metadata"].get("doc_id") == gold_doc_id if search_results else False
        
        # Print top-3
        for i, r in enumerate(search_results, 1):
            marker = " ★" if r["metadata"].get("doc_id") == gold_doc_id else ""
            print(f"  [{i}] score={r['score']:.4f} doc_id={r['metadata'].get('doc_id')}{marker}")
            print(f"      preview: {r['content'][:120]}...")
        
        # Agent answer
        answer = agent.answer(query, top_k=3)
        print(f"  Agent: {answer[:100]}...")
        print()
        
        # Score: 2 if top-1 and relevant, 1 if top-2/3, 0 if not found
        if found_in_top1:
            score = 2
        elif found_in_top3:
            score = 1
        else:
            score = 0
        
        results.append({
            "query_id": q["id"],
            "query": query,
            "gold_doc_id": gold_doc_id,
            "gold_answer": gold_answer,
            "top_results": [r["metadata"].get("doc_id") for r in search_results],
            "found_in_top1": found_in_top1,
            "found_in_top3": found_in_top3,
            "score": score,
        })
    
    # Summary
    total_score = sum(r["score"] for r in results)
    max_score = 2 * len(results)
    top1_count = sum(1 for r in results if r["found_in_top1"])
    top3_count = sum(1 for r in results if r["found_in_top3"])
    
    print("=== SUMMARY ===")
    print(f"Total score: {total_score}/{max_score}")
    print(f"Top-1 accuracy: {top1_count}/{len(results)}")
    print(f"Top-3 recall: {top3_count}/{len(results)}")
    print()
    
    for r in results:
        print(f"  {r['query_id']}: score={r['score']} (top1={r['found_in_top1']}, top3={r['found_in_top3']})")
    
    # Save results
    output = {
        "chunker": CHUNKER_TYPE,
        "embedding": EMBEDDING_BACKEND,
        "total_score": total_score,
        "max_score": max_score,
        "top1_count": top1_count,
        "top3_count": top3_count,
        "results": results,
    }
    
    with open("ket_qua_benchmark.txt", "w", encoding="utf-8") as f:
        f.write(json.dumps(output, ensure_ascii=False, indent=2))
    
    print(f"\nResults saved to ket_qua_benchmark.txt")


if __name__ == "__main__":
    main()