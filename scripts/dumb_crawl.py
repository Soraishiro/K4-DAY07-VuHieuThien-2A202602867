
import csv
import logging
import os
import time
import requests
from bs4 import BeautifulSoup
import json
import re
import unicodedata


# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Determine base paths relative to this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../../"))

METADATA_FILE = os.path.join(SCRIPT_DIR, "metadata.csv")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "curiculum", "raw")

TARGET_SECTIONS = [
    "giới thiệu",           # For "1. GIỚI THIỆU CHUNG" - program introduction
    "chương trình đào tạo", # Main curriculum section (includes footnotes, tables, etc.)
    "kế hoạch giảng dạy",   # Teaching plan
    "điều kiện tốt nghiệp", # Graduation requirements (NOT "Khối kiến thức tốt nghiệp")
    "khác biệt",            # For "Sự khác biệt..."
    "quy định",             # For "Các quy định khác"
    "tài năng",             # For "Chương trình tài năng" section on Type B pages
    "quy định anh văn"      # For English proficiency rules (TOEIC for IS Tiên Tiến)
    # NOTE: "lưu ý" removed - footnotes stay within their parent section
    # NOTE: "danh mục môn học" removed - course tables captured via fallback
]

# STOP_KEYWORDS: Headers that signal a section boundary.
# More specific to avoid false positives (e.g., "Khối kiến thức tốt nghiệp" != "Điều kiện tốt nghiệp")
STOP_KEYWORDS = [
    "giới thiệu chung",
    "chuẩn đầu ra",
    "chương trình đào tạo",
    "kế hoạch giảng dạy",
    "điều kiện tốt nghiệp",  # Only this, not "Khối kiến thức tốt nghiệp"  
    "đối tượng tuyển sinh",
    "tỷ lệ các khối kiến thức",
    "nội dung chương trình đào tạo",
]


def fetch_html(url):
    logger.info(f"Fetching {url}...")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return None

def normalize_compare(t):
    if not t:
        return ""
    # Unicode normalization to handle combined/decomposed characters
    t = unicodedata.normalize('NFKC', t)
    # Replace non-breaking spaces, dashes, en-dashes with space
    t = (
        t.replace("\xa0", " ")
        .replace("-", " ")
        .replace("–", " ")
        .replace("(", "")
        .replace(")", "")
        .lower()
    )
    return " ".join(t.split())



def determine_accordion_type(dl_tag):
    """
    Determine if the accordion contains 'Programs' (Type A) or 'Sections' (Type B).
    Returns: 'PROGRAMS', 'SECTIONS', or 'UNKNOWN'
    """
    dts = dl_tag.find_all("dt")
    if not dts:
        return 'UNKNOWN'
        
    # Check distinct keywords
    program_keywords = ["cử nhân", "kỹ sư", "chương trình đại trà", "chương trình tài năng", "chương trình tiên tiến", "hệ chính quy", "việt - nhật"]
    section_keywords = ["giới thiệu", "mục tiêu", "cơ hội", "chương trình đào tạo", "kế hoạch", "chuẩn đầu ra", "tốt nghiệp", "đội ngũ", "khác biệt"]
    
    prog_score = 0
    sect_score = 0
    
    for dt in dts:
        text = normalize_compare(dt.get_text())
        if any(k in text for k in program_keywords):
            # Special case: "Chương trình đào tạo" contains "chương trình", but it is a Section name.
            if "chương trình đào tạo" not in text:
                prog_score += 1
        
        if any(k in text for k in section_keywords):
            sect_score += 1
            
    if sect_score > prog_score:
        return 'SECTIONS'
    elif prog_score > 0:
        return 'PROGRAMS'
        
    return 'UNKNOWN'

