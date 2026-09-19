import requests
from bs4 import BeautifulSoup
import json
import os
from pathlib import Path

# Resolve paths relative to project root
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "curiculum" / "raw"

URL = "https://student.uit.edu.vn/danh-muc-mon-hoc-dai-hoc"
OUTPUT_FILE = OUTPUT_DIR / "course_list.json"

def clean_text(text):
    return text.strip()

def crawl_subjects():
    """Crawl the UIT course catalog and save to course_list.json."""
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Fetching {URL}...")
    try:
        response = requests.get(URL, timeout=10)
        response.raise_for_status()
        html_content = response.text
    except Exception as e:
        print(f"Error fetching URL: {e}")
        return

    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Locate the table
    # Based on the user provided file, it's a standard table with header row.
    table = soup.find('table')
    if not table:
        print("Error: No table found in the content.")
        return

    subjects = []
    
    # Iterate rows
    rows = table.find_all('tr')
    
    # Identify headers
    # Expected headers: STT, Mã MH, Tên MH (Tiếng Việt), Tên MH (Tiếng Anh), Còn mở lớp, ĐVQL, Loại MH, Mã cũ, Tương đương, Tiên quyết, Môn học trước, Số TCLT, Số TCTH
    
    start_index = 0
    if rows and "Mã MH" in rows[0].get_text():
        start_index = 1
        
    for row in rows[start_index:]:
        cols = row.find_all('td')
        if len(cols) < 13: 
            continue
            
        def get_text(idx):
             return clean_text(cols[idx].get_text())

        def get_list_from_cell(idx):
            # Use separator to handle <br> tags
            text = cols[idx].get_text(separator='|', strip=True)
            if not text:
                return []
            # Split by separator and clean
            return [t.strip() for t in text.split('|') if t.strip()]
             
        stt = get_text(0)
        code = get_text(1)
        name_vi = get_text(2)
        name_en = get_text(3)
        
        # Open status is an image
        is_open_img = cols[4].find('img')
        is_open = False
        if is_open_img:
            title = is_open_img.get('title', '').lower()
            if "đang mở" in title:
                is_open = True
                
        faculty = get_text(5)
        course_type = get_text(6)
        old_code = get_text(7)
        # Parse these as lists
        equiv_code = get_list_from_cell(8)
        prereq_code = get_list_from_cell(9)
        prev_code = get_list_from_cell(10)
        
        credit_theory = get_text(11)
        credit_practice = get_text(12)
        
        if not code and not name_vi:
            continue
            
        subject = {
            "stt": stt,
            "code": code,
            "name_vi": name_vi,
            "name_en": name_en,
            "is_open": is_open,
            "faculty": faculty,
            "type": course_type,
            "old_code": old_code,
            "equiv_code": equiv_code,
            "prereq_code": prereq_code,
            "prev_code": prev_code,
            "credit_theory": credit_theory,
            "credit_practice": credit_practice
        }
        subjects.append(subject)
        
    print(f"Found {len(subjects)} subjects.")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(subjects, f, indent=2, ensure_ascii=False)
        
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    crawl_subjects()
