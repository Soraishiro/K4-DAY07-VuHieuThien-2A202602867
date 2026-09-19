import argparse
import csv
import json
import logging
import os
import requests
import time
from bs4 import BeautifulSoup
import extraction_utils  # Assuming this exists in the same dir

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def fetch_html(url):
    logger.info(f"Fetching {url}...")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return None


def process_single_url(
    url, cohort, default_faculty, output_dir, target_program_name=None
):
    html = fetch_html(url)
    if not html:
        return

    soup = BeautifulSoup(html, "html.parser")

    # 1. Detect multiple programs (Accordions)
    # The student portal uses various classes like 'styled', 'accordion', or no class at all
    dl_tag = (
        soup.find("dl", class_="styled")
        or soup.find("dl", class_="accordion")
        or soup.find("dl")
    )
    programs_found = []

    def normalize_compare(t):
        if not t:
            return ""
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

    if dl_tag:
        dts = dl_tag.find_all("dt")
        dds = dl_tag.find_all("dd")

        if len(dts) == len(dds) and len(dts) > 0:
            logger.info(f"Found {len(dts)} sections in curriculum accordion.")
            for dt, dd in zip(dts, dds):
                sub_name = dt.get_text().strip()
                s_norm = normalize_compare(sub_name)

                # ALWAYS Skip administrative noise
                # "văn bằng" covers "văn bằng 2", "văn bằng đại học thứ 2"
                if any(
                    x in s_norm for x in ["văn bằng", "liên thông", "thứ 2", "thứ hai"]
                ):
                    logger.info(f"Skipping administrative section: {sub_name}")
                    continue

                # Targeted Filtering
                if target_program_name:
                    t_norm = normalize_compare(target_program_name)

                    is_vn_search = "việt nhật" in t_norm
                    is_vn_section = "việt nhật" in s_norm

                    # Disambiguation Logic:
                    if is_vn_search and not is_vn_section:
                        logger.info(f"Skipping '{sub_name}' (Target is Viet-Nhat)")
                        continue
                    if not is_vn_search and is_vn_section:
                        logger.info(f"Skipping '{sub_name}' (Target is Standard)")
                        continue

                    # Honors check
                    is_h_search = "tài năng" in t_norm
                    is_h_section = "tài năng" in s_norm
                    if is_h_search != is_h_section:
                        continue

                program_key = f"{cohort}_{sub_name}"
                programs_found.append((program_key, str(dd), sub_name))
        else:
            logger.warning(
                "DL found but no clear DT/DD pairs. Falling back to whole page."
            )

    if not programs_found:
        # Fallback for single program pages
        title_tag = soup.find("h1", class_="page-header") or soup.find(
            "h1", class_="title"
        )
        p_name = title_tag.get_text().strip() if title_tag else "Unknown Program"
        programs_found.append((f"{cohort}_{p_name}", str(soup), p_name))

    # 2. Extract Data for each program found
    for p_key, content_html, p_name in programs_found:
        logger.info(f"Extracting data for: {p_name}")

        extracted_data = extraction_utils.extract_program_data(content_html, p_name)

        if extracted_data:
            extracted_data["metadata"] = {
                "url": url,
                "cohort": cohort,
                "faculty": default_faculty,
                "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

            # 3. Save to output in cohort-specific subdirectory
            # Update output_dir to include cohort if it's not already there
            cohort_dir = os.path.join(output_dir, cohort)
            os.makedirs(cohort_dir, exist_ok=True)

            # Make filename unique to the program name, faculty, AND cohort
            import re

            # 1. Normalize Names
            req_name = (
                target_program_name.lower().replace("-", " ")
                if target_program_name
                else ""
            )
            found_name = p_name.lower().replace("-", " ")

            # 2. Determine Program Type
            prog_type = ""
            if "tài năng" in req_name or "tài năng" in found_name:
                prog_type = "_Honors"
            elif "việt nhật" in req_name or "việt nhật" in found_name:
                prog_type = "_VietNhat"
            elif "tiên tiến" in req_name or "tiên tiến" in found_name:
                prog_type = "_Advanced"
            elif "song ngành" in req_name or "song ngành" in found_name:
                prog_type = "_Dual"

            # 3. Create a concise label
            raw_label = target_program_name if target_program_name else p_name
            clean_label = (
                raw_label.replace("Cử nhân ngành", "")
                .replace("Kỹ sư", "")
                .replace("ngành", "")
                .replace("Chương trình", "")
            )
            clean_label = re.sub(
                r"\(?Áp dụng từ khóa.*", "", clean_label, flags=re.IGNORECASE
            )
            clean_label = re.sub(
                r"\(?tài năng\)?", "", clean_label, flags=re.IGNORECASE
            )
            clean_label = re.sub(
                r"\(?tiên tiến\)?", "", clean_label, flags=re.IGNORECASE
            )
            clean_label = re.sub(
                r"\(?việt.*nhật\)?", "", clean_label, flags=re.IGNORECASE
            )

            # Final sanitization
            clean_label = re.sub(r"[^\w\s-]", "", clean_label).strip().replace(" ", "_")
            clean_label = re.sub(r"_+", "_", clean_label).strip("_")

            # Map common long names to acronyms (normalized for accents)
            # We strip the label if it effectively just repeats the faculty name
            norm_label = clean_label.lower().replace("_", " ")
            fac_match = False
            if default_faculty == "CS" and "khoa học máy tính" in norm_label:
                fac_match = True
            if default_faculty == "IT" and "công nghệ thông tin" in norm_label:
                fac_match = True
            if default_faculty == "SE" and "kỹ thuật phần mềm" in norm_label:
                fac_match = True
            if default_faculty == "AI" and "trí tuệ nhân tạo" in norm_label:
                fac_match = True
            if default_faculty == "IS" and "hệ thống thông tin" in norm_label:
                fac_match = True
            if default_faculty == "NC" and "mạng máy tính" in norm_label:
                fac_match = True
            if default_faculty == "CE" and "kỹ thuật máy tính" in norm_label:
                fac_match = True
            if default_faculty == "DS" and "khoa học dữ liệu" in norm_label:
                fac_match = True

            if fac_match:
                clean_label = ""

            # 4. Final Filename: COHORT_FACULTY_TYPE_LABEL.json
            parts = [cohort, default_faculty]
            if prog_type:
                parts.append(prog_type.strip("_"))
            if clean_label:
                parts.append(clean_label)

            filename = "_".join(parts) + ".json"
            outfile = os.path.join(cohort_dir, filename)

            with open(outfile, "w", encoding="utf-8") as f:
                json.dump(extracted_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved data to {outfile}")

        else:
            logger.warning(f"Failed to extract structured data for {p_name}")


def main():
    parser = argparse.ArgumentParser(description="Targeted Academic Crawler for UIT")

    # Mode 1: Single URL
    parser.add_argument("--url", help="Target URL to crawl")
    parser.add_argument("--cohort", help="Cohort identifier (e.g., K18)")
    parser.add_argument("--faculty", help="Faculty code (e.g., SE, CS)")
    parser.add_argument(
        "--name", help="Specific program name to target (for multi-program URLs)"
    )

    # Mode 2: Batch from CSV
    parser.add_argument("--input-file", help="Path to metadata.csv")

    # Common
    parser.add_argument(
        "--output-dir",
        default="data/raw/student_portal/curriculum/",
        help="Base output directory",
    )

    args = parser.parse_args()

    if args.url:
        if not args.cohort:
            logger.error("--cohort is required with --url")
            return
        logger.info(f"Starting single crawl for {args.url}")
        process_single_url(
            args.url, args.cohort, args.faculty, args.output_dir, args.name
        )

    elif args.input_file:
        logger.info(f"Starting batch crawl from {args.input_file}")
        with open(args.input_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row["URL"]
                cohort = row["Cohort"]
                faculty = row["Faculty"]
                name = row.get("Program Name", None)  # Pass the name from CSV

                process_single_url(url, cohort, faculty, args.output_dir, name)
                time.sleep(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
