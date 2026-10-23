"""FrailtyScope v0.45: local, metadata-only triage of study-team response CSVs.

Never opens supporting documents, model binaries or patient records, never writes the
review responses into the repository, and cannot confer research/clinical approval.
The returned JSON contains only counts and canonical request IDs, not references.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import stat
from collections import Counter
from pathlib import Path

SCHEMA = 'FRAILTYSCOPE_STUDY_EVIDENCE_TRIAGE_V45'
TEMPLATE = 'research/templates/STUDY_TEAM_EVIDENCE_REQUEST_V44.csv'
TEMPLATE_SHA256 = 'd579589f77e79d2ad86028682ad05c5c8f52d35b3db1525e9aa818c3ef902ec6'
HEADER = ('request_id', 'category', 'candidate_source', 'current_evidence_status',
          'reviewer_role', 'requested_evidence', 'approval_status',
          'evidence_reference_to_be_supplied_offline')
STATUSES = ('NOT_RECEIVED', 'IN_REVIEW', 'EVIDENCE_RECEIVED',
            'CHANGES_REQUESTED', 'REJECTED', 'APPROVED')
CATEGORY_COUNTS = {'predictor': 14, 'outcome': 4, 'governance': 7}
OPAQUE = re.compile(r'OFFLINE-[A-Z0-9][A-Z0-9_-]{5,39}\Z')
MAX_BYTES = 128 * 1024


class TriageRefused(ValueError):
    """Public/non-sensitive failure; never embed input values in diagnostics."""


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise TriageRefused('TRIAGE_REFUSED: ' + reason)


def safe_read(path: Path, *, template: bool = False) -> bytes:
    require(path.suffix.lower() == '.csv', 'Expected a CSV file')
    require(not path.is_symlink(), 'Symlinked review files are not accepted')
    try:
        mode = path.stat()
    except OSError as exc:
        raise TriageRefused('TRIAGE_REFUSED: File unavailable') from exc
    require(stat.S_ISREG(mode.st_mode), 'Expected a regular file')
    require(0 < mode.st_size <= MAX_BYTES, 'Unexpected file size')
    data = path.read_bytes()
    require(len(data) <= MAX_BYTES and b'\0' not in data, 'Unsupported binary input')
    if template:
        require(hashlib.sha256(data).hexdigest() == TEMPLATE_SHA256,
                'Public v0.44 request template changed; re-review required')
    return data


def read_rows(data: bytes) -> list[dict[str, str]]:
    try:
        content = data.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content, newline=''), restkey='__EXTRA__')
        require(tuple(reader.fieldnames or ()) == HEADER, 'CSV header/schema mismatch')
        rows = list(reader)
    except (UnicodeError, csv.Error) as exc:
        raise TriageRefused('TRIAGE_REFUSED: CSV encoding or structure is invalid') from exc
    require(len(rows) == 25, 'Expected exactly 25 evidence request rows')
    require(all('__EXTRA__' not in r and None not in r.values() for r in rows),
            'Malformed CSV column count')
    return rows


def public_template(root: Path) -> list[dict[str, str]]:
    path = root / TEMPLATE
    require(path.is_file() and not path.is_symlink(), 'Public template missing or unsafe')
    rows = read_rows(safe_read(path, template=True))
    require(Counter(r['category'] for r in rows) == CATEGORY_COUNTS,
            'Public template category distribution changed')
    require(len({r['request_id'] for r in rows}) == 25 and
            all(r['approval_status'] == 'NOT_RECEIVED' and
                r['evidence_reference_to_be_supplied_offline'] == '' for r in rows),
            'Public template unexpectedly contains review responses')
    return rows


def triage(root: Path, response_path: Path) -> dict:
    """Check only an explicitly selected response CSV, *outside* the repository.

    No approval signature, data rights, mapping validity, incident outcomes,
    calibration, or independent validation is verified by this function.
    """
    root = root.resolve()
    path = response_path.expanduser()
    require(not path.is_symlink(), 'Symlinked review response rejected')
    require(not path.resolve().is_relative_to(root),
            'Private response must stay outside the public repository')
    expected = public_template(root)
    received = read_rows(safe_read(path))
    status_counts = Counter()
    category_counts = {c: Counter() for c in CATEGORY_COUNTS}
    follow_up_ids = []
    claimed_signoffs = []
    for i, (baseline, actual) in enumerate(zip(expected, received)):
        # The six request-description columns are immutable, including row order.
        require(all(actual[key] == baseline[key] for key in HEADER[:6]),
                f'Immutable request column/order modified (row {i + 1})')
        status = actual['approval_status']
        ref = actual['evidence_reference_to_be_supplied_offline']
        require(status in STATUSES, f'Unsupported review status (row {i + 1})')
        require(bool(OPAQUE.fullmatch(ref)) if ref else True,
                f'Use opaque OFFLINE-... reference only (row {i + 1})')
        require(not (status in ('EVIDENCE_RECEIVED', 'APPROVED') and not ref),
                f'Received/claimed-approval status needs offline ticket (row {i + 1})')
        require(not (status == 'NOT_RECEIVED' and ref),
                f'Unreceived request cannot carry evidence ticket (row {i + 1})')
        status_counts[status] += 1
        category_counts[baseline['category']][status] += 1
        if status != 'APPROVED':
            follow_up_ids.append(baseline['request_id'])
        else:
            claimed_signoffs.append(baseline['request_id'])
    # Even 25 claimed APPROVED statuses do not verify a signature or authorize use.
    return {
        'schema': SCHEMA,
        'scope': 'LOCAL_OFFLINE_CSV_STRUCTURE_ONLY',
        'requests_checked': len(received),
        'status_counts': {s: status_counts[s] for s in STATUSES},
        'categories': {k: {'total':CATEGORY_COUNTS[k],
                           'counts':{s:category_counts[k][s] for s in STATUSES}}
                       for k in CATEGORY_COUNTS},
        'follow_up_request_ids': follow_up_ids,
        'claimed_signoff_request_ids_unverified': claimed_signoffs,
        'evidence_contents_opened': False,
        'signatures_verified': False,
        'approval_documents_verified': 0,
        'real_data_execution_permitted': False,
        'model_fitting_permitted': False,
        'clinical_inference': False,
        'clinical_promotion_decision': 'DENIED',
        'message': 'CSV structure reviewed only. Opaque offline tickets and APPROVED cells do not prove authorized research, model validity, or clinical release.'
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--check-template', action='store_true',
                       help='Verify unchanged public 25-item blank handoff')
    group.add_argument('--review-response', type=Path,
                       help='Read explicit CSV outside repo and print REDACTED status counts only')
    a = p.parse_args()
    try:
        if a.check_template:
            rows = public_template(a.root)
            print(f'PASS: v0.45 public {len(rows)}-request template unchanged; no approvals claimed')
        else:
            report = triage(a.root, a.review_response)
            print(json.dumps(report, indent=2))
    except (TriageRefused, OSError) as exc:
        # Diagnostics are fixed strings; never echo raw CSV contents or file paths.
        raise SystemExit(str(exc)) from None


if __name__ == '__main__':
    main()
