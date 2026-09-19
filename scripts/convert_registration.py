"""Convert already-crawled UIT JSON into registration-focused Lab 07 Markdown.

Offline only. Does not infer publication dates, permissions, or faculty content.
"""

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

SOURCES = ('doc_id', 'file_path', 'title', 'source_url', 'retrieved_at',
           'document_version', 'license_or_permission')
AUDIT = ('raw_file', 'doc_id', 'status', 'reason', 'source_url')
CATALOG_URLS = {
    'course_list.json': 'https://student.uit.edu.vn/danh-muc-mon-hoc-dai-hoc',
    'course_summaries.json': 'https://student.uit.edu.vn/content/bang-tom-tat-mon-hoc',
}
SELECT_FACULTIES = ('AI', 'CE', 'CS', 'DS', 'IS', 'IT', 'NC', 'SE')
EXCLUDED_VARIANTS = ('tài năng', 'tiên tiến', 'việt nhật', 'birmingham', 'newcastle')
DEFAULT_LAB_DATE = '2026-09-19'


def normal(value):
    return unicodedata.normalize('NFKC', str(value)).casefold()


def slug(value):
    value = unicodedata.normalize('NFKD', str(value).replace('đ', 'd').replace('Đ', 'D'))
    value = value.encode('ascii', 'ignore').decode('ascii').lower()
    return re.sub(r'-+', '-', re.sub('[^a-z0-9]+', '-', value)).strip('-')


def quoted(value):
    return json.dumps(str(value), ensure_ascii=False)


def source_url(value):
    url = str(value).strip()
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname != 'student.uit.edu.vn':
        raise ValueError('Expected official public student.uit.edu.vn HTTPS source URL')
    if parsed.username or parsed.password:
        raise ValueError('Source URL contains credentials')
    return url


def date_from_metadata(meta):
    stamp = str(meta.get('crawled_at') or meta.get('scraped_at') or
                meta.get('retrieved_at') or '')[:10]
    if stamp and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', stamp):
        raise ValueError('Malformed original retrieval date')
    return stamp or 'not-stated'


def trim_graduation_heading_blocks(text):
    """Remove whole titled graduation subsections, retain other source wording."""
    lines, kept, skipped_at = str(text).splitlines(), [], None
    for line in lines:
        match = re.match(r'^(#{1,6})\s+(.+)', line)
        if match:
            level = len(match.group(1))
            if skipped_at is not None and level <= skipped_at:
                skipped_at = None
            if 'tốt nghiệp' in normal(match.group(2)) and skipped_at is None:
                skipped_at = level
        if skipped_at is None:
            kept.append(line)
    return '\n'.join(kept).strip()


def program_parts(doc):
    sections = doc.get('sections')
    if not isinstance(sections, dict):
        raise ValueError('Expected sectioned program JSON; cannot safely extract courses')
    parts = []
    for key, label in (('chương trình đào tạo', 'Danh mục và lựa chọn học phần'),
                       ('kế hoạch giảng dạy', 'Kế hoạch học phần theo học kỳ')):
        text = trim_graduation_heading_blocks(sections.get(key, ''))
        if text:
            parts.append(f'## {label}\n\n{text}')
    for key in ('quy định anh văn', 'quy định', 'lưu ý'):
        text = str(sections.get(key, '')).strip()
        if text and 'đăng ký học phần' in normal(text):
            parts.append(f'## {key.capitalize()} liên quan đến đăng ký học phần\n\n'
                         + trim_graduation_heading_blocks(text))
    # Honors appendices are a separate source section; do not silently mix them
    # into the regular program's shared curriculum.
    honors = sections.get('tài năng', '')
    is_honors = 'tài năng' in normal(doc.get('metadata', {}).get('program_name', ''))
    if is_honors and honors and 'yêu cầu về môn học tài năng' in normal(honors):
        match = re.search(r'(?im)^#\s*\d+\.\s*yêu cầu về môn học tài năng[^\n]*', honors)
        if match:
            tail = honors[match.start():]
            following = re.search(r'(?m)^#\s+', tail[match.end()-match.start():])
            if following:
                tail = tail[:match.end()-match.start() + following.start()]
            parts.append('## Yêu cầu lựa chọn học phần tài năng\n\n' + tail.strip())
    if not parts:
        raise ValueError('No program course/curriculum/teaching-plan sections found')
    return '\n\n'.join(parts)