def extract_from_program_accordion(dl_tag, target_program_name, soup):
    """
    Type A: Accordion contains different Programs.
    Find the correct Program block(s), then extract sections from them (using flat extraction).
    """
    dts = dl_tag.find_all("dt")
    dds = dl_tag.find_all("dd")
    
    valid_blocks = []
    primary_name = None
    
    t_norm = normalize_compare(target_program_name)
    is_h_search = "tài năng" in t_norm
    is_vn_search = "việt nhật" in t_norm

    for dt, dd in zip(dts, dds):
        sub_name = dt.get_text().strip()
        s_norm = normalize_compare(sub_name)

        if any(x in s_norm for x in ["văn bằng", "liên thông", "thứ 2", "thứ hai"]):
            continue

        is_vn_section = "việt nhật" in s_norm
        
        # Viet-Nhat Filter
        if is_vn_search and not is_vn_section:
            continue
        if not is_vn_search and is_vn_section:
            continue

        # Honors Filter (Inclusive)
        is_h_section = "tài năng" in s_norm
        
        if is_h_search:
            # Honors needs Standard + Honors
            if not is_h_section:
                pass # Accept Standard
            else:
                primary_name = sub_name
        else:
            # Standard excludes Honors
            if is_h_section:
                continue
            primary_name = sub_name

        valid_blocks.append(str(dd))

    if not valid_blocks:
        logger.warning(f"Type A: No matching program block for {target_program_name}")
        return None, None

    combined_html = "\n<hr>\n".join(valid_blocks)
    return extract_content_sections_flat(combined_html), primary_name or "Combined"



def html_to_markdown(html):
    """
    Convert HTML content to simple Markdown text.
    Preserves basic table structure and headers.
    """
    if not html:
        return ""
    
    soup = BeautifulSoup(html, "html.parser")
    
    # Process headers
    for i in range(1, 7):
        for h in soup.find_all(f'h{i}'):
            h.string = f"{'#' * i} {h.get_text()} \n"
            
    # Process lists
    for ul in soup.find_all('ul'):
        for li in ul.find_all('li'):
            li.string = f"- {li.get_text()} \n"
            
    # Process tables (simple text representation)
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        table_text = []
        for row in rows:
            cols = row.find_all(['td', 'th'])
            col_text = [ele.get_text(separator=" ", strip=True) for ele in cols]
            table_text.append(" | ".join(col_text))
        
        if table_text:
            table_md = "\n" + "\n".join(table_text) + "\n"
            table.string = table_md
            
    # Get clean text with newlines
    text = soup.get_text(separator="\n", strip=True)
    return text

def extract_from_section_accordion(dl_tag):

    """
    Type B: Accordion contains Sections of the target program.
    Extract distinct sections directly.
    Supports both standard dl/dt/dd structure AND CKEditor accordion structure.
    """
    found = {}
    
    # Map normalized section keywords to canonical names
    # Reuse global TARGET_SECTIONS for consistency
    targets_map = {normalize_compare(t): t for t in TARGET_SECTIONS}
    
    # Try standard dl/dt/dd structure first
    dts = dl_tag.find_all("dt")
    dds = dl_tag.find_all("dd")
    
    if dts and dds:
        for dt, dd in zip(dts, dds):
            header_text = dt.get_text().strip()
            norm_header = normalize_compare(header_text)
            
            matched_key = None
            for t_norm, t_original in targets_map.items():
                 if t_norm in norm_header:
                     matched_key = t_original
                     break
            
            if matched_key:
                content = html_to_markdown(str(dd))
                if matched_key in found:
                    found[matched_key] += "\n\n" + content
                else:
                    found[matched_key] = content
    
    # Also try CKEditor accordion structure
    togglers = dl_tag.find_all(class_="ckeditor-accordion-toggler")
    
    for toggler in togglers:
        header_text = toggler.get_text().strip()
        norm_header = normalize_compare(header_text)
        
        matched_key = None
        for t_norm, t_original in targets_map.items():
            if t_norm in norm_header:
                matched_key = t_original
                break
        
        if matched_key:
            # Find the body - usually the next sibling with class ckeditor-accordion-body
            body = toggler.find_next_sibling(class_="ckeditor-accordion-body")
            if body:
                content = html_to_markdown(str(body))
                if matched_key in found:
                    found[matched_key] += "\n\n" + content
                else:
                    found[matched_key] = content
            
    return found


