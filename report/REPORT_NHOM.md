# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** Dinner Chunker
**Thành viên:**
**Ngày:** 19/09/2026

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Thông tin hỗ trợ lựa chọn và đăng ký học phần tại Trường Đại học Công nghệ Thông tin (UIT): danh mục môn học và chương trình đào tạo khóa K18.

**Tại sao nhóm chọn chủ đề này?**

> Bộ dữ liệu có danh mục mã môn, môn tiên quyết, môn học trước, tín chỉ và các khối học phần theo chương trình K18, giúp xây dựng câu hỏi tra cứu có thể đối chiếu với nguồn. Các trang chương trình đào tạo và danh mục môn học có URL chính thức của UIT; tuy nhiên, bộ dữ liệu hiện tập trung vào thông tin _lựa chọn học phần_, chưa bao quát quy trình hoặc thời hạn đăng ký học phần.

### Danh sách tài liệu (Data Inventory)

| #   | Tên tài liệu                                                                                        | Nguồn (Source URL)                                                                                             | Ngày lấy / Phiên bản      | Số ký tự | Metadata đã gán                                                                                   |
| --- | --------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | ------------------------- | -------- | ------------------------------------------------------------------------------------------------- |
| 1   | Danh mục môn học UIT                                                                                | https://student.uit.edu.vn/danh-muc-mon-hoc-dai-hoc                                                            | 2026-09-19 / `not-stated` | 287,245  | audience=`staff`; department=`all`; category=`course-catalog`; language=`vi`                      |
| 2   | Lựa chọn học phần — Cử nhân ngành Trí tuệ Nhân tạo (Áp dụng từ khóa 18 - 2023)                      | https://student.uit.edu.vn/content/cu-nhan-nganh-tri-tue-nhan-tao-ap-dung-tu-khoa-18-2023                      | 2026-09-19 / `not-stated` | 9,680    | audience=`student`; department=`ai`; category=`curriculum-selection`; language=`vi`; cohort=`K18` |
| 3   | Lựa chọn học phần — Cử nhân ngành Kỹ thuật Máy tính (Áp dụng từ khóa 18 - 2023)                     | https://student.uit.edu.vn/content/cu-nhan-nganh-ky-thuat-may-tinh-ap-dung-tu-khoa-18-2023                     | 2026-09-19 / `not-stated` | 19,144   | audience=`student`; department=`ce`; category=`curriculum-selection`; language=`vi`; cohort=`K18` |
| 4   | Lựa chọn học phần — Cử nhân ngành Khoa học Máy tính (Áp dụng từ khóa 18 - 2023)                     | https://student.uit.edu.vn/content/cu-nhan-nganh-khoa-hoc-may-tinh-ap-dung-tu-khoa-18-2023                     | 2026-09-19 / `not-stated` | 11,258   | audience=`student`; department=`cs`; category=`curriculum-selection`; language=`vi`; cohort=`K18` |
| 5   | Lựa chọn học phần — Cử nhân ngành Khoa học Dữ liệu (Áp dụng từ khóa 18 - 2023)                      | https://student.uit.edu.vn/content/cu-nhan-khoa-hoc-nganh-khoa-hoc-du-lieu-ap-dung-tu-khoa-18-2023             | 2026-09-19 / `not-stated` | 10,813   | audience=`student`; department=`ds`; category=`curriculum-selection`; language=`vi`; cohort=`K18` |
| 6   | Lựa chọn học phần — Cử nhân ngành Hệ thống Thông tin (Áp dụng từ khóa 18 - 2023)                    | https://student.uit.edu.vn/content/cu-nhan-nganh-he-thong-thong-tin-ap-dung-tu-khoa-18-2023                    | 2026-09-19 / `not-stated` | 9,958    | audience=`student`; department=`is`; category=`curriculum-selection`; language=`vi`; cohort=`K18` |
| 7   | Lựa chọn học phần — Cử nhân ngành Công nghệ Thông tin (Áp dụng từ khóa 18 - 2023)                   | https://student.uit.edu.vn/content/cu-nhan-nganh-cong-nghe-thong-tin-ap-dung-tu-khoa-18-2023                   | 2026-09-19 / `not-stated` | 10,416   | audience=`student`; department=`it`; category=`curriculum-selection`; language=`vi`; cohort=`K18` |
| 8   | Lựa chọn học phần — Cử nhân ngành Mạng máy tính và Truyền thông dữ liệu (Áp dụng từ khóa 18 - 2023) | https://student.uit.edu.vn/content/cu-nhan-nganh-mang-may-tinh-va-truyen-thong-du-lieu-ap-dung-tu-khoa-18-2023 | 2026-09-19 / `not-stated` | 7,392    | audience=`student`; department=`nc`; category=`curriculum-selection`; language=`vi`; cohort=`K18` |
| 9   | Lựa chọn học phần — Cử nhân ngành Kỹ thuật Phần mềm (Áp dụng từ khóa 18 - 2023)                     | https://student.uit.edu.vn/content/cu-nhan-nganh-ky-thuat-phan-mem-ap-dung-tu-khoa-18-2023                     | 2026-09-19 / `not-stated` | 7,602    | audience=`student`; department=`se`; category=`curriculum-selection`; language=`vi`; cohort=`K18` |
| 10  | Bảng tóm tắt môn học UIT                                                                            | https://student.uit.edu.vn/content/bang-tom-tat-mon-hoc                                                        | 2026-09-19 / `not-stated` | 204,964  | audience=`staff`; department=`all`; category=`course-description`; language=`vi`                  |

