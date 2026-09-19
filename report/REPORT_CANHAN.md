# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Vũ Hiếu Thiên
**Nhóm:** Dinner Chunker
**Ngày:** 19/09/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**

> Hai vector embedding trỏ về cùng hướng trong không gian vector — nghĩa là hai đoạn văn bản mang ý nghĩa ngữ nghĩa gần nhau, bất kể độ dài hay từ vựng cụ thể.

**Ví dụ có độ tương tự CAO:**

- Câu A: "Sinh viên được phép đăng ký tối đa 22 tín chỉ mỗi học kỳ."
- Câu B: "Mỗi học kỳ, học viên có thể ghi danh tối đa 22 tín chỉ."
- Tại sao tương đồng: Cùng nói về quy định 22 tín chỉ/học kỳ, khác từ vựng ("sinh viên"/"học viên", "đăng ký"/"ghi danh") nhưng cùng ý nghĩa cốt lõi.

**Ví dụ có độ tương tự THẤP:**

- Câu A: "Thư viện mở cửa từ 7h sáng đến 22h tối."
- Câu B: "Học phí năm nay tăng 5% so với năm trước."
- Tại sao khác: Hai chủ đề hoàn toàn khác nhau (giờ mở cửa vs học phí), không có từ khóa chung.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**

> Cosine similarity chỉ đo góc giữa hai vector (hướng/ngữ nghĩa) và bất biến với độ dài vector (magnitude). Euclidean distance bị ảnh hưởng bởi độ dài văn bản — văn bản dài có vector magnitude lớn hơn dù cùng chủ đề, làm méo kết quả. Embeddings thường được chuẩn hóa (||v||=1) nên dot product = cosine.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**

> Công thức: `ceil((độ_dài − overlap) / (chunk_size − overlap)) = ceil((10000 − 50) / (500 − 50)) = ceil(9950 / 450) = ceil(22.11) = 23`
>
> Kiểm tra bằng FixedSizeChunker: 23 chunks
>
> **Đáp án: 23 chunks**

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**

> Overlap=100: `ceil((10000 − 100) / (500 − 100)) = ceil(9900 / 400) = ceil(24.75) = 25 chunks`. Tăng overlap từ 50→100 làm tăng 2 chunks.
>
> Overlap lớn hơn giúp bảo toàn ngữ cảnh tại ranh giới chunk — thông tin bị cắt giữa hai chunk vẫn xuất hiện trong cả hai, giảm rủi ro mất thông tin quan trọng khi retrieval. Chi phí: tốn bộ nhớ và thời gian embed/search nhiều hơn.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:

> Dùng regex `(?<=[.!?])\s+` (positive lookbehind) để tách ở vị trí **sau** dấu câu `.`, `!`, `?` theo sau bởi whitespace — giữ nguyên dấu câu trong chunk. Sau đó gom `max_sentences_per_chunk` câu thành một chunk. Edge cases: chữ viết tắt (TS., v.v.) và số thập phân (3.14) sẽ bị cắt sai — ghi nhận trong báo cáo nhưng chưa xử lý do giới hạn regex đơn giản.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:

> Thuật toán hai chiều: (1) **Đệ quy xuống**: thử tách bằng separator ưu tiên cao nhất (`\n\n`, `\n`, `. `, ` `, ``); mảnh nào vẫn > `chunk_size` thì gọi lại `_split` với các separator còn lại. Base case: text ≤ chunk_size hoặc hết separator (fallback cắt cứng theo chunk_size). (2) **Gom lên**: sau khi đệ quy, `_merge_small_chunks()` nối các mảnh nhỏ liền kề cho tới sát `chunk_size` để tránh chunk vụn 5–10 ký tự.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:

> In-memory store: `add_documents` embed từng Document qua `embedding_fn`, lưu record `{id, content, metadata, embedding}` vào list `self._store`. `search` embed query, tính dot product với mọi record, sort giảm dần, trả top-k (bỏ embedding khỏi kết quả). Vector đã chuẩn hóa (||v||=1) nên dot product = cosine similarity.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:

