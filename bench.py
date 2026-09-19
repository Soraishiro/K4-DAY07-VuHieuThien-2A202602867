#!/usr/bin/env python3
"""
Benchmark script for Lab 07.

Runs the shared five-query benchmark across chunking strategies, verifies that
retrieved chunks contain the declared evidence, and records filtered/unfiltered
A/B results for metadata filters.
"""

import argparse
import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> None:
        return None

from src.agent import KnowledgeBaseAgent
from src.chunking import FixedSizeChunker, RecursiveChunker, SentenceChunker
from src.embeddings import MockEmbedder
from src.models import Document
from src.store import EmbeddingStore


DATA_DIR_NAMES = ("dang-ky-hoc-phan", "thu-vien")
DEFAULT_STRATEGIES = ("fixed", "sentence", "recursive", "heading", "custom")
CHUNK_SIZE = 500


class HeadingChunker:
    """Chunk Markdown by level-two and level-three headings."""

    def __init__(self, chunk_size: int = CHUNK_SIZE) -> None:
        self.chunk_size = max(1, chunk_size)

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []

        parts = re.split(r"(^#{2,3}\s+.+$)", text, flags=re.MULTILINE)
        chunks: list[str] = []
        current_section: list[str] = []
        current_heading = ""

        for raw_part in parts:
            part = raw_part.strip()
            if not part:
                continue

            if re.match(r"^#{2,3}\s+", part):
                if current_section:
                    chunks.extend(self._split_section("\n\n".join(current_section), current_heading))
                current_heading = part
                current_section = [part]
            else:
                current_section.append(part)

        if current_section:
            chunks.extend(self._split_section("\n\n".join(current_section), current_heading))

        return chunks

    def _split_section(self, section: str, heading: str) -> list[str]:
        if len(section) <= self.chunk_size:
            return [section]

        pieces: list[str] = []
        remainder = section
        has_split = False

        while len(remainder) > self.chunk_size:
            split_at = max(
                remainder.rfind("\n\n", 0, self.chunk_size),
                remainder.rfind("\n", 0, self.chunk_size),
                remainder.rfind(". ", 0, self.chunk_size),
            )
            if split_at <= 0:
                split_at = self.chunk_size

            piece = remainder[:split_at].strip()
            if has_split and heading:
                piece = f"{heading}\n\n{piece}"
            if piece:
                pieces.append(piece)

            remainder = remainder[split_at:].strip()
            has_split = True

        if remainder:
            if has_split and heading:
                remainder = f"{heading}\n\n{remainder}"
            if remainder:
                pieces.append(remainder)

        return pieces or [section]


class CustomChunker:
    """Heading-first chunker with recursive fallback for oversized sections."""

    def __init__(self, chunk_size: int = CHUNK_SIZE) -> None:
        self.chunk_size = max(1, chunk_size)
        self.heading_chunker = HeadingChunker(chunk_size=self.chunk_size)
        self.recursive_chunker = RecursiveChunker(chunk_size=self.chunk_size)

    def chunk(self, text: str) -> list[str]:
        chunks: list[str] = []
        for chunk in self.heading_chunker.chunk(text):
            if len(chunk) <= self.chunk_size:
                chunks.append(chunk)
            else:
                chunks.extend(self.recursive_chunker.chunk(chunk))
        return chunks


def get_chunker(chunker_type: str):
    if chunker_type == "fixed":
        return FixedSizeChunker(chunk_size=CHUNK_SIZE, overlap=50)
    if chunker_type == "sentence":
        return SentenceChunker(max_sentences_per_chunk=3)
    if chunker_type == "recursive":
        return RecursiveChunker(chunk_size=CHUNK_SIZE)
    if chunker_type == "heading":
        return HeadingChunker(chunk_size=CHUNK_SIZE)
    if chunker_type == "custom":
        return CustomChunker(chunk_size=CHUNK_SIZE)
    raise ValueError(f"Unknown chunker type: {chunker_type}")