def extract_notes_sections(soup):
    """
    Extract content from header-based sections that contain notes/footnotes.
    These are typically paragraphs after headers like "3.5 Lưu ý:" which are not
    inside accordions or tables.
    
    Args:
        soup: BeautifulSoup object of the page
        
    Returns:
        dict: Dictionary with section name as key and content as value
    """
    found = {}
    note_keywords = ["lưu ý", "ghi chú", "chú ý"]
    
    # Find all headers that might contain notes
    for header in soup.find_all(['h2', 'h3', 'h4']):
        header_text = header.get_text().strip()
        norm_header = normalize_compare(header_text)
        
        # Check if this header contains note keywords
        if any(kw in norm_header for kw in note_keywords):
            logger.info(f"Found notes section header: {header_text[:50]}...")
            content_parts = []
            
            # Collect all content until next same-level or higher header
            for sibling in header.find_next_siblings():
                # Stop at next major section header
                if sibling.name in ['h1', 'h2']:
                    break
                # Stop at h3 if current is h3 or lower
                if sibling.name == 'h3' and header.name in ['h3', 'h4']:
                    break
                    
                content_parts.append(str(sibling))
            
            if content_parts:
                content = html_to_markdown("".join(content_parts))
                key = "lưu ý"  # Canonical key
                if key in found:
                    found[key] += "\n\n" + content
                else:
                    found[key] = content
                logger.info(f"Captured notes content: {len(content)} chars")
    
    return found


def extract_english_requirements(soup):
    """
    Extract English proficiency requirements (TOEIC thresholds) from the page.
    These are commonly found in IS Tiên Tiến programs.
    
    Args:
        soup: BeautifulSoup object of the page
        
    Returns:
        dict: Dictionary with 'quy định anh văn' key if requirements found
    """
    text = soup.get_text()
    requirements = []
    
    # Pattern 1: TOEIC requirements with numbers
    toeic_pattern = r'[^.]*(?:TOEIC|toeic)\s*\d+[^.]*\.'
    matches = re.findall(toeic_pattern, text)
    requirements.extend(matches)
    
    # Pattern 2: "Anh văn X" with requirements 
    eng_pattern = r'[^.]*[Kk]ết thúc học kỳ[^.]*[Aa]nh [Vv]ăn[^.]*\.'
    eng_matches = re.findall(eng_pattern, text)
    requirements.extend(eng_matches)
    
    if requirements:
        # Deduplicate and clean
        unique_reqs = list(set(req.strip() for req in requirements))
        logger.info(f"Found {len(unique_reqs)} English requirement statements")
        return {"quy định anh văn": "\n".join(unique_reqs)}
    
    return {}


