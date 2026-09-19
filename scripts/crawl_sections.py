# =============================================================================
# Shared section constants for UIT program crawlers
# =============================================================================

TARGET_SECTIONS = [
    "chương trình đào tạo",
    "danh mục môn học",  # Contains course pools and details
    "kế hoạch giảng dạy",
    "tốt nghiệp",        # Broader to catch "Điều kiện tốt nghiệp", "Khối kiến thức tốt nghiệp"
    "khác biệt",         # For "Sự khác biệt..."
    "quy định",          # For "Các quy định khác"
    "tài năng",          # For "Chương trình tài năng" section on Type B pages
    "lưu ý",             # For notes/footnotes explaining credit types, course equivalencies
    "quy định anh văn"   # For English proficiency rules (TOEIC for IS Tiên Tiến)
]