def get_embedder(backend: str):
    if backend == "mock":
        return MockEmbedder()
    if backend == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY not found in environment")
        from src.embeddings import OpenAIEmbedder

        return OpenAIEmbedder()
    if backend == "local":
        from src.embeddings import LocalEmbedder

        return LocalEmbedder()
    if backend == "gemini":
        from src.embeddings import GeminiEmbedder

        return GeminiEmbedder()
    raise ValueError(f"Unknown embedding backend: {backend}")


def load_documents(data_dir: Path) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for file_path in sorted(data_dir.glob("*.md")):
        content = file_path.read_text(encoding="utf-8")
        metadata: dict[str, str] = {}
        body = content

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                body = parts[2].strip()
                for line in parts[1].splitlines():
                    if ":" not in line:
                        continue
                    key, value = line.split(":", 1)
                    value = value.strip().strip("\"'")
                    metadata[key.strip()] = value

        doc_id = metadata.get("doc_id", file_path.stem)
        docs.append(
            {
                "doc_id": doc_id,
                "title": metadata.get("title", file_path.stem),
                "content": body,
                "metadata": metadata,
            }
        )
    return docs


def load_queries() -> list[dict[str, Any]]:
    with Path("data/benchmark_queries.json").open("r", encoding="utf-8") as file:
        queries = json.load(file)
    if len(queries) != 5:
        raise ValueError(f"Expected exactly 5 benchmark queries, found {len(queries)}")
    return queries


def build_store(
    chunker_type: str,
    embedder,
) -> tuple[EmbeddingStore, list[dict[str, Any]], list[Document]]:
    raw_docs: list[dict[str, Any]] = []
    for data_dir_name in DATA_DIR_NAMES:
        data_dir = Path("data") / data_dir_name
        if data_dir.exists():
            raw_docs.extend(load_documents(data_dir))

    chunker = get_chunker(chunker_type)
    documents: list[Document] = []
    for raw_doc in raw_docs:
        for index, chunk in enumerate(chunker.chunk(raw_doc["content"])):
            if not chunk.strip():
                continue
            documents.append(
                Document(
                    id=f"{raw_doc['doc_id']}#{index}",
                    content=chunk,
                    metadata={**raw_doc["metadata"], "doc_id": raw_doc["doc_id"]},
                )
            )

    store = EmbeddingStore(embedding_fn=embedder)
    store.add_documents(documents)
    return store, raw_docs, documents


def normalize_text(value: str) -> str:
    text = str(value or "")
    text = re.sub(r"\*\*|__|`", "", text)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("|", " ")
    return re.sub(r"\s+", " ", text).strip().casefold()


