import requests
from bs4 import BeautifulSoup
import json
import os
from pathlib import Path

# Resolve paths relative to project root
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "curiculum" / "raw"

URL = "https://student.uit.edu.vn/content/bang-tom-tat-mon-hoc"
OUTPUT_FILE = OUTPUT_DIR / "course_summaries.json"

def clean_text(text):
    if not text:
        return ""
    return ' '.join(text.split())

def crawl_summaries():
    """Crawl UIT course summaries and save to course_summaries.json."""
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

    courses = []
    
    # Iterate rows
    rows = table.find_all('tr')
    
    # Skip header
    # Header row: STT, Mã MH, Tên MH, Tóm tắt môn học
    start_index = 0
    if rows:
        header_text = rows[0].get_text()
        if "Mã MH" in header_text or "STT" in header_text:
            start_index = 1
        
    for row in rows[start_index:]:
        cols = row.find_all('td')
        if len(cols) < 4: 
            continue
            
        def get_text(idx):
             return clean_text(cols[idx].get_text())
             
        stt = get_text(0)
        code = get_text(1)
        name = get_text(2)
        summary = get_text(3)
        
        if not code and not name:
            continue
            
        course = {
            "stt": stt,
            "code": code,
            "name": name,
            "summary": summary
        }
        courses.append(course)
        
    print(f"Found {len(courses)} courses.")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(courses, f, indent=2, ensure_ascii=False)
        
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    crawl_summaries()