> `search_with_filter`: **LỌC TRƯỚC** (pre-filter) — duyệt `self._store`, chỉ giữ record khớp `metadata_filter` trên mọi key, sau đó mới chạy similarity search trên tập đã lọc. Điều này đảm bảo top-k không bị chiếm bởi tài liệu sai filter. `delete_document`: xoá tất cả record có `metadata['doc_id'] == doc_id`, trả `True/False` tuỳ có xoá được gì.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:

> 1. Kiểm tra store rỗng → trả thông báo. 2. `store.search(question, top_k)` lấy context. 3. Xây prompt: đánh số chunk `[1] [2] [3]` kèm nguồn (`source_url`), yêu cầu model trích dẫn số chunk khi trả lời. 4. Gọi `llm_fn(prompt)`. Prompt cấm bịa đặt: "Chỉ dùng ngữ cảnh cung cấp, không có thì nói rõ không tìm thấy."

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
# Dán kết quả (output) của: pytest tests/ -v
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-8.2.2, pluggy-1.6.0
collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED

============================= 42 passed in 0.08s ==============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán    | Điểm thực tế | Đúng? |
| --- | ----- | ----- | ---------- | ------------ | ----- |
| 1   | Sinh viên được phép đăng ký tối đa 22 tín chỉ mỗi học kỳ. | Mỗi học kỳ, học viên có thể ghi danh tối đa 22 tín chỉ. | cao | 0.0349 | Sai |
| 2   | Thư viện mở cửa từ 7h sáng đến 22h tối. | Học phí năm nay tăng 5% so với năm trước. | thấp | -0.0006 | Đúng |
| 3   | Đăng ký học phần bắt đầu từ ngày 1 tháng 7. | Học phần mở đăng ký từ 1/7 năm nay. | cao | 0.0249 | Sai |
| 4   | Sinh viên nộp học phí trước ngày 15/8. | Hạn nộp học phí là 15 tháng 8. | cao | -0.1063 | Sai |
| 5   | Thư viện có sách tiếng Anh và tiếng Việt. | Cư trú ký túc xá cần đăng ký trước 31/7. | thấp | 0.0110 | Đúng |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**

> Cặp 1 và 4 có ý nghĩa gần như tương đương (cùng nói về 22 tín chỉ/học kỳ, cùng nói về hạn nộp học phí 15/8) nhưng điểm similarity rất thấp (~0.03 và -0.11). Điều này cho thấy **MockEmbedder không mã hóa ngữ nghĩa** — nó băm MD5 văn bản rồi sinh vector giả ngẫu nhiên, nên câu giống nhau về mặt từ vựng cũng cho điểm ngẫu nhiên. Embeddings thật (Sentence Transformers, OpenAI, Gemini) mới nắm bắt được ngữ nghĩa: cùng ý nghĩa → vector cùng hướng → cosine similarity cao.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

| #   | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
| --- | --------------- | ------------------------------------ | ---------- | ------------------------------ | ------------------------------- |
| 1   |                 |                                      |            |                                |                                 |
| 2   |                 |                                      |            |                                |                                 |
| 3   |                 |                                      |            |                                |                                 |
| 4   |                 |                                      |            |                                |                                 |
| 5   |                 |                                      |            |                                |                                 |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** \_\_ / 5

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**

> _Viết 2-3 câu: (Cập nhật sau khi có dữ liệu nhóm và chạy benchmark)_

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí                                        | Điểm tự đánh giá |
| ----------------------------------------------- | ---------------- |
| Khởi động (Warm-up)                             | 5 / 5            |
| Hướng tiếp cận của tôi (My Approach)            | 10 / 10          |
| Hoàn thiện code (Core Implementation — tests)   | 30 / 30          |
| Dự đoán độ tương tự (Similarity Predictions)    | 5 / 5            |
| Kết quả truy xuất của tôi (Competition Results) | \_\_ / 10        |
| **Tổng phần cá nhân**                           | **\_\_ / 60**    |
