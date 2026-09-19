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

Chạy `ChunkingStrategyComparator().compare()` trên 2-3 tài liệu:

| Tài liệu | Chiến lược (Strategy)            | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
| -------- | -------------------------------- | -------------- | ----------------- | ------------------------ |
|          | FixedSizeChunker (`fixed_size`)  |                |                   |                          |
|          | SentenceChunker (`by_sentences`) |                |                   |                          |
|          | RecursiveChunker (`recursive`)   |                |                   |                          |

### Chiến lược của từng thành viên

> Mỗi thành viên điền một khối dưới đây (copy thêm nếu nhóm có nhiều hơn 3 người).

**Thành viên 1 — [Tên]**

- **Loại chiến lược:** [FixedSize / Sentence / Recursive / custom]
- **Mô tả & lý do chọn cho chủ đề này:** _(2-3 câu)_
- **Code snippet (nếu custom):**

```python
# Dán mã nguồn (implementation) vào đây
```

**Thành viên 2 — [Tên]**

- **Loại chiến lược:**
- **Mô tả & lý do chọn:**
- **Code snippet (nếu custom):**

**Thành viên 3 — [Tên]**

- **Loại chiến lược:**
- **Mô tả & lý do chọn:**
- **Code snippet (nếu custom):**

### So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
| ---------- | --------------------- | -------------------- | --------- | -------- |
|            |                       |                      |           |          |
|            |                       |                      |           |          |
|            |                       |                      |           |          |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**

> _Viết 2-3 câu — đây là phần được đánh giá cao nhất (khả năng suy nghĩ & giải thích):_

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| #   | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
| --- | --------------- | ------------------------------- | ------------------------- |
| 1   |                 |                                 |                           |
| 2   |                 |                                 |                           |
| 3   |                 |                                 |                           |
| 4   |                 |                                 |                           |
| 5   |                 |                                 |                           |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

| #   | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
| --- | ------- | ------------------------------- | ------------------------------- | ------- |
| 1   |         |                                 |                                 |         |
| 2   |         |                                 |                                 |         |
| 3   |         |                                 |                                 |         |
| 4   |         |                                 |                                 |         |
| 5   |         |                                 |                                 |         |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**

> _Viết 2-3 câu:_

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**

> _Liệt kê 2-3 ý:_

**Bài học rút ra khi so sánh trong nhóm:**

> _Viết 2-3 câu — cùng tài liệu nhưng chiến lược khác nhau dẫn tới khác biệt gì?_

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**

> _Viết 2-3 câu:_

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí                                 | Điểm tự đánh giá |
| ---------------------------------------- | ---------------- |
| Lựa chọn tài liệu (Document Set Quality) | / 10             |
| Thiết kế chiến lược (Strategy Design)    | / 15             |
| Chất lượng truy xuất (Retrieval Quality) | / 10             |
| Thuyết trình (Demo)                      | / 5              |
| **Tổng phần nhóm**                       | **/ 40**         |