_Số ký tự tính trên phần nội dung Markdown sau YAML front matter, loại khoảng trắng đầu/cuối; không tính metadata để phản ánh lượng văn bản đưa vào chunking. Ngày `2026-09-19` là ngày chuẩn hóa theo yêu cầu, chưa được xác minh là ngày crawl thực tế. Nguồn gốc của 10 tài liệu được đối chiếu với `data/dang-ky-hoc-phan/sources.csv`._

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**

- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata        | Kiểu                         | Ví dụ giá trị                                               | Tại sao hữu ích cho truy xuất (retrieval)?                                                                            |
| ---------------------- | ---------------------------- | ----------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `doc_id`               | string                       | `course-list`                                               | Định danh tài liệu gốc; gắn vào mọi chunk để truy vết, đối chiếu nguồn và xóa tài liệu.                               |
| `title`                | string                       | `Danh mục môn học UIT`                                      | Hiển thị tên nguồn và hỗ trợ xác định chương trình phù hợp.                                                           |
| `source_url`           | string (URL)                 | `https://student.uit.edu.vn/danh-muc-mon-hoc-dai-hoc`       | Dẫn về trang nguồn để kiểm tra câu trả lời.                                                                           |
| `retrieved_at`         | string (YYYY-MM-DD)          | `2026-09-19`                                                | Theo dõi ngày được ghi trong corpus; đây là ngày chuẩn hóa do người dùng chỉ định, không phải ngày crawl đã xác minh. |
| `document_version`     | string                       | `not-stated`                                                | Phân biệt phiên bản/ngày hiệu lực nếu nguồn công bố; không tự suy diễn phiên bản.                                     |
| `audience`             | string (enum)                | `student; staff`                                            | Cho phép lọc theo nhóm đối tượng; nhãn staff là phân loại do người dùng gán, cần kiểm chứng tính phù hợp.             |
| `department`           | string                       | `ai; all`                                                   | Lọc theo ngành/khoa hoặc danh mục dùng chung, giảm lẫn dữ liệu các ngành.                                             |
| `category`             | string                       | `curriculum-selection; course-catalog; course-description`  | Giới hạn loại nội dung khi truy xuất môn học, chương trình hoặc mô tả.                                                |
| `language`             | string                       | `vi`                                                        | Lọc văn bản theo ngôn ngữ tiếng Việt.                                                                                 |
| `cohort`               | string                       | `K18`                                                       | Lọc chương trình theo khóa tuyển sinh; chuỗi rỗng ở tài liệu danh mục chung.                                          |
| `raw_file`             | string                       | `course_list.json`                                          | Truy vết file JSON thô đã dùng để tạo Markdown.                                                                       |
| `processed_at`         | string (YYYY-MM-DD)          | `2026-09-19`                                                | Phân biệt ngày xử lý/chuyển đổi với thời điểm lấy dữ liệu từ nguồn.                                                   |
| `original_crawled_at`  | string (timestamp hoặc rỗng) | `2026-01-27 08:17:16`                                       | Bảo tồn timestamp crawl gốc ở các JSON chương trình; rỗng khi không có.                                               |
| `retrieval_date_basis` | string                       | `user-assigned-not-verified`                                | Nêu rõ nguồn gốc của trường ngày, tránh coi ngày chuẩn hóa là chứng cứ crawl.                                         |
| `audience_basis`       | string                       | `source-context; user-assigned-for-lab-not-source-verified` | Phân biệt nhãn suy ra từ ngữ cảnh và nhãn cấu hình chưa được nguồn xác nhận.                                          |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` + HeadingChunker trên 3 tài liệu mẫu:

| Tài liệu                   | Chiến lược (Strategy)            | Số lượng Chunk | Độ dài trung bình | Ghi chú                                            |
| -------------------------- | -------------------------------- | -------------- | ----------------- | -------------------------------------------------- |
| course-list.md (287K)      | FixedSizeChunker (`fixed_size`)  | 575            | 499.6             | Cắt đều, có overlap                                |
|                            | SentenceChunker (`by_sentences`) | 1              | 287,245.0         | **Fail** - toàn bộ file thành 1 chunk (ít dấu câu) |
|                            | RecursiveChunker (`recursive`)   | 956            | 300.5             | Giữ cấu trúc heading, merge chunk nhỏ              |
|                            | HeadingChunker (`heading_based`) | 1023           | 279.8             | Tách theo ##/###, giữ heading trong chunk          |
| course-summaries.md (205K) | FixedSizeChunker                 | 410            | 499.9             | Cắt đều                                            |
|                            | SentenceChunker                  | 337            | 606.3             | Tách theo câu, chunk to hơn                        |
|                            | RecursiveChunker                 | 535            | 383.1             | Cân bằng                                           |
|                            | HeadingChunker                   | 840            | 242.9             | Nhiều chunk nhỏ theo heading                       |
| k18-ai.md (9.7K)           | FixedSizeChunker                 | 20             | 484.0             | Cắt đều                                            |
|                            | SentenceChunker                  | 31             | 311.3             | Tách câu 3/1 chunk                                 |
|                            | RecursiveChunker                 | 21             | 461.0             | Giống fixed size (văn bản đã có heading)           |
|                            | HeadingChunker                   | 31             | 310.9             | Tương tự sentence chunker                          |

### Chiến lược của từng thành viên

> Mỗi thành viên điền một khối dưới đây (copy thêm nếu nhóm có nhiều hơn 3 người).

**Thành viên 1 — Đỗ Trịnh Huy Hoàng (2A202602392)**

- **Loại chiến lược:** Sentence Chunker (`by_sentences`)
- **Mô tả & lý do chọn cho chủ đề này:** Chunk theo câu phù hợp với truy vấn yêu cầu thông tin cụ thể (ví dụ: "hạn mượn sách bao nhiêu ngày", "IT001 dạy ở học kỳ nào") vì mỗi câu trong tài liệu thường chứa một thông tin hoàn chỉnh. Với chủ đề đăng ký học phần UIT, các câu trong tài liệu chương trình đào tạo thường nêu rõ quy định, điều kiện, thời gian — tách theo câu giúp truy xuất chính xác hơn.
- **Code snippet (nếu custom):**

```python
# Sử dụng SentenceChunker có sẵn từ src.chunking
from src.chunking import SentenceChunker
chunker = SentenceChunker(max_sentences_per_chunk=3)
chunks = chunker.chunk(document_content)
```

**Thành viên 2 — Nguyễn Phạm Oanh Oanh (2A202602665)**

- **Loại chiến lược:** Fixed Size Chunker (`fixed_size`)
- **Mô tả & lý do chọn:** Chunk theo kích thước cố định với overlap đảm bảo không mất thông tin ở biên. Chiến lược này đơn giản, ổn định và phù hợp khi tài liệu có cấu trúc đều đặn (bảng biểu, danh sách môn học). Với corpus UIT có nhiều bảng tín chỉ, danh sách môn học, fixed chunker giữ được ngữ cảnh liên tục giữa các chunk.
- **Code snippet (nếu custom):**

```python
from src.chunking import FixedSizeChunker
chunker = FixedSizeChunker(chunk_size=500, overlap=50)
chunks = chunker.chunk(document_content)
```

**Thành viên 3 — Hoàng Bích Ngọc (2A202602766)**

- **Loại chiến lược:** Heading Chunker (`heading`)
- **Mô tả & lý do chọn:** Chunk theo heading/section phù hợp với tài liệu quy định có cấu trúc mục rõ ràng. Mỗi heading trở thành một chunk, section dài quá ngưỡng sẽ fallback sang recursive. Với tài liệu chương trình đào tạo UIT có nhiều mục (## Điều khoản, ### Mục), heading chunker giúp mỗi chunk tương ứng một đơn vị ngữ nghĩa trọn vẹn.
- **Code snippet (nếu custom):**

```python
# Sử dụng HeadingChunker có sẵn từ src.chunking
from src.chunking import HeadingChunker
chunker = HeadingChunker(chunk_size=500)
chunks = chunker.chunk(document_content)
```

**Thành viên 4 — Trần Thế Anh**

- **Loại chiến lược:** Custom — `HeadingChunker` kết hợp `RecursiveChunker` fallback và metadata pre-filter.
- **Mô tả & lý do chọn cho chủ đề này:** Dữ liệu chương trình đào tạo là Markdown có nhiều heading và bảng, vì vậy tôi chia tài liệu theo heading để giữ tên section đi cùng nội dung. Section dài hơn `chunk_size` được chia tiếp bằng `RecursiveChunker`; trước khi xếp hạng, tôi lọc theo `audience`, `department` và `cohort` để thu hẹp đúng ngành và khóa.
- **Code snippet (nếu custom):**

```python
chunker = HeadingChunker(chunk_size=500)
chunks = chunker.chunk(document_text)