def evidence_candidates(query: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    for key in ("evidence", "gold_value"):
        value = query.get(key)
        if isinstance(value, str) and value.strip() and value.strip() not in candidates:
            candidates.append(value.strip())
    return candidates


def evidence_matches(content: str, evidence: str) -> bool:
    if not evidence:
        return False

    normalized_content = normalize_text(content)
    normalized_evidence = normalize_text(evidence)
    if normalized_evidence in normalized_content:
        return True

    tokens = re.findall(r"[^\W_]{2,}", normalized_evidence, flags=re.UNICODE)
    stop_words = {
        "à",
        "các",
        "của",
        "là",
        "trong",
        "và",
        "với",
        "ngày",
        "môn",
        "học",
        "tài",
        "liệu",
        "ngành",
        "chuyên",
        "sinh",
        "viên",
        "giảng",
    }
    distinctive = [
        token
        for token in tokens
        if len(token) >= 3 and token not in stop_words and not token.isdigit()
    ]
    if not distinctive:
        return False

    required_hits = len(distinctive) if len(distinctive) <= 2 else max(2, (len(distinctive) + 1) // 2)
    return sum(token in normalized_content for token in distinctive) >= required_hits


def evidence_snippet(content: str, evidence: str) -> str:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    for line in lines:
        if evidence_matches(line, evidence):
            return line[:240]

    tokens = [
        token
        for token in re.findall(r"[^\W_]{2,}", normalize_text(evidence), flags=re.UNICODE)
        if len(token) >= 3
    ]
    if tokens:
        best_line = max(lines, key=lambda line: sum(token in normalize_text(line) for token in tokens), default="")
        if best_line:
            return best_line[:240]

    return content.strip()[:240]


def find_evidence(
    search_results: list[dict[str, Any]],
    query: dict[str, Any],
) -> tuple[bool, str | None, str, str | None]:
    candidates = evidence_candidates(query)
    for result in search_results:
        for candidate in candidates:
            if evidence_matches(result["content"], candidate):
                return (
                    True,
                    candidate,
                    evidence_snippet(result["content"], candidate),
                    result["metadata"].get("doc_id"),
                )
    return False, None, "Không tìm thấy bằng chứng trong top-3.", None


def evaluate_search(
    search_results: list[dict[str, Any]],
    query: dict[str, Any],
) -> dict[str, Any]:
    gold_doc_id = query["gold_doc_id"]
    found_in_top1 = bool(search_results and search_results[0]["metadata"].get("doc_id") == gold_doc_id)
    found_in_top3 = any(result["metadata"].get("doc_id") == gold_doc_id for result in search_results)
    evidence_found, evidence_match, snippet, evidence_doc_id = find_evidence(search_results, query)

    if evidence_found and found_in_top1:
        score = 2
        score_reason = "top-1 và top-3 chứa bằng chứng"
    elif evidence_found and found_in_top3:
        score = 1
        score_reason = "top-3 chứa bằng chứng nhưng không ở top-1"
    else:
        score = 0
        score_reason = "không có bằng chứng trong top-3"

    agent_answer = f"Ngữ cảnh chứa bằng chứng: {snippet}" if evidence_found else "Không tìm thấy bằng chứng trong top-3."
    return {
        "query_id": query["id"],
        "query": query["query"],
        "query_type": query.get("type"),
        "gold_doc_id": gold_doc_id,
        "gold_answer": query["gold_answer"],
        "gold_value": query.get("gold_value"),
        "evidence": query.get("evidence"),
        "metadata_filter": query.get("metadata_filter"),
        "top_results": [result["metadata"].get("doc_id") for result in search_results],
        "top_scores": [result["score"] for result in search_results],
        "found_in_top1": found_in_top1,
        "found_in_top3": found_in_top3,
        "evidence_found": evidence_found,
        "evidence_match": evidence_match,
        "evidence_doc_id": evidence_doc_id,
        "agent_answer": agent_answer,
        "agent_answer_verified": evidence_found,
        "score": score,
        "score_reason": score_reason,
    }


def search_query(
    store: EmbeddingStore,
    query: dict[str, Any],
    metadata_filter: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    if metadata_filter is None:
        return store.search(query["query"], top_k=3)
    return store.search_with_filter(
        query["query"],
        top_k=3,
        metadata_filter=metadata_filter,
    )


def run_ab_pair(
    store: EmbeddingStore,
    query: dict[str, Any],
) -> dict[str, Any]:
    metadata_filter = query.get("metadata_filter")
    without_results = store.search(query["query"], top_k=3)
    with_results = search_query(store, query, metadata_filter)
    return {
        "query_id": query["id"],
        "query": query["query"],
        "metadata_filter": metadata_filter,
        "without_filter": evaluate_search(without_results, query),
        "with_filter": evaluate_search(with_results, query),
    }


def write_log_header(log_file: Path, chunker_type: str, embedding_backend: str) -> None:
    with log_file.open("w", encoding="utf-8") as log:
        log.write("=== Lab 07 Benchmark ===\n")
        log.write(f"Chunker: {chunker_type}\n")
        log.write(f"Embedding: {embedding_backend}\n")
        log.write("Scoring: evidence-aware; 2=top-1+evidence, 1=top-3+evidence, 0=none\n\n")


def append_log_result(log_file: Path, result: dict[str, Any]) -> None:
    with log_file.open("a", encoding="utf-8") as log:
        log.write(f"Query: {result['query']}\n")
        if result.get("metadata_filter"):
            log.write(f"  Filter: {result['metadata_filter']}\n")
        for index, doc_id in enumerate(result["top_results"], start=1):
            marker = " *" if doc_id == result["gold_doc_id"] else ""
            log.write(f"  [{index}] score={result['top_scores'][index - 1]:.4f} doc_id={doc_id}{marker}\n")
        log.write(f"  Evidence: {result['evidence_found']} match={result['evidence_match']} doc_id={result['evidence_doc_id']}\n")
        log.write(f"  Agent answer: {result['agent_answer']}\n")
        log.write(f"  Score: {result['score']} ({result['score_reason']})\n\n")


def append_log_ab(log_file: Path, ab_tests: dict[str, Any]) -> None:
    if not ab_tests:
        return
    with log_file.open("a", encoding="utf-8") as log:
        log.write("=== A/B METADATA FILTER TESTS ===\n")
        for query_id, ab_result in ab_tests.items():
            without_filter = ab_result["without_filter"]
            with_filter = ab_result["with_filter"]
            log.write(
                f"{query_id}: filter={ab_result['metadata_filter']} | "
                f"without top1={without_filter['found_in_top1']} top3={without_filter['found_in_top3']} "
                f"evidence={without_filter['evidence_found']} | "
                f"with top1={with_filter['found_in_top1']} top3={with_filter['found_in_top3']} "
                f"evidence={with_filter['evidence_found']}\n"
            )


def run_benchmark(
    chunker_type: str,
    embedding_backend: str,
    output_file: str | Path,
    log_file: str | Path,
    run_ab: bool = True,
) -> dict[str, Any]:
    output_path = Path(output_file)
    log_path = Path(log_file)
    write_log_header(log_path, chunker_type, embedding_backend)

    store, raw_docs, documents = build_store(chunker_type, get_embedder(embedding_backend))
    queries = load_queries()
    mock_llm = lambda prompt: "[MOCK LLM] Answer based on context above."
    agent = KnowledgeBaseAgent(store, mock_llm)

    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"Total documents: {len(raw_docs)}\n")
        log.write(f"Stored chunks: {len(documents)}\n")
        log.write(f"=== Running {len(queries)} Benchmark Queries ===\n\n")

    results: list[dict[str, Any]] = []
    for query in queries:
        search_results = search_query(store, query, query.get("metadata_filter"))
        result = evaluate_search(search_results, query)
        result["agent_response"] = agent.answer(query["query"], top_k=3)
        results.append(result)
        append_log_result(log_path, result)

    ab_tests: dict[str, Any] = {}
    if run_ab:
        for query in queries:
            if query.get("metadata_filter"):
                ab_tests[query["id"]] = run_ab_pair(store, query)
        append_log_ab(log_path, ab_tests)

    total_score = sum(result["score"] for result in results)
    max_score = 2 * len(results)
    top1_count = sum(result["found_in_top1"] for result in results)
    top3_count = sum(result["found_in_top3"] for result in results)
    evidence_count = sum(result["evidence_found"] for result in results)

    output = {
        "chunker": chunker_type,
        "embedding": embedding_backend,
        "document_count": len(raw_docs),
        "chunk_count": len(documents),
        "scoring": {
            "method": "evidence-aware",
            "max_score": max_score,
            "rule": "2=top-1 and evidence, 1=top-3 and evidence, 0=no evidence",
        },
        "total_score": total_score,
        "max_score": max_score,
        "top1_count": top1_count,
        "top3_count": top3_count,
        "evidence_count": evidence_count,
        "results": results,
        "ab_tests": ab_tests,
    }

    with log_path.open("a", encoding="utf-8") as log:
        log.write("=== SUMMARY ===\n")
        log.write(f"Total evidence-aware score: {total_score}/{max_score}\n")
        log.write(f"Top-1 accuracy: {top1_count}/{len(results)}\n")
        log.write(f"Top-3 recall: {top3_count}/{len(results)}\n")
        log.write(f"Evidence found: {evidence_count}/{len(results)}\n\n")
        for result in results:
            log.write(
                f"  {result['query_id']}: score={result['score']} "
                f"(top1={result['found_in_top1']}, top3={result['found_in_top3']}, evidence={result['evidence_found']})\n"
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def write_ab_summary(all_results: dict[str, Any], output_dir: Path) -> None:
    ab_data = {
        strategy: result.get("ab_tests", {})
        for strategy, result in all_results.items()
    }
    (output_dir / "ab_results.json").write_text(
        json.dumps(ab_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "=== Lab 07 A/B Metadata Filter Results ===",
        "Scoring: evidence-aware; 2=top-1 and evidence, 1=top-3 and evidence, 0=no evidence",
        "",
    ]
    for strategy, result in all_results.items():
        lines.append(f"[{strategy}] chunks={result['chunk_count']} score={result['total_score']}/{result['max_score']}")
        for query_id, ab_result in result.get("ab_tests", {}).items():
            without_filter = ab_result["without_filter"]
            with_filter = ab_result["with_filter"]
            lines.append(
                f"{query_id} filter={ab_result['metadata_filter']} | "
                f"without: top1={without_filter['found_in_top1']} top3={without_filter['found_in_top3']} evidence={without_filter['evidence_found']} | "
                f"with: top1={with_filter['found_in_top1']} top3={with_filter['found_in_top3']} evidence={with_filter['evidence_found']}"
            )
        lines.append("")
    (output_dir / "ab_results.txt").write_text("\n".join(lines), encoding="utf-8")


def run_all(
    strategies: list[str] | tuple[str, ...],
    embedding_backend: str,
    output_dir: str | Path = ".",
    run_ab: bool = True,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    embedder = get_embedder(embedding_backend)
    all_results: dict[str, Any] = {}

    for strategy in strategies:
        output_file = output_path / f"ket_qua_benchmark_{strategy}_{embedding_backend}.txt"
        log_file = output_path / f"bench_log_{strategy}_{embedding_backend}.txt"
        print(f"Running {strategy} + {embedding_backend}...")
        result = run_benchmark(strategy, embedding_backend, output_file, log_file, run_ab=run_ab)
        all_results[strategy] = result
        print(
            f"  chunks={result['chunk_count']} score={result['total_score']}/{result['max_score']} "
            f"top1={result['top1_count']}/5 top3={result['top3_count']}/5 evidence={result['evidence_count']}/5"
        )

    (output_path / "ket_qua_benchmark.txt").write_text(
        json.dumps(all_results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if run_ab:
        write_ab_summary(all_results, output_path)
    return all_results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Lab 07 retrieval benchmark")
    parser.add_argument(
        "--strategies",
        nargs="+",
        default=list(DEFAULT_STRATEGIES),
        choices=list(DEFAULT_STRATEGIES),
        help="Chunking strategies to run uniformly",
    )
    parser.add_argument(
        "--embedding",
        default="openai",
        choices=("mock", "local", "openai", "gemini"),
        help="Embedding backend used for every strategy",
    )
    parser.add_argument("--output-dir", default=".", help="Directory for result and log files")
    parser.add_argument("--skip-ab", action="store_true", help="Skip filtered/unfiltered A/B tests")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    results = run_all(args.strategies, args.embedding, args.output_dir, run_ab=not args.skip_ab)
    print("\n=== COMBINED SUMMARY ===")
    for strategy, result in results.items():
        print(
            f"{strategy:12} | Score: {result['total_score']}/{result['max_score']} "
            f"| Top-1: {result['top1_count']}/5 | Top-3: {result['top3_count']}/5 "
            f"| Evidence: {result['evidence_count']}/5"
        )
    print("\nResults saved to ket_qua_benchmark.txt and individual result/log files.")


if __name__ == "__main__":
    main()