def extract_content_sections_flat(html):
    """
    Dumb extraction from flat HTML (or combined blocks).
    """
    soup = BeautifulSoup(html, "html.parser")
    found = {}
    
    
    candidates = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'strong', 'b', 'p'])
    
    current_section = None
    current_content = []
    
    targets_map = {normalize_compare(t): t for t in TARGET_SECTIONS}
    
    # Map common sub-headers or variants to canonical sections
    VARIANTS = {
        normalize_compare("tỷ lệ các khối kiến thức"): "chương trình đào tạo",
        normalize_compare("nội dung chương trình"): "chương trình đào tạo",
        normalize_compare("khung chương trình"): "chương trình đào tạo",
    }
    
    # Use STOP_KEYWORDS for boundary detection (broader than TARGET_SECTIONS)
    stop_keywords_norm = [normalize_compare(k) for k in STOP_KEYWORDS]
    
    for node in candidates:
        # Skip inline strong/b that are likely just emphasis in a full sentence
        if node.name in ['strong', 'b'] and node.parent and node.parent.name == 'p':
            parent_text = node.parent.get_text().strip()
            node_text = node.get_text().strip()
            # If parent is significantly longer, assume it's inline text not a header
            if len(parent_text) > len(node_text) + 20:
                continue

        text = node.get_text().strip()
        norm_text = normalize_compare(text)
        
        matched_key = None
        
        # 1. Check exact/fuzzy match in main TARGET_SECTIONS
        for t_norm, t_original in targets_map.items():
            if t_norm in norm_text and len(norm_text) < len(t_norm) + 15:
                # Avoid intro sections misidentified as curriculum
                if t_original == "chương trình đào tạo" and any(k in norm_text for k in ["quan điểm", "mục tiêu", "vị trí", "cơ hội", "hình thức"]):
                    continue
                matched_key = t_original
                break
        
        # 2. Check variants if no match found (to catch cases with missing main headers)
        if not matched_key:
            for v_norm, t_original in VARIANTS.items():
                if v_norm in norm_text and len(norm_text) < len(v_norm) + 15:
                    matched_key = t_original
                    break
        
        if matched_key:
            # Save previous
            if current_section and current_content:
                content = html_to_markdown("".join(current_content))
                if current_section in found:
                    found[current_section] += "\n\n" + content
                else:
                    found[current_section] = content
            
            current_section = matched_key
            current_content = []
            
            # Start grabbing from parent if inline
            start_node = node
            if node.name in ['strong', 'b'] and node.parent.name in ['p', 'div', 'h2', 'h3', 'h4', 'h5']:
                start_node = node.parent
            
            # Also check if start_node has no following siblings (nested in wrapper)
            # If so, climb to parent (e.g. <div><h1>Title</h1></div> -> sibling is after div)
            if not start_node.next_sibling and start_node.parent and start_node.parent.name not in ['body', 'html']:
                # Verify parent is a wrapper (generic div/section)
                start_node = start_node.parent
            
            curr = start_node.next_sibling
            while curr:
                # Check if current node is a potential header that matches a STOP keyword
                is_header_stop = False
                
                # We need to check if 'curr' contains a section header.
                # If curr is a Tag, check its text.
                if hasattr(curr, 'get_text') and hasattr(curr, 'name'):
                    # Check if this node ITSELF is a candidate type
                    if curr.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'strong', 'b', 'p']:
                        text_chk = curr.get_text().strip()
                        norm_chk = normalize_compare(text_chk)
                        
                        # Special case: Check if paragraph starts with markdown header syntax (# or ##)
                        if curr.name == 'p' and text_chk.startswith(('#', '##')):
                            # Extract text after the markdown prefix
                            # Remove leading # symbols and whitespace
                            clean_text = text_chk.lstrip('#').strip()
                            norm_chk = normalize_compare(clean_text)
                        
                        # Stop if it matches any STOP keyword (not just target sections)
                        for stop_kw in stop_keywords_norm:
                             if stop_kw in norm_chk and len(norm_chk) < len(stop_kw) + 20:
                                 is_header_stop = True
                                 break
                    
                    # Also check if it CONTAINS a header tag that matches (h1-h5, strong, b)
                    if not is_header_stop and curr.name in ['p', 'div']:
                        child_header = curr.find(['h1', 'h2', 'h3', 'h4', 'h5', 'strong', 'b'])
                        if child_header:
                            text_chk = child_header.get_text().strip()
                            norm_chk = normalize_compare(text_chk)
                            for stop_kw in stop_keywords_norm:
                                if stop_kw in norm_chk and len(norm_chk) < len(stop_kw) + 20:
                                    is_header_stop = True
                                    break

                
                if is_header_stop:
                    break
                    
                if hasattr(curr, 'get_text'):
                    current_content.append(str(curr))
                curr = curr.next_sibling
                
    # Save last
    if current_section and current_content:
        content = html_to_markdown("".join(current_content))
        if current_section in found:
            found[current_section] += "\n\n" + content
        else:
            found[current_section] = content
        
    return found