results = store.search_with_filter(
    query,
    top_k=3,
    metadata_filter={
        "audience": "student",
        "department": "se",
        "cohort": "K18",
    },
)
```

**Thành viên 5 — Vũ Hiếu Thiên (2A202602867)**

- **Loại chiến lược:** Recursive (`recursive`) + OpenAI Embedding
- **Mô tả & lý do chọn cho chủ đề này:** Implement `RecursiveChunker` (đệ quy với separator ưu tiên, merge chunk nhỏ) và `OpenAIEmbedder` (có in-memory cache). Recursive chunker cân bằng giữa ngữ cảnh section và độ dài chunk; kết hợp OpenAI `text-embedding-3-small` để có vector ngữ nghĩa thực sự.
- **Code snippet (nếu custom):**

```python
chunker = RecursiveChunker(chunk_size=500)
chunks = chunker.chunk(document_content)

embedder = OpenAIEmbedder(model_name="text-embedding-3-small")
store = EmbeddingStore(embedding_fn=embedder)
store.add_documents(all_docs)

results = store.search_with_filter(
    query,
    top_k=3,
    metadata_filter={"audience": "student"},
)
```

### So Sánh Giữa Các Thành Viên (OpenAI embeddings)

| Thành viên            | Chiến lược (Strategy)        | Điểm truy xuất (/10) | Top-1 / 5 | Top-3 / 5 | Điểm mạnh                                                                                   | Điểm yếu                                                                 |
| --------------------- | ---------------------------- | -------------------- | --------- | --------- | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Đỗ Trịnh Huy Hoàng    | Sentence (`by_sentences`)    | 0/10                 | 0/5       | 1/5       | N/A — chỉ chạy với mock embedding                                                           | Mock embedding không phân biệt ngữ nghĩa → mọi truy vấn trả về cùng doc   |
| Nguyễn Phạm Oanh Oanh | Fixed (`fixed_size`)         | **9/10**             | 4/5       | 5/5       | Top-3 recall hoàn hảo; tìm được Q1 (course-list), Q2 (k18-ai), Q4 (k18-se), Q5 (library-student) ở top1 | Q3 thất bại — course-summaries lấn át k18-ai                              |
| Hoàng Bích Ngọc       | Heading (`heading`)          | 8/10                 | 4/5       | 4/5       | Top-1 accuracy 4/5; tìm đúng Q1, Q2, Q4, Q5 ở top1                                           | Q3 thất bại — course-list lấn át k18-ai                                   |
| Trần Thế Anh          | Custom (Heading + Recursive) | 7/10                 | 3/5       | 4/5       | Metadata filter giúp Q5 tìm đúng; Q2, Q4 đúng ngành                                         | Q1, Q3 thất bại — vector embedding không ưu tiên course-list/k18-ai      |
| Vũ Hiếu Thiên         | Recursive (`recursive`)      | 7/10                 | 3/5       | 4/5       | Cơ chế merge chunk nhỏ giữ ngữ cảnh tốt; tìm đúng Q2, Q4, Q5 ở top1                          | Q1, Q3 thất bại — cùng lỗi với recursive                                |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**

> Với OpenAI embeddings, **Fixed chunker đạt điểm cao nhất (9/10)** — top3 recall hoàn hảo 5/5, chỉ Q3 miss top1. Heading chunker gần bằng (8/10). Recursive và Custom đều đạt 7/10.
>
> **Fixed chunker** mạnh nhất vì corpus UIT có cấu trúc đều (bảng môn học, danh sách mã), và OpenAI embedding hiểu ngữ nghĩa tốt → mỗi chunk chứa đủ context cho similarity match.
>
> **Heading chunker** cũng mạnh (8/10) vì tách theo section giữ ngữ cảnh đơn vị thông tin.
>
> Tuy nhiên, **câu hỏi Q3 (IT001 dạy ở học kỳ nào?)** là thách thức chung: course-list/course-summaries (chứa mô tả môn IT001) rank cao hơn k18-ai (chứa lịch học kỳ). Cần BM25/hybrid search hoặc reranker để cải thiện.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| #   | Câu hỏi (Query)                                                                   | Câu trả lời chuẩn (Gold Answer)                                                                            | Chunk nào chứa thông tin?                                            |
| --- | --------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| 1   | Theo danh mục môn học UIT, CS106 yêu cầu môn học trước nào?                       | IT003                                                                                                      | course-list                                                          |
| 2   | Điều kiện để được đăng ký chuyên ngành Trí tuệ Nhân tạo K18 là gì?                | Hoàn thành khối kiến thức cơ sở ngành (≥ 57 TC) và đáp ứng điều kiện riêng của ngành                       | k18-ai-cu-nhan-nganh-tri-tue-nhan-tao-ap-dung-tu-khoa-18-20-83330a33 |
| 3   | Theo kế hoạch giảng dạy K18 AI, IT001 (Nhập môn Lập trình) được dạy ở học kỳ nào? | Học kỳ 1                                                                                                   | k18-ai-cu-nhan-nganh-tri-tue-nhan-tao-ap-dung-tu-khoa-18-20-83330a33 |
| 4   | Liệt kê các môn tự chọn chuyên ngành của Kỹ thuật Phần mềm K18 (14 tín chỉ)       | 14 tín chỉ tự chọn chuyên ngành, bao gồm các môn theo định hướng SE                                        | k18-se-cu-nhan-nganh-ky-thuat-phan-mem-ap-dung-tu-khoa-18-2-e01fcd2c |
| 5   | Hạn mượn sách tại thư viện UIT là bao nhiêu ngày?                                 | Sinh viên: 21 ngày (sách tham khảo/giáo trình); Giảng viên: 90 ngày (giáo trình), 21 ngày (sách tham khảo) | library-loan-student                                                 |

### Tổng hợp chất lượng truy xuất của nhóm (OpenAI embeddings)

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-1 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

| #   | Câu hỏi                               | Chiến lược tốt nhất cho câu này  | Top-1 accuracy (OpenAI) | Ghi chú                                                                |
| --- | ------------------------------------- | -------------------------------- | ----------------------- | ----------------------------------------------------------------------- |
| 1   | CS106 yêu cầu môn học trước nào?      | Fixed (9/10)                     | ✅ course-list ở top1   | Fixed + OpenAI tìm thấy course-list ở top1 (score=0.588)                |
| 2   | Điều kiện đăng ký chuyên ngành AI K18 | Heading/Fixed/Recursive          | ✅ k18-ai ở top1        | Cả 3 chiến lược tìm thấy k18-ai ở top1 với filter department=ai         |
| 3   | IT001 dạy ở học kỳ nào?               | — (tất cả thất bại)              | ❌                        | Gold doc (k18-ai) không trong top3; course-list/course-summaries chiếm top3  |
| 4   | Môn tự chọn chuyên ngành SE K18       | Heading/Fixed/Recursive          | ✅ k18-se ở top1        | Cả 3 chiến lược tìm thấy k18-se ở top1 với filter department=se         |
| 5   | Hạn mượn sách thư viện UIT            | Fixed/Heading/Recursive          | ✅ library-loan-student ở top1 | Tất cả chiến lược tìm thấy library-loan-student ở top1 với filter audience=student |

**Top-1 accuracy tổng hợp (OpenAI embeddings):**

| Chiến lược | Điểm | Top-1 | Top-3 |
| ---------- | ---- | ----- | ----- |
| Fixed      | 9/10 | 4/5   | 5/5   |
| Heading    | 8/10 | 4/5   | 4/5   |
| Recursive  | 7/10 | 3/5   | 4/5   |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**

> **Có, metadata filter giúp ích rất lớn ở Q5 (hạn mượn sách) và Q2, Q4 (chuyên ngành).** Câu hỏi Q5 không nêu rõ người hỏi, nhưng corpus có tài liệu cho sinh viên (21 ngày) và giảng viên (90/21 ngày). **Với filter `audience=student`:** tất cả 3 chiến lược đều tìm thấy `library-loan-student` ở top1. Nếu không filter, retrieval sẽ lẫn thông tin hai đối tượng.
>
> Ở Q2 và Q4, filter `department` (ai, se) giúp thu hẹp tài liệu đúng lên top1 — đây là yếu tố then chốt để Q2, Q4 đạt top1. Q1 không cần filter (course-list là tài liệu chung).
>
> **Kết luận:** Metadata filter + OpenAI embeddings cho top1 accuracy 4/5 ở Fixed chunker, vượt trội so với mock embedding (2/5).

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**

> 1. **Mock embedding làm sai lệch kết quả retrieval — chuyển sang OpenAI embeddings cải thiện đáng kể.** Với MockEmbedder (băm MD5 + random), kết quả benchmark không phản ánh chất lượng thực sự: cả 3 chiến lược (fixed, recursive, heading) đều chỉ đạt 5/10 (top1 accuracy 2/5) — không phân biệt được. **Khi chuyển sang OpenAI `text-embedding-3-small`, Fixed chunker đạt 9/10 (top1 accuracy 4/5)** — chứng minh embedding thật mới nắm bắt được ngữ nghĩa.
> 2. **Fixed chunker tốt nhất với OpenAI (9/10), Heading gần bằng (8/10), Recursive và Custom đều 7/10.** Với mock, heading chunker duy nhất tìm đúng tài liệu cho Q2 (AI) và Q4 (SE) ở top1. Với OpenAI, Fixed tìm thấy course-list ở top1 cho Q1 và library-loan-student cho Q5 — truy vấn tra cứu dữ liệu số liệu cụ thể. Heading cũng mạnh vì giữ ngữ cảnh section.
> 3. **Metadata filter là chìa khóa cho Q5 (hạn mượn sách).** Câu hỏi về hạn mượn sách cần phân biệt đối tượng (sinh viên 21 ngày/giảng viên 90 ngày). **Với OpenAI + filter `audience=student`:** tất cả chiến lược tìm `library-loan-student` ở top1 (2 điểm). Nếu không filter, kết quả sẽ lẫn thông tin hai đối tượng.

**Bài học rút ra khi so sánh trong nhóm:**

> Cùng một bộ tài liệu nhưng chiến lược chunking khác nhau cho kết quả hoàn toàn khác biệt. **Với mock embedding**, heading chunker dẫn đầu (5/10) — tìm đúng Q2, Q4 nhờ giữ ngữ cảnh section; fixed tìm được Q1; recursive tìm được Q5. Sentence chunker luôn trả về course-summaries cho mọi truy vấn (0/10).
> **Với OpenAI embedding**, fixed chunker vượt trội (9/10, top1 accuracy 4/5) — tìm đúng Q1, Q2, Q4, Q5 ở top1. Heading gần bằng (8/10, top1 4/5). Recursive và Custom đều 7/10. Cách chunking quyết định chất lượng retrieval **khi embedding hiểu được ngữ nghĩa**. Tuy nhiên, **Q3 (IT001 học kỳ nào?)** vẫn thất bại ở mọi chiến lược — lịch học kỳ trong k18-ai bị lấn át bởi course-list/course-summaries.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**

> 1. Sử dụng embedding model thật (OpenAI/sentence-transformers) thay vì mock để benchmark phản ánh đúng chất lượng retrieval.
> 2. Tách tài liệu library-loan-student theo audience (student/faculty) để metadata filter hoạt động hiệu quả hơn.
> 3. Thêm **hybrid search (semantic + BM25/keyword)** để cải thiện kết quả cho Q3 — truy vấn mang tính sự kiện (IT001, học kỳ 1) cần keyword matching để tìm đúng trong k18-ai thay vì bị lấn át bởi course-list.
> 4. **Fixed chunker là lựa chọn tối ưu** cho corpus UIT (cấu trúc đều, bảng môn học) với OpenAI embeddings — top3 recall 5/5.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí                                 | Điểm tự đánh giá |
| ---------------------------------------- | ---------------- |
| Lựa chọn tài liệu (Document Set Quality) | 9/10             |
| Thiết kế chiến lược (Strategy Design)    | 14/15            |
| Chất lượng truy xuất (Retrieval Quality) | 9/10             |
| Thuyết trình (Demo)                      | 5/5              |
| **Tổng phần nhóm**                       | **37/40**        |

**Giải thích:**

- **Lựa chọn tài liệu (9/10):** 12 tài liệu (10 chương trình đào tạo + 2 thư viện), metadata đầy đủ, chủ đề phù hợp. Đã thêm tài liệu thư viện (library-loan-student/faculty) với metadata_filter test.
- **Thiết kế chiến lược (14/15):** 4+1 chiến lược khác nhau (sentence, fixed, heading, custom heading+recursive+filter, recursive). Heading chunker đạt 8/10 với OpenAI. Fixed chunker dẫn đầu với 9/10. Phân tích so sánh chi tiết giữa mock và OpenAI.
- **Chất lượng truy xuất (9/10):** Với OpenAI embeddings, Fixed chunker tìm đúng Q1, Q2, Q4, Q5 ở top1 (4/5). Q3 thất bại (course-list lấn át k18-ai). Top-3 recall 5/5 với Fixed.
- **Thuyết trình (5/5):** Demo đầy đủ với benchmark OpenAI, so sánh 3 chunker strategies, insights rõ rệt.
