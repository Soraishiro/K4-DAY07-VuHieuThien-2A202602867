"""
Dedicated crawler for linked (Birmingham/Newcastle) programs.

These programs have a different HTML structure:
- No accordion sections
- Courses in plain HTML tables with columns: [STT, Vietnamese Name, English Name, Credits]
- Phases (Giai đoạn 1, 2) instead of standard categories

Output matches standard program JSON structure with:
- code, name, credits, prerequisites, description
"""

import json
import re
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime
from typing import Optional


# URLs for linked programs - matching existing filename convention
# Note: K19 Birmingham reuses K18 (same URL), K20 CS Birmingham also reuses K18
LINKED_PROGRAMS = {
    "K18": [
        {
            "filename": "K18_CS_Khoa_học_Máy_tính_Birmingham_City.json",
            "faculty": "CS",
            "url": "https://student.uit.edu.vn/content/cu-nhan-nganh-khoa-hoc-may-tinh-chuong-trinh-lien-ket-voi-dh-birmingham-city-ap-dung-tu-0",
        },
        {
            "filename": "K18_NC_Mạng_máy_tính_Birmingham_City.json",
            "faculty": "NC",
            "url": "https://student.uit.edu.vn/content/cu-nhan-nganh-mang-may-tinh-va-toan-thong-tin-chuong-trinh-lien-ket-voi-dh-birmingham-city-1",
        },
    ],
    "K19": [
        {
            "filename": "K19_CS_Khoa_học_Máy_tính_Birmingham_City.json",
            "faculty": "CS",
            "url": "https://student.uit.edu.vn/content/cu-nhan-nganh-khoa-hoc-may-tinh-chuong-trinh-lien-ket-voi-dh-birmingham-city-ap-dung-tu-0",
            "reuses": "K18",
        },
        {
            "filename": "K19_NC_Mạng_máy_tính_Birmingham_City.json",
            "faculty": "NC",
            "url": "https://student.uit.edu.vn/content/cu-nhan-nganh-mang-may-tinh-va-toan-thong-tin-chuong-trinh-lien-ket-voi-dh-birmingham-city-1",
            "reuses": "K18",
        },
    ],
    "K20": [
        {
            "filename": "K20_CE_Newcastle.json",
            "faculty": "CE",
            "url": "https://student.uit.edu.vn/content/cu-nhan-nganh-ky-thuat-he-thong-may-tinh-chuong-trinh-lien-ket-voi-truong-dai-hoc-newcastle",
        },
        {
            "filename": "K20_NC_Mạng_máy_tính_Birmingham_City.json",
            "faculty": "NC",
            "url": "https://student.uit.edu.vn/content/cu-nhan-nganh-mang-may-tinh-va-toan-thong-tin-chuong-trinh-lien-ket-voi-dh-birmingham-city-2",
        },
        {
            "filename": "K20_CS_Khoa_học_Máy_tính_Birmingham_City.json",
            "faculty": "CS",
            "url": "https://student.uit.edu.vn/content/cu-nhan-nganh-khoa-hoc-may-tinh-chuong-trinh-lien-ket-voi-dh-birmingham-city-ap-dung-tu-0",
            "reuses": "K18",
        },
    ],
}

OUTPUT_DIR = Path("data/raw/student_portal/curriculum")