def course_parts(name, records):
    if not isinstance(records, list) or not records:
        raise ValueError('Expected nonempty course-record list')
    if name == 'course_list.json':
        required = ('code', 'name_vi', 'prereq_code', 'prev_code', 'equiv_code')
        heading = '# Danh mục môn học UIT (dữ liệu đã crawl)'
        fields = ('code', 'name_vi', 'name_en', 'is_open', 'faculty', 'type',
                  'old_code', 'equiv_code', 'prereq_code', 'prev_code',
                  'credit_theory', 'credit_practice')
    else:
        required = ('code', 'name', 'summary')
        heading = '# Bảng tóm tắt môn học UIT (tài liệu bổ trợ)'
        fields = ('code', 'name', 'summary')
    parts = [heading]
    seen = set()
    for row in records:
        if not isinstance(row, dict) or any(field not in row for field in required):
            raise ValueError('Course record missing required source field')
        code = str(row['code']).strip()
        if not code or code in seen:
            raise ValueError('Missing or duplicate course code')
        seen.add(code)
        title = str(row.get('name_vi') or row.get('name') or '').strip()
        lines = [f'## {code} — {title}']
        for key in fields:
            value = row.get(key)
            if isinstance(value, list):
                rendered = ', '.join(map(str, value)) if value else '[]'
            elif isinstance(value, bool):
                rendered = str(value).lower()
            else:
                rendered = str(value if value is not None else '')
            lines.append(f'- {key}: {rendered}')
        parts.append('\n'.join(lines))
    return '\n\n'.join(parts)


def document_fields(doc_id, title, url, retrieved_at, audience, department,
                    category, cohort='', raw_file='', version='not-stated',
                    processed_at='', retrieval_date_basis='original-crawl-metadata',
                    original_crawled_at='', audience_basis='source-context'):
    return {
        'doc_id': doc_id, 'title': title, 'source_url': url,
        'retrieved_at': retrieved_at, 'document_version': version,
        'audience': audience, 'department': department, 'category': category,
        'language': 'vi', 'cohort': cohort, 'raw_file': raw_file,
        'processed_at': processed_at, 'retrieval_date_basis': retrieval_date_basis,
        'original_crawled_at': original_crawled_at, 'audience_basis': audience_basis,
    }


def to_markdown(fields, content):
    return '---\n' + ''.join(f'{k}: {quoted(v)}\n' for k, v in fields.items()) + \
           '---\n\n' + f'# {fields["title"]}\n\n' + content.strip() + '\n'