def save_output(cohort, program_name, url, faculty, found_sections, found_name_meta):
    if found_sections:
        output_data = {
            "metadata": {
                "url": url,
                "cohort": cohort,
                "program_name": program_name,
                "faculty": faculty,
                "found_section_name": found_name_meta,
                "crawled_at": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "sections": found_sections
        }
        
        safe_name = re.sub(r'[^\w\s-]', '', program_name).strip().replace(' ', '_')
        filename = f"{cohort}_{faculty}_{safe_name}.json"
        
        cohort_dir = os.path.join(OUTPUT_DIR, cohort)
        os.makedirs(cohort_dir, exist_ok=True)
        
        outfile = os.path.join(cohort_dir, filename)
        with open(outfile, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(found_sections)} sections to {outfile}")
    else:
        logger.warning(f"No target sections found for {program_name} in {url}")

def process_url(url, cohort, program_name, faculty):
    html = fetch_html(url)
    if not html:
        return

    soup = BeautifulSoup(html, "html.parser")
    
    # ========================================
    # SPECIAL CASE: Multi-Program Flat Pages
    # Used by IT page which has 3 programs in sequence:
    #   Program A: Standard IT (positions 6-19)
    #   Program B: IT Việt-Nhật (positions 20-33)
    #   Program C: IT Liên thông (positions 46-62)
    # The programs are separated by "5/6. ĐIỀU KIỆN TỐT NGHIỆP" followed by "1. GIỚI THIỆU CHUNG"
    # ========================================
    target_norm = normalize_compare(program_name)
    is_vn = "việt nhật" in target_norm
    is_lien_thong = "liên thông" in target_norm
    
    # Check if this is a multi-program flat page
    # by looking for multiple "1. GIỚI THIỆU CHUNG" headers
    # Note: We use get_text() because headers may contain nested links
    intro_headers = []
    for h in soup.find_all(['h1', 'h2']):
        h_text = h.get_text()
        if re.search(r'1\.\s*GIỚI THIỆU', h_text, re.IGNORECASE):
            intro_headers.append(h)
    
    if len(intro_headers) >= 2:
        logger.info(f"Detected multi-program flat page with {len(intro_headers)} program blocks")

        
        # For Việt-Nhật: Find the section that mentions "Việt – Nhật" in text
        # For Liên thông: Find section with "ĐỐI TƯỢNG TUYỂN SINH"
        
        program_start = None
        program_end = None
        
        if is_vn:
            # Việt-Nhật content starts at the SECOND "1. GIỚI THIỆU" header
            if len(intro_headers) >= 2:
                program_start = intro_headers[1]
                logger.info(f"Found VN program start (2nd Gioi Thieu): {program_start.get_text()[:60]}")
            
            # Find where it ends (THIRD "1. GIỚI THIỆU" or "ĐỐI TƯỢNG TUYỂN SINH")
            if program_start:
                if len(intro_headers) >= 3:
                    program_end = intro_headers[2]
                else:
                    # Look for "ĐỐI TƯỢNG TUYỂN SINH" which marks Liên thông
                    for elem in program_start.find_all_next(['h1', 'h2']):
                        text = normalize_compare(elem.get_text())
                        if 'đối tượng tuyển sinh' in text:
                            program_end = elem
                            break
        
        elif is_lien_thong:
            # Liên thông content starts at the THIRD "1. GIỚI THIỆU" header
            if len(intro_headers) >= 3:
                program_start = intro_headers[2]
                logger.info(f"Found LT program start (3rd Gioi Thieu): {program_start.get_text()[:60]}")
        
        else:
            # Standard Program (Program A) - starts at the FIRST "1. GIỚI THIỆU" header
            # and ends at the SECOND "1. GIỚI THIỆU" header (or "5. Điều kiện tốt nghiệp" of Program A, but we can just stop at Program B start)
            if len(intro_headers) >= 1:
                program_start = intro_headers[0]
                logger.info(f"Found Standard program start (1st Gioi Thieu): {program_start.get_text()[:60]}")
                if len(intro_headers) >= 2:
                    program_end = intro_headers[1]
        
        if program_start:
            logger.info(f"Extracting from program block starting at: {program_start.get_text()[:50]}")
            
            # Use find_all_next to get all elements until program_end
            # Check if program_start is nested (e.g., header inside a div with no siblings)
            # If so, climb up to find the block level container
            cursor = program_start
            # Climb up if no subsequent meaningful siblings (ignoring empty strings)
            # Use a limited climb to avoid going too high (like to body)
            while cursor.parent and cursor.parent.name not in ['body', 'html', 'main']:
                siblings = list(cursor.find_next_siblings())
                has_meaningful_sibling = any(s.name or (isinstance(s, str) and s.strip()) for s in siblings)
                
                if not has_meaningful_sibling:
                    logger.info(f"Header {cursor.name} has no siblings, climbing to parent {cursor.parent.name}")
                    cursor = cursor.parent
                else:
                    break
            
            # Now extract from cursor (which might be the header or its container)
            # We include the cursor itself to capture the header
            content_parts = [str(cursor)]
            
            for sibling in cursor.find_next_siblings():
                if program_end:
                    # Check if this sibling contains the program_end element
                    # If program_end is a descendant of this sibling, we need to handle it?
                    # For flat structures, usually program_end is a sibling or descendant of a following sibling.
                    
                    # Simple check: stop if we hit program_end directly
                    if sibling == program_end:
                        break
                    
                    # Stop if sibling contains program_end
                    if hasattr(sibling, 'descendants') and program_end in sibling.descendants:
                        # In a cleaner implementation we might want to split this element
                        # But for now, let's include it or stop? 
                        # If it contains the end, it likely contains the start of the next section.
                        # We should probably stop BEFORE this sibling if it's the next program header container
                        break
                
                # Stop if we hit the next program's intro header (if not using program_end)
                if sibling in intro_headers and sibling != program_start:
                    break
                    
                # Stop if we hit "ĐỐI TƯỢNG TUYỂN SINH" for non-Liên thông programs
                if not is_lien_thong:
                    sib_text = normalize_compare(sibling.get_text())
                    if 'đối tượng tuyển sinh' in sib_text:
                        break
                content_parts.append(str(sibling))


            
            program_html = "".join(content_parts)
            found_sections = extract_content_sections_flat(program_html)
            
            prog_type_name = "CHÍNH QUY"
            if is_vn: prog_type_name = "VIỆT NHẬT"
            elif is_lien_thong: prog_type_name = "LIÊN THÔNG"
                
            found_name_meta = f"B. NGÀNH CNTT {prog_type_name}"
            
            # Note: We do NOT extract tables separately here because extract_content_sections_flat
            # already captures them as part of the content flow. 
            # Separate extraction causes duplicates.

            
            # Save and return early
            save_output(cohort, program_name, url, faculty, found_sections, found_name_meta)
            return
    
    # ========================================
    # Standard processing path
    # ========================================
    dl_tags = soup.find_all("dl")  # Find ALL accordions
    
    if not dl_tags:
        # Fallback to flat
        strategy = "FLAT"


    else:
        # Determine strategy based on the FIRST useful accordion?
        # Or check all? Usually all accordions on a page will follow the same pattern (Structure)
        # But let's check the first one that has DTs.
        strategy = "UNKNOWN"
        target_dl = None
        
        for dl in dl_tags:
            st = determine_accordion_type(dl) 
            if st != 'UNKNOWN':
                strategy = st
                target_dl = dl
                break
        
        if strategy == "UNKNOWN":
            strategy = "FLAT" # Fallback

    found_sections = {}
    found_name_meta = program_name

    logger.info(f"Processing {url} | Strategy: {strategy}")

    if strategy == 'PROGRAMS':
        # If strategy is PROGRAMS, presumably one of the accordions contains the programs.
        # We should probably check ALL accordions for the program block?
        # Yes, merged.
        combined_html_parts = []
        pname_found = None
        
        for dl in dl_tags:
             # Only process if it looks like a program list? 
             # Or just try to find the block in all of them.
             # `extract_from_program_accordion` logic returns None if not found.
             
             # We need to expose the "find block" part separately if we want to be clean, 
             # but `extract_from_program_accordion` currently does extraction too.
             # Let's just refactor slightly inline:
             
             # We assume here that `extract_from_program_accordion` can handle being called multiple times
             # But it returns extracted sections.
             
             # Let's try to extract from THIS dl.
             dl_sections, pname = extract_from_program_accordion(dl, program_name, soup)
             if dl_sections:
                 if pname: pname_found = pname
                 for k, v in dl_sections.items():
                     if k in found_sections:
                         found_sections[k] += "\n\n" + v
                     else:
                         found_sections[k] = v
        
        if pname_found: found_name_meta = pname_found
        
    elif strategy == 'SECTIONS':
        # Process ALL accordions as section lists
        for dl in dl_tags:
            dl_sections = extract_from_section_accordion(dl)
            for k, v in dl_sections.items():
                if k in found_sections:
                    found_sections[k] += "\n\n" + v
                else:
                    found_sections[k] = v
        
        # Also check for CKEditor accordion directly in soup (not inside dl tags)
        targets_map = {normalize_compare(t): t for t in TARGET_SECTIONS}
        togglers = soup.find_all(class_="ckeditor-accordion-toggler")
        
        for toggler in togglers:
            header_text = toggler.get_text().strip()
            norm_header = normalize_compare(header_text)
            
            matched_key = None
            for t_norm, t_original in targets_map.items():
                if t_norm in norm_header:
                    matched_key = t_original
                    break
            
            if matched_key and matched_key not in found_sections:
                # Find the body - usually the next sibling with class ckeditor-accordion-body
                body = toggler.find_next_sibling(class_="ckeditor-accordion-body")
                if body:
                    content = html_to_markdown(str(body))
                    found_sections[matched_key] = content
                    
    else: # FLAT
        found_sections = extract_content_sections_flat(html)
    
    
    # Fallback: Always scan for course tables if we haven't found a dedicated section
    # or even if we have, to be safe (append them).
    logger.info("Fallback: Scanning for course tables...")
    tables = soup.find_all("table")
    logger.info(f"Total tables found in DOM: {len(tables)}")
    
    valid_tables = []
    
    for i, table in enumerate(tables):
        # Check if table headers look like course info
        # Get first few rows to check for headers (sometimes header is 2nd row)
        rows = table.find_all('tr')
        if not rows: continue
        
        is_course_table = False
        header_text_debug = ""
        
        for r_idx in range(min(3, len(rows))):
            row_text = rows[r_idx].get_text(" ", strip=True).lower()
            
            # Standard/Honors Programs: Need "mã" and "tên"
            cond_standard = "mã" in row_text and "tên" in row_text
            
            # Birmingham/International: Might not have "mã", but has "tên" and "tín chỉ" or "cats"
            cond_international = ("tên" in row_text and "môn" in row_text) and ("tín chỉ" in row_text or "cats" in row_text or "credits" in row_text)
            
            if cond_standard or cond_international:
                is_course_table = True
                header_text_debug = row_text
                break
        
        if is_course_table:
            logger.info(f"Table {i}: MATCHED course table (Header: {header_text_debug[:50]}...)")
            
            # Try to find a preceding header for context
            prev = table.find_previous_sibling(['h3', 'h4', 'h5', 'strong', 'b', 'p'])
            title = f"Bảng môn học {len(valid_tables)+1}"
            if prev:
                title_text = prev.get_text().strip()
                if len(title_text) > 3 and len(title_text) < 100:
                    title = title_text
                
            table_md = html_to_markdown(str(table))
            valid_tables.append(f"### {title}\n{table_md}")
        else:
             logger.info(f"Table {i}: Skipped (Header: {rows[0].get_text()[:50]}...)")

    if valid_tables:
        logger.info(f"Fallback: Found {len(valid_tables)} course tables.")
        content = "\n\n".join(valid_tables)
        # Append to "chương trình đào tạo" since course tables are part of curriculum
        if "chương trình đào tạo" in found_sections:
            found_sections["chương trình đào tạo"] += "\n\n" + content
        else:
            found_sections["chương trình đào tạo"] = content

    else:
        logger.warning("Fallback: No course tables found matching criteria.")
    
    # NOTE: Step 4 (notes/footnotes extraction) REMOVED
    # Footnotes should stay within their parent sections (e.g., inside "chương trình đào tạo")

    
    # Step 5: Extract English proficiency requirements (for IS Tiên Tiến programs)
    english_reqs = extract_english_requirements(soup)
    for key, content in english_reqs.items():
        if key in found_sections:
            found_sections[key] += "\n\n" + content
        else:
            found_sections[key] = content
    
    save_output(cohort, program_name, url, faculty, found_sections, found_name_meta)


import argparse

def main():
    parser = argparse.ArgumentParser(description="Dumb Crawler for UIT")
    parser.add_argument("--url", help="Target URL")
    parser.add_argument("--cohort", help="Cohort")
    parser.add_argument("--faculty", help="Faculty code")
    parser.add_argument("--name", help="Program name")
    parser.add_argument("--output-dir", help="Output directory")

    args = parser.parse_args()

    if args.url:
        if not args.cohort or not args.faculty:
            logger.error("--cohort and --faculty are required with --url")
            return
        
        # Determine paths
        # If output_dir is passed, override global OUTPUT_DIR (a bit hacky since global is used inside process_url)
        # But process_url uses global OUTPUT_DIR. Let's rely on global constant or default.
        # Ideally refactor process_url to accept output_dir, but for now we trust the default.
        
        name = args.name or "Single_Crawl_Program"
        process_url(args.url, args.cohort, name, args.faculty)
        return

    # Batch mode (default)
    if not os.path.exists(METADATA_FILE):
        logger.error(f"Metadata file not found: {METADATA_FILE}")
        return

    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row["URL"]
            cohort = row["Cohort"]
            faculty = row["Faculty"]
            program_name = row["Program Name"]
            
            # Skip rows without URL
            if not url or not url.strip():
                continue
                
            process_url(url, cohort, program_name, faculty)
            time.sleep(1) # Be polite

if __name__ == "__main__":
    main()

