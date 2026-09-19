from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        if self.store.get_collection_size() == 0:
            return "Không tìm thấy thông tin trong cơ sở dữ liệu."
        
        results = self.store.search(question, top_k=top_k)
        
        if not results:
            return "Không tìm thấy thông tin liên quan đến câu hỏi."
        
        context_parts = []
        for i, result in enumerate(results, 1):
            source = result["metadata"].get("source_url", "unknown")
            context_parts.append(f"[{i}] {result['content']} (nguồn: {source})")
        
        context = "\n\n".join(context_parts)
        
        prompt = f"""Dựa trên ngữ cảnh dưới đây, hãy trả lời câu hỏi. Chỉ sử dụng thông tin trong ngữ cảnh. Nếu ngữ cảnh không chứa câu trả lời, hãy nói rõ rằng không tìm thấy thông tin.

Ngữ cảnh:
{context}

Câu hỏi: {question}

Trả lời (trích dẫn số thứ tự chunk như [1], [2] khi dùng thông tin):"""
        
        return self.llm_fn(prompt)
