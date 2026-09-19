"""
Utility functions for extracting structured data from UIT web pages.

Provides helper functions for parsing HTML content and extracting
academic program information from student portal pages.
"""

import re
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup


def clean_text(text: str) -> str:
    """
    Clean and normalize text content.
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text with normalized whitespace
    """
    if not text:
        return ""
    return ' '.join(text.split()).strip()


def extract_program_data(html_content: str, program_name: str) -> Dict[str, Any]:
    """
    Extract structured program data from HTML content.
    
    Args:
        html_content: HTML content containing program information
        program_name: Name of the program being extracted
        
    Returns:
        Dict containing extracted program data with sections and courses
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Initialize program data structure
    program_data = {
        "name": program_name,
        "sections": [],
        "total_courses": 0
    }
    
    # Look for course tables or structured content
    tables = soup.find_all('table')
    
    # Section names to exclude (sample schedules, not actual curriculum)
    excluded_section_patterns = ['kế hoạch giảng dạy', 'học kỳ', 'teaching schedule']
    
    for table in tables:
        section_data = extract_course_table(table)
        if section_data and section_data.get('courses'):
            # Skip excluded sections (schedules)
            section_name_lower = section_data.get('section_name', '').lower()
            if any(pattern in section_name_lower for pattern in excluded_section_patterns):
                continue
            program_data["sections"].append(section_data)
            program_data["total_courses"] += len(section_data["courses"])
    
    # If no tables found, try to extract from other structures
    if not program_data["sections"]:
        # Look for course lists in divs or other containers
        course_containers = soup.find_all(['div', 'section'], class_=re.compile(r'course|curriculum|program'))
        for container in course_containers:
            section_data = extract_course_container(container)
            if section_data and section_data.get('courses'):
                program_data["sections"].append(section_data)
                program_data["total_courses"] += len(section_data["courses"])
    
    # Extract graduation criteria
    grad_criteria = extract_graduation_criteria(soup)
    if grad_criteria:
        program_data["graduation_criteria"] = grad_criteria

    return program_data if program_data["sections"] else None


def extract_course_table(table) -> Optional[Dict[str, Any]]:
    """
    Extract course information from a table element.
    
    Args:
        table: BeautifulSoup table element
        
    Returns:
        Dict containing section data with courses, or None if no courses found
    """
    rows = table.find_all('tr')
    if len(rows) < 2:  # Need at least header and one data row
        return None
    
    # Try to identify header row and extract column mapping
    header_row = rows[0]
    headers = [clean_text(th.get_text()) for th in header_row.find_all(['th', 'td'])]
    
    # Common column patterns in UIT curriculum tables
    column_mapping = identify_column_mapping(headers)
    
    if not column_mapping:
        return None
    
    courses = []
    
    # Try to find the section name by traversing previous siblings
    # Skip informational paragraphs (credit counts, instructions, etc.)
    section_name = "Unknown Section"
    prev_elem = table.find_previous_sibling()
    
    noise_phrases = ['tổng số tín chỉ', 'tổng cộng', 'sinh viên chọn', 
                     'hoặc', 'tín chỉ', 'bắt buộc', 'tự chọn', '●']
    
    import re
    # Regex for section numbering: "1.", "1.1.", "3.4.1.", "3.5" (allow missing space after dot)
    # Also handles "A.", "B." if they appear
    section_pattern = re.compile(r'^\s*(\d+(\.\d+)*|[A-Z])\.?\s*') 
    
    # Walk backwards through siblings until we find a header
    attempts = 0
    # Increase search depth as some pages have many empty p tags or breaks
    while prev_elem and attempts < 20: 
        attempts += 1
        
        text = clean_text(prev_elem.get_text())
        if not text:
            prev_elem = prev_elem.find_previous_sibling()
            continue

        # Check if this is a header tag (h2-h6)
        is_header_tag = prev_elem.name in ['h2', 'h3', 'h4', 'h5', 'h6']
        
        # Check for paragraph with strong/bold (common in Viet-Nhat)
        is_bold_p = False
        if prev_elem.name in ['p', 'div']:
            strong_tags = prev_elem.find_all(['strong', 'b'])
            if strong_tags:
                # Issue: Viet-Nhat uses <p><a><strong>3.4.2.2.</strong><strong>Title</strong></a></p>
                # We need to construct the full text from ALL strong tags or the parent text
                
                full_text = clean_text(prev_elem.get_text())
                first_strong = clean_text(strong_tags[0].get_text())
                
                # If the paragraph starts with the strong text roughly (ignoring punctuation), it's likely a header
                if full_text.startswith(first_strong) or full_text.replace('.', '').startswith(first_strong.replace('.', '')):
                     # If the first strong is just numbering, use the FULL text of the paragraph/link
                     if section_pattern.match(first_strong) and len(first_strong) < 10:
                         text = full_text
                     else:
                         text = full_text # Safer to just use the whole line if it starts with bold
                     
                     if len(text) > 0 and (section_pattern.match(text) or len(text) < 150):
                         is_bold_p = True

        # Validation: Is this actually a header?
        is_valid_header = False
        
        # 1. Numbered Header (e.g., "3.5.1.")
        if section_pattern.match(text) and len(text) < 200:
             is_valid_header = True
             
        # 2. Keyword Header (e.g., "Khối kiến thức chung")
        elif any(k in text.lower() for k in ["kiến thức", "tự chọn", "bắt buộc", "thực tập", "khóa luận", "đồ án", "chuyên đề", "đại cương", "cơ sở ngành"]):
             if len(text) < 100:
                 if is_header_tag or is_bold_p:
                     is_valid_header = True

        # 3. Skip if it's "noisy" text even if it matched (false positives)
        if any(phrase in text.lower() for phrase in noise_phrases):
             is_valid_header = False

        if is_valid_header:
            # Clean up text (add space if missing after dot)
            # "3.4.2.1.Định hướng" -> "3.4.2.1. Định hướng"
            # Handle cases like "3.4.2.2.Title" -> "3.4.2.2. Title"
            
            # Find the dot that separates number and title
            match = section_pattern.match(text)
            if match:
                 number_part = match.group(0)
                 rest_part = text[len(number_part):].strip()
                 # Ensure space
                 section_name = f"{number_part.strip()} {rest_part}"
            else:
                 section_name = text.replace('\xa0', ' ')
            
            # Final cleanup of double spaces
            section_name = " ".join(section_name.split())
            break
        
        prev_elem = prev_elem.find_previous_sibling()
    
    # Fallback: check parent dd for header if we're inside an accordion
    if section_name == "Unknown Section":
        parent_dd = table.find_parent('dd')
        if parent_dd:
            # The header is usually in the dt sibling before dd
            parent_dl = parent_dd.find_parent('dl')
            if parent_dl:
                # Get all dt/dd pairs
                dts = parent_dl.find_all('dt')
                dds = parent_dl.find_all('dd')
                for dt, dd in zip(dts, dds):
                    if dd == parent_dd:
                        section_name = clean_text(dt.get_text())
                        break
    
    # Extract courses from data rows
    for row in rows[1:]:
        cells = row.find_all(['td', 'th'])
        if len(cells) < len(headers):
            continue
            
        course_data = extract_course_from_row(cells, column_mapping)
        if course_data:
            courses.append(course_data)
    
    return {
        "section_name": section_name,
        "courses": courses,
        "course_count": len(courses)
    }


def extract_course_container(container) -> Optional[Dict[str, Any]]:
    """
    Extract course information from a container element.
    
    Args:
        container: BeautifulSoup container element
        
    Returns:
        Dict containing section data with courses, or None if no courses found
    """
    # Look for course codes and names in the container
    courses = []
    
    # Pattern to match course codes (e.g., IT001, MA003, NT105)
    course_code_pattern = re.compile(r'\b[A-Z]{2,4}\d{3,4}\b')
    
    text_content = container.get_text()
    course_codes = course_code_pattern.findall(text_content)
    
    for code in course_codes:
        # Try to find the course name near the code
        course_name = extract_course_name_near_code(container, code)
        
        courses.append({
            "code": code,
            "name": course_name or "Unknown Course",
            "credits": None,
            "prerequisites": [],
            "description": ""
        })
    
    if not courses:
        return None
    
    return {
        "section_name": "Extracted Courses",
        "courses": courses,
        "course_count": len(courses)
    }


def identify_column_mapping(headers: List[str]) -> Optional[Dict[str, int]]:
    """
    Identify column mapping from table headers.
    
    Args:
        headers: List of header texts
        
    Returns:
        Dict mapping field names to column indices, or None if no mapping found
    """
    mapping = {}
    
    for i, header in enumerate(headers):
        header_lower = header.lower()
        
        # Map common Vietnamese and English column names
        if any(term in header_lower for term in ['mã', 'code', 'mã môn']):
            mapping['code'] = i
        elif any(term in header_lower for term in ['tên', 'name', 'môn học', 'course']):
            mapping['name'] = i
        elif any(term in header_lower for term in ['tín chỉ', 'credit', 'tc', 'số tc']):
            mapping['credits'] = i
        elif any(term in header_lower for term in ['tiên quyết', 'prerequisite', 'điều kiện']):
            mapping['prerequisites'] = i
        elif any(term in header_lower for term in ['ghi chú', 'note', 'mô tả', 'description']):
            mapping['description'] = i
    
    # Return mapping only if we found at least code and name columns
    return mapping if 'code' in mapping and 'name' in mapping else None


def extract_course_from_row(cells, column_mapping: Dict[str, int]) -> Optional[Dict[str, Any]]:
    """
    Extract course data from a table row.
    
    Args:
        cells: List of table cells
        column_mapping: Mapping of field names to column indices
        
    Returns:
        Dict containing course data, or None if invalid
    """
    if len(cells) <= max(column_mapping.values()):
        return None
    
    # Extract basic course information
    code = clean_text(cells[column_mapping['code']].get_text()) if 'code' in column_mapping else ""
    name = clean_text(cells[column_mapping['name']].get_text()) if 'name' in column_mapping else ""
    
    # Skip rows without valid course code
    if not code or not re.match(r'^[A-Z]{2,4}\d{3,4}$', code):
        return None
    
    course_data = {
        "code": code,
        "name": name,
        "credits": None,
        "prerequisites": [],
        "description": ""
    }
    
    # Extract credits if available
    if 'credits' in column_mapping:
        credits_text = clean_text(cells[column_mapping['credits']].get_text())
        try:
            course_data['credits'] = int(credits_text) if credits_text.isdigit() else None
        except (ValueError, AttributeError):
            pass
    
    # Extract prerequisites if available
    if 'prerequisites' in column_mapping:
        prereq_text = clean_text(cells[column_mapping['prerequisites']].get_text())
        course_data['prerequisites'] = extract_prerequisite_codes(prereq_text)
    
    # Extract description if available
    if 'description' in column_mapping:
        course_data['description'] = clean_text(cells[column_mapping['description']].get_text())
    
    return course_data


def extract_prerequisite_codes(text: str) -> List[str]:
    """
    Extract course codes from prerequisite text.
    
    Args:
        text: Text containing prerequisite information
        
    Returns:
        List of prerequisite course codes
    """
    if not text:
        return []
    
    # Pattern to match course codes
    course_code_pattern = re.compile(r'\b[A-Z]{2,4}\d{3,4}\b')
    return course_code_pattern.findall(text)


def extract_course_name_near_code(container, code: str) -> Optional[str]:
    """
    Extract course name that appears near a course code.
    
    Args:
        container: BeautifulSoup container element
        code: Course code to find name for
        
    Returns:
        Course name if found, None otherwise
    """
    # This is a simplified implementation
    # In practice, you'd need more sophisticated text analysis
    text = container.get_text()
    
    # Look for the code in the text and try to extract nearby text as name
    code_index = text.find(code)
    if code_index == -1:
        return None
    
    # Extract text after the code (simplified approach)
    after_code = text[code_index + len(code):code_index + len(code) + 100]
    
    # Clean and extract potential course name
    lines = after_code.split('\n')
    for line in lines:
        cleaned = clean_text(line)
        if cleaned and len(cleaned) > 5:  # Reasonable course name length
            return cleaned
    
    return None


def extract_graduation_criteria(soup: BeautifulSoup) -> Optional[str]:
    """
    Extract graduation criteria section.
    
    Args:
        soup: BeautifulSoup object
        
    Returns:
        String content of graduation criteria or None
    """
    # Look for header containing "Điều kiện tốt nghiệp" or "Công nhận tốt nghiệp"
    # Common headers are h3, h4, or strong inside p, or just a p with strong text
    candidates = soup.find_all(['h3', 'h4', 'strong', 'b', 'p'])
    
    target_header = None
    for h in candidates:
        text = h.get_text().strip().lower()
        # Check for key phrases
        if ("điều kiện tốt nghiệp" in text or "công nhận tốt nghiệp" in text):
            # precise check to avoid finding random sentences mentioning it
            if len(text) < 100: 
                target_header = h
                break
            # If it's a paragraph starting with the bold text "Công nhận tốt nghiệp:"
            if h.name == 'p' and (text.startswith("điều kiện tốt nghiệp") or text.startswith("công nhận tốt nghiệp")):
                 target_header = h
                 break

    if not target_header:
        return None
        
    content = []
    
    # If header is inside a p, we might want to start from the p's siblings
    current_node = target_header
    
    # If it's a bold tag inside a P, typically the content follows immediately or in next siblings
    if target_header.name in ['strong', 'b'] and target_header.parent.name == 'p':
        # If the P only contains this header, move to P's sibling
        # Check if the text of parent is roughly same as text of bold tag
        parent_text = target_header.parent.get_text().strip()
        header_text = target_header.get_text().strip()
        
        if len(parent_text) <= len(header_text) + 5:
             current_node = target_header.parent
        else:
             # content is inside the same P, after the bold tag
             # We capture the whole parent text as it likely contains the criteria
             content.append(parent_text)
             # We might have captured it all, but let's check next siblings of P just in case it continues
             current_node = target_header.parent

    curr = current_node.next_sibling
    
    while curr:
        # Stop if we hit another header-like element
        if curr.name in ['h2', 'h3', 'h4', 'h5']:
            break
            
        # Stop if we hit a strong/b tag that looks like a simplified header (e.g. "6. ...")
        if curr.name in ['p', 'div']:
            strong_child = curr.find(['strong', 'b'])
            if strong_child:
                s_text = strong_child.get_text().strip()
                # Check if it starts with a number and looks like a header (e.g. "6. Reference")
                if re.match(r'^\d+\.', s_text):
                    break
        
        # Stop if we hit a table (usually means next section started)
        if curr.name == 'table':
            break

        if hasattr(curr, 'get_text'):
            text = curr.get_text().strip()
            if text:
                content.append(text)
        
        curr = curr.next_sibling
        
    return "\n".join(content) if content else None