def fetch_page(url: str) -> Optional[BeautifulSoup]:
    """Fetch and parse a webpage."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def extract_courses_from_table(table: BeautifulSoup) -> list[dict]:
    """
    Extract courses from a Birmingham/Newcastle table.
    Returns courses in standard format: code, name, credits, prerequisites, description
    """
    courses = []
    rows = table.find_all("tr")

    for row in rows:
        cols = row.find_all(["td", "th"])
        if len(cols) < 3:
            continue

        texts = [col.get_text(strip=True) for col in cols]

        # Skip header rows
        first_col = texts[0].lower()
        if first_col in ["stt", "mã môn học", "stts", "học kỳ", "", "tiếng việt"]:
            continue
        if "tiếng anh" in first_col:
            continue

        # Skip summary rows
        if "tổng số" in first_col.lower() or "giai đoạn" in first_col.lower():
            continue

        # Parse course data
        # Birmingham format: [STT, Vietnamese Name, English Name, Credits/CATS]
        if texts[0].isdigit() and len(texts) >= 4:
            vi_name = texts[1]
            en_name = texts[2]
            credits = _extract_credits(texts[3])

            # Skip if Vietnamese name is too short or is a header
            if vi_name and len(vi_name) > 3:
                course = {
                    "code": "",  # Birmingham doesn't use standard codes
                    "name": f"{vi_name} ({en_name})" if en_name else vi_name,
                    "credits": credits,
                    "prerequisites": [],
                    "description": f"English: {en_name}" if en_name else "",
                }
                courses.append(course)

        # Newcastle format: [Code, Name, Credits]
        elif len(texts) >= 2 and re.match(r"^[A-Z]{2,4}\d{3,4}", texts[0]):
            course = {
                "code": texts[0],
                "name": texts[1],
                "credits": _extract_credits(texts[-1]) if len(texts) > 2 else None,
                "prerequisites": [],
                "description": "",
            }
            if course["name"]:
                courses.append(course)

    return courses


def _extract_credits(text: str) -> Optional[int]:
    """Extract credit number from text."""
    if not text or text == "-":
        return None
    match = re.search(r"^\d+$", str(text).strip())
    return int(match.group()) if match else None


def extract_program_data(soup: BeautifulSoup, url: str) -> dict:
    """Extract all program data from page."""
    # Get program title from h1
    title_elem = soup.find("h1", class_="page-header")
    if not title_elem:
        title_elem = soup.find("h1")
    title = title_elem.get_text(strip=True) if title_elem else "Unknown Program"

    # Find content area
    content = soup.find("div", class_="field-item")
    if not content:
        content = soup.find("article") or soup

    # Find all tables with course data and extract
    # Birmingham pages have 2 tables:
    # 1. Course list table (columns: STT, Vietnamese Name, English Name, Credits)
    # 2. Hours breakdown table (columns: Học kỳ, Tên môn học, Scheduled Learning, etc.) - SKIP THIS
    tables = content.find_all("table")
    phase1_courses = []
    phase2_courses = []

    # Only process first table (course list)
    if tables:
        table = tables[0]
        rows = table.find_all("tr")
        current_phase = 1

        for row in rows:
            cols = row.find_all(["td", "th"])
            if len(cols) < 3:
                continue

            texts = [col.get_text(strip=True) for col in cols]
            first_col = texts[0].lower()

            # Detect phase markers
            if "giai đoạn 2" in first_col or "phase 2" in first_col:
                current_phase = 2
                continue
            if "giai đoạn 1" in first_col or "phase 1" in first_col:
                current_phase = 1
                continue

            # Skip headers and summary rows
            if first_col in ["stt", "mã môn học", "", "tiếng việt"] or "tiếng anh" in first_col:
                continue
            if "tổng số" in first_col:
                continue

            # Parse course: [STT, Vietnamese Name, English Name, Credits]
            if texts[0].isdigit() and len(texts) >= 4:
                vi_name = texts[1]
                en_name = texts[2]
                credits = _extract_credits(texts[3])

                if vi_name and len(vi_name) > 3:
                    course = {
                        "code": "",
                        "name": f"{vi_name} ({en_name})" if en_name else vi_name,
                        "credits": credits,
                        "prerequisites": [],
                        "description": f"English: {en_name}" if en_name else "",
                    }
                    if current_phase == 1:
                        phase1_courses.append(course)
                    else:
                        phase2_courses.append(course)

    # Build sections matching standard format
    sections = []
    if phase1_courses:
        sections.append({
            "section_name": "Giai đoạn 1 - Học tại UIT",
            "courses": phase1_courses,
            "course_count": len(phase1_courses),
        })
    if phase2_courses:
        sections.append({
            "section_name": "Giai đoạn 2 - Học tại Đại học đối tác",
            "courses": phase2_courses,
            "course_count": len(phase2_courses),
        })

    # Extract graduation criteria
    graduation_criteria = ""
    if content:
        text = content.get_text()
        match = re.search(
            r"(sinh viên.*tốt nghiệp.*|cấp bằng.*|công nhận tốt nghiệp.*)[^\n]+",
            text,
            re.IGNORECASE,
        )
        if match:
            graduation_criteria = match.group().strip()

    total_courses = sum(s["course_count"] for s in sections)

    return {
        "name": title,
        "sections": sections,
        "total_courses": total_courses,
        "extraction_timestamp": None,
        "graduation_criteria": graduation_criteria,
        "metadata": {
            "url": url,
            "cohort": "",  # Will be filled
            "faculty": "",  # Will be filled
            "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "program_type": "linked",
        },
    }


def crawl_linked_programs():
    """Crawl all linked programs and save to JSON files."""
    for cohort, programs in LINKED_PROGRAMS.items():
        cohort_dir = OUTPUT_DIR / cohort
        cohort_dir.mkdir(parents=True, exist_ok=True)

        for program in programs:
            print(f"Crawling {cohort} - {program['filename']}...")

            soup = fetch_page(program["url"])
            if not soup:
                print(f"  FAILED: Could not fetch page")
                continue

            data = extract_program_data(soup, program["url"])
            data["metadata"]["cohort"] = cohort
            data["metadata"]["faculty"] = program["faculty"]

            # Add source cohort if this reuses another cohort's curriculum
            if "reuses" in program:
                data["metadata"]["original_source_cohort"] = program["reuses"]

            filepath = cohort_dir / program["filename"]

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"  SUCCESS: Saved {program['filename']} ({data['total_courses']} courses)")


if __name__ == "__main__":
    print("=" * 60)
    print("Linked Programs Crawler (Birmingham/Newcastle)")
    print("=" * 60)
    crawl_linked_programs()
    print("\nDone!")