def write_csv(path, fieldnames, rows):
    with path.open('w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build(input_dir, output_dir, catalog_retrieved_at=None, processed_at=None,
          uniform_date=None):
    input_dir, output_dir = Path(input_dir), Path(output_dir)
    for label, date in (('catalog_retrieved_at', catalog_retrieved_at),
                        ('processed_at', processed_at), ('uniform_date', uniform_date)):
        if date is not None:
            from datetime import date as date_type
            try:
                if date_type.fromisoformat(date).isoformat() != date:
                    raise ValueError()
            except ValueError as exc:
                raise ValueError(f'{label} must be YYYY-MM-DD') from exc
    all_dir = output_dir / 'all-converted'
    selected_dir = output_dir / 'data' / 'dang-ky-hoc-phan'
    all_dir.mkdir(parents=True, exist_ok=True)
    selected_dir.mkdir(parents=True, exist_ok=True)
    for folder in (all_dir, selected_dir):
        for old in folder.glob('*.md'):
            old.unlink()  # These two directories contain only generated Markdown.

    records, audit, selected_candidates, encountered = [], [], [], set()
    source_content = {}
    raw_paths = sorted(p for p in input_dir.rglob('*.json')
                       if p.name.startswith('K18_') or p.name in CATALOG_URLS)
    for path in raw_paths:
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
            if path.name in CATALOG_URLS:
                url = source_url(CATALOG_URLS[path.name])
                key = path.stem.replace('_', '-')
                doc_id = key
                title = ('Danh mục môn học UIT' if key == 'course-list'
                         else 'Bảng tóm tắt môn học UIT')
                body = course_parts(path.name, payload)
                retrieved = catalog_retrieved_at or 'not-stated'
                date_basis = ('user-provided-unverified' if catalog_retrieved_at
                              else 'missing-original-crawl-timestamp')
                original_crawled_at = ''
                audience_basis = 'user-assigned-for-lab-not-source-verified'
                faculty, cohort = 'all', ''
                category = 'course-catalog' if key == 'course-list' else 'course-description'
                candidate = True
                reason = ('catalog supports prerequisites, equivalence and credit checks'
                          if key == 'course-list' else
                          'course descriptions support selecting appropriate courses; not registration rules')
            else:
                if not isinstance(payload, dict):
                    raise ValueError('Expected program object')
                meta = payload['metadata']
                url = source_url(meta['url'])
                cohort = str(meta.get('cohort', '')).strip()
                if cohort != 'K18':
                    raise ValueError('Out-of-scope cohort')
                faculty = str(meta.get('faculty', '')).strip()
                name = str(meta['program_name']).strip()
                if not name:
                    raise ValueError('Program has no name')
                audience = meta.get('audience', 'student')
                if audience not in ('student', 'all'):
                    raise ValueError('Unverified or conflicting program audience')
                body = program_parts(payload)
                digest = hashlib.sha256(name.encode('utf-8')).hexdigest()[:8]
                doc_id = f'k18-{slug(faculty)}-{slug(name)[:52].rstrip("-")}-{digest}'
                title = f'Lựa chọn học phần — {name}'
                retrieved = date_from_metadata(meta)
                date_basis = 'original-crawl-metadata'
                original_crawled_at = str(meta.get('crawled_at') or meta.get('scraped_at') or '')
                audience_basis = 'source-context'
                category = 'curriculum-selection'
                candidate = (faculty in SELECT_FACULTIES and
                             not any(word in normal(name).replace('-', ' ')
                                     for word in EXCLUDED_VARIANTS))
                reason = ('standard K18 curriculum selected' if candidate else
                          'additional program variant; retained in full converted archive')
            if path.name in CATALOG_URLS:
                audience = 'staff'  # User-assigned lab classification, NOT a source fact.
            if uniform_date:
                retrieved = uniform_date  # User-assigned date, not a new crawl event.
                date_basis = 'user-assigned-not-verified'
            if doc_id in encountered:
                raise ValueError('Duplicate doc_id: check duplicate input files')
            encountered.add(doc_id)
            version = ('not-stated' if path.name in CATALOG_URLS else
                       str(payload['metadata'].get('document_version') or 'not-stated'))
            fields = document_fields(doc_id, title, url, retrieved, audience,
                                     faculty.lower(), category, cohort, path.name, version,
                                     processed_at or uniform_date or '', date_basis,
                                     original_crawled_at, audience_basis)
            md = to_markdown(fields, body)
            (all_dir / (doc_id + '.md')).write_text(md, encoding='utf-8')
            records.append((fields, md))
            source_content[doc_id] = (url, hashlib.sha256(body.encode('utf-8')).hexdigest())
            selected_candidates.append((fields, md, candidate, reason, path.name))
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
            audit.append({'raw_file': path.name, 'doc_id': '', 'status': 'error',
                          'reason': str(error), 'source_url': ''})

    # Exactly one standard program per faculty; never treat two variants on the
    # same URL as the same rule. Reuse only the selected program identity.
    chosen_faculties = set()
    selected = []
    duplicate_counts = {}
    for original_source, body_hash in source_content.values():
        key = (original_source, body_hash)
        duplicate_counts[key] = duplicate_counts.get(key, 0) + 1
    for fields, md, candidate, reason, filename in sorted(
            selected_candidates, key=lambda item: (item[0]['category'] != 'course-catalog',
                                                    SELECT_FACULTIES.index(item[0]['department'].upper())
                                                    if item[0]['department'].upper() in SELECT_FACULTIES else 99,
                                                    item[0]['doc_id'])):
        faculty = fields['department'].upper()
        if not candidate and duplicate_counts[source_content[fields['doc_id']]] > 1:
            reason = 'duplicate extracted course content at same source URL; program variant needs source review'
        if candidate and faculty in SELECT_FACULTIES and faculty in chosen_faculties:
            candidate = False
            reason = 'duplicate selected faculty or source curriculum; check program variants'
        if candidate and len(selected) >= 10:
            candidate = False
            reason = 'over 10 documents; retained in full converted archive'
        if candidate:
            (selected_dir / (fields['doc_id'] + '.md')).write_text(md, encoding='utf-8')
            selected.append(fields)
            if faculty in SELECT_FACULTIES:
                chosen_faculties.add(faculty)
        audit.append({'raw_file': filename, 'doc_id': fields['doc_id'],
                      'status': 'selected' if candidate else 'not-selected',
                      'reason': reason, 'source_url': fields['source_url']})

    def manifest(fields, prefix):
        return {'doc_id': fields['doc_id'], 'file_path': f'{prefix}/{fields["doc_id"]}.md',
                'title': fields['title'], 'source_url': fields['source_url'],
                'retrieved_at': fields['retrieved_at'],
                'document_version': fields['document_version'],
                'license_or_permission': 'permission-not-verified'}

    write_csv(all_dir / 'sources.csv', SOURCES,
              [manifest(fields, 'all-converted') for fields, _ in records])
    write_csv(selected_dir / 'sources.csv', SOURCES,
              [manifest(fields, 'data/dang-ky-hoc-phan') for fields in selected])
    write_csv(output_dir / 'audit.csv', AUDIT, audit)
    issues = []
    for fields in selected:
        if fields['retrieved_at'] == 'not-stated':
            issues.append({'doc_id': fields['doc_id'], 'issue': 'missing_retrieval_date',
                           'action': 'Recover date from original crawl log or re-collect with authorization'})
        if fields['retrieval_date_basis'] == 'user-provided-unverified':
            issues.append({'doc_id': fields['doc_id'], 'issue': 'unverified_user_supplied_retrieval_date',
                           'action': 'Date supplied by user, not evidenced by original crawl log; verify before submission'})
        if fields['retrieval_date_basis'] == 'user-assigned-not-verified':
            issues.append({'doc_id': fields['doc_id'], 'issue': 'user_assigned_retrieval_date',
                           'action': '2026-09-19 is an assigned lab date, not proof of retrieval; original timestamp is retained where available'})
        issues.append({'doc_id': fields['doc_id'], 'issue': 'permission_not_verified',
                       'action': 'Check site terms, robots and reuse permissions before submission'})
    if len(set(fields['audience'] for fields in selected)) < 2:
        issues.append({'doc_id': '', 'issue': 'only_student_audience',
                       'action': 'Add actual faculty/staff rules with distinct source text; do not relabel'})
    elif any(fields['audience_basis'] == 'user-assigned-for-lab-not-source-verified'
             for fields in selected):
        issues.append({'doc_id': '', 'issue': 'audience_label_not_source_supported',
                       'action': 'Staff catalog label is user-assigned; do not claim the source defines staff-only policy'})
    issues.append({'doc_id': '', 'issue': 'registration_process_sources_missing',
                   'action': 'Obtain authoritative registration window, add/drop and credit-limit policies'})
    write_csv(output_dir / 'validation_issues.csv', ('doc_id', 'issue', 'action'), issues)
    return {'converted': len(records), 'selected': len(selected),
            'errors': sum(r['status'] == 'error' for r in audit), 'issues': len(issues)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, default=Path(__file__).parent / 'input')
    parser.add_argument('--output-dir', type=Path, default=Path(__file__).parent)
    parser.add_argument('--catalog-retrieved-at', help='User-provided catalog date YYYY-MM-DD (unverified until checked against logs)')
    parser.add_argument('--processed-at', help='Date when JSON was converted, YYYY-MM-DD')
    parser.add_argument('--uniform-date', default=DEFAULT_LAB_DATE,
                        help='User-assigned lab date for all files (not proof of new crawl)')
    args = parser.parse_args()
    result = build(args.input_dir, args.output_dir, args.catalog_retrieved_at,
                   args.processed_at, args.uniform_date)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
