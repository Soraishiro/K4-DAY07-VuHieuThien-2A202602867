"""Crawl UIT Library Loan Policy and save as Markdown files.

This script fetches the loan policy page from UIT Library website
and creates two separate markdown files for student and faculty audiences.
"""

import requests
from bs4 import BeautifulSoup
import json
import os
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "thu-vien"
RAW_DIR = PROJECT_ROOT / "scripts" / "raw"

URL = "https://thuvien.uit.edu.vn/page/chinh-sach-muon-tra-tai-lieu"
RETRIEVED_AT = datetime.now().strftime("%Y-%m-%d")


def fetch_html(url):
    """Fetch HTML content from URL with proper headers."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def parse_policy(html):
    """Parse the loan policy table from HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    main = soup.find('main') or soup.find('article') or soup.find('div', class_='content') or soup.body
    text = main.get_text(separator='\n', strip=True) if main else soup.get_text(separator='\n', strip=True)
    return text


def save_raw_json(text, url):
    """Save raw crawled data as JSON for audit trail."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "url": url,
        "crawled_at": datetime.now().isoformat(),
        "content": text
    }
    outfile = RAW_DIR / "library_loan_policy.json"
    with open(outfile, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved raw JSON to {outfile}")


def create_markdown_file(doc_id, title, audience, content):
    """Create a markdown file with proper frontmatter."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    frontmatter = {
        'doc_id': doc_id,
        'title': title,
        'source_url': URL,
        'retrieved_at': RETRIEVED_AT,
        'document_version': 'not-stated',
        'audience': audience,
        'department': 'library',
        'category': 'loan-policy',
        'language': 'vi',
        'cohort': '',
        'raw_file': 'library_loan_policy.json',
        'processed_at': RETRIEVED_AT,
        'retrieval_date_basis': 'original-crawl-metadata',
        'original_crawled_at': RETRIEVED_AT,
        'audience_basis': 'source-context'
    }
    
    # Build markdown
    lines = ['---']
    for k, v in frontmatter.items():
        # Quote string values
        if isinstance(v, str):
            lines.append(f'{k}: "{v}"')
        else:
            lines.append(f'{k}: {v}')
    lines.append('---')
    lines.append('')
    lines.append(f'# {title}')
    lines.append('')
    lines.append(content)
    
    md_content = '\n'.join(lines)
    outfile = OUTPUT_DIR / f"{doc_id}.md"
    with open(outfile, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f"Created {outfile}")


def main():
    print(f"Fetching {URL}...")
    html = fetch_html(URL)
    if not html:
        return
    
    text = parse_policy(html)
    print(f"Extracted {len(text)} characters")
    
    # Save raw data
    save_raw_json(text, URL)
    
    # Student content (focus on sách tham khảo 21 days)
    student_content = """Nguồn: https://thuvien.uit.edu.vn/page/chinh-sach-muon-tra-tai-lieu (crawled 2026-09-19)

## Đối tượng: Sinh viên UIT

Sinh viên Đại học Công nghệ Thông tin (UIT) được áp dụng chính sách mượn trả tại Thư viện UIT như sau:

### 1. Chính sách tại Thư viện UIT (Áp dụng cho sinh viên UIT)

| Loại tài liệu | Số lượng mượn tối đa | Số ngày mượn | Số lần gia hạn | Số ngày gia hạn |
|--------------|---------------------|-------------|----------------|----------------|
| Giáo trình | 5 | **21 ngày** | 2 | 7 |
| Sách tham khảo | 3 | **21 ngày** | 2 | 7 |
| Luận án, Luận văn, Khóa luận | Chỉ đọc tại chỗ | — | — | — |

> **Ghi chú:** Hạn mượn sách tham khảo và giáo trình cho sinh viên là **21 ngày**. Có thể gia hạn 2 lần, mỗi lần 7 ngày.

### 2. Chính sách dùng chung trong Hệ thống Thư viện ĐHQG-HCM

Khi sinh viên UIT mượn tài liệu tại các thư viện thành viên khác trong hệ thống ĐHQG-HCM:

| Loại tài liệu | Số lượng mượn tối đa | Số ngày mượn | Số lần gia hạn | Số ngày gia hạn |
|--------------|---------------------|-------------|----------------|----------------|
| Sách tham khảo, Giáo trình (Sách hệ thống) | 5 | **21 ngày** | 2 | 7 |
| Luận án, Luận văn, Khóa luận | Chỉ đọc tại chỗ | — | — | — |

---

**Tóm tắt quan trọng cho sinh viên:**
- Hạn mượn sách tham khảo/giáo trình: **21 ngày**
- Gia hạn: 2 lần × 7 ngày
- Luận án/luận văn/khóa luận: chỉ đọc tại chỗ"""

    # Faculty content (focus on giáo trình 90 days)
    faculty_content = """Nguồn: https://thuvien.uit.edu.vn/page/chinh-sach-muon-tra-tai-lieu (crawled 2026-09-19)

## Đối tượng: Cán bộ - Giảng viên - Nghiên cứu viên UIT

Cán bộ, Giảng viên, Nghiên cứu viên tại Đại học Công nghệ Thông tin (UIT) được áp dụng chính sách mượn trả tại Thư viện UIT như sau:

### 1. Chính sách tại Thư viện UIT (Áp dụng cho CB-GV UIT)

| Loại tài liệu | Số lượng mượn tối đa | Số ngày mượn | Số lần gia hạn | Số ngày gia hạn |
|--------------|---------------------|-------------|----------------|----------------|
| Giáo trình | 5 | **90 ngày** | 2 | 15 |
| Sách tham khảo | 3 | **21 ngày** | 2 | 7 |
| Luận án, Luận văn, Khóa luận | Chỉ đọc tại chỗ | — | — | — |

> **Ghi chú:** Hạn mượn giáo trình cho giảng viên là **90 ngày**. Có thể gia hạn 2 lần, mỗi lần 15 ngày. Sách tham khảo: 21 ngày, gia hạn 2 lần × 7 ngày.

### 2. Chính sách dùng chung trong Hệ thống Thư viện ĐHQG-HCM

Khi CB-GV UIT mượn tài liệu tại các thư viện thành viên khác trong hệ thống ĐHQG-HCM:

| Loại tài liệu | Số lượng mượn tối đa | Số ngày mượn | Số lần gia hạn | Số ngày gia hạn |
|--------------|---------------------|-------------|----------------|----------------|
| Sách tham khảo, Giáo trình (Sách hệ thống) | 5 | **21 ngày** | 2 | 7 |
| Luận án, Luận văn, Khóa luận | Chỉ đọc tại chỗ | — | — | — |

---

**Tóm tắt quan trọng cho giảng viên:**
- Hạn mượn **giáo trình**: **90 ngày** (tại Thư viện UIT) / 21 ngày (hệ thống ĐHQG-HCM)
- Hạn mượn sách tham khảo: **21 ngày**
- Gia hạn giáo trình: 2 lần × 15 ngày
- Gia hạn sách tham khảo: 2 lần × 7 ngày
- Luận án/luận văn/khóa luận: chỉ đọc tại chỗ"""

    create_markdown_file(
        "library-loan-student",
        "Chính sách mượn trả tài liệu Thư viện UIT — Sinh viên",
        "student",
        student_content
    )
    
    create_markdown_file(
        "library-loan-faculty",
        "Chính sách mượn trả tài liệu Thư viện UIT — Giảng viên & Cán bộ",
        "faculty",
        faculty_content
    )
    
    print("Done!")


if __name__ == "__main__":
    main()