"""
Expectation suite đơn giản (không bắt buộc Great Expectations).

Sinh viên có thể thay bằng GE / pydantic / custom — miễn là có halt có kiểm soát.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Tuple


@dataclass
class ExpectationResult:
    name: str
    passed: bool
    severity: str  # "warn" | "halt"
    detail: str


def run_expectations(cleaned_rows: List[Dict[str, Any]]) -> Tuple[List[ExpectationResult], bool]:
    """
    Trả về (results, should_halt).

    should_halt = True nếu có bất kỳ expectation severity halt nào fail.
    """
    results: List[ExpectationResult] = []

    # E1: có ít nhất 1 dòng sau clean
    ok = len(cleaned_rows) >= 1
    results.append(
        ExpectationResult(
            "min_one_row",
            ok,
            "halt",
            f"cleaned_rows={len(cleaned_rows)}",
        )
    )

    # E2: không doc_id rỗng
    bad_doc = [r for r in cleaned_rows if not (r.get("doc_id") or "").strip()]
    ok2 = len(bad_doc) == 0
    results.append(
        ExpectationResult(
            "no_empty_doc_id",
            ok2,
            "halt",
            f"empty_doc_id_count={len(bad_doc)}",
        )
    )

    # E3: policy refund không được chứa cửa sổ sai 14 ngày (sau khi đã fix)
    bad_refund = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "policy_refund_v4"
        and "14 ngày làm việc" in (r.get("chunk_text") or "")
    ]
    ok3 = len(bad_refund) == 0
    results.append(
        ExpectationResult(
            "refund_no_stale_14d_window",
            ok3,
            "halt",
            f"violations={len(bad_refund)}",
        )
    )

    # E4: chunk_text đủ dài
    short = [r for r in cleaned_rows if len((r.get("chunk_text") or "")) < 8]
    ok4 = len(short) == 0
    results.append(
        ExpectationResult(
            "chunk_min_length_8",
            ok4,
            "warn",
            f"short_chunks={len(short)}",
        )
    )

    # E5: effective_date đúng định dạng ISO sau clean (phát hiện parser lỏng)
    iso_bad = [
        r
        for r in cleaned_rows
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", (r.get("effective_date") or "").strip())
    ]
    ok5 = len(iso_bad) == 0
    results.append(
        ExpectationResult(
            "effective_date_iso_yyyy_mm_dd",
            ok5,
            "halt",
            f"non_iso_rows={len(iso_bad)}",
        )
    )

    # E6: không còn marker phép năm cũ 10 ngày trên doc HR (conflict version sau clean)
    bad_hr_annual = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "hr_leave_policy"
        and "10 ngày phép năm" in (r.get("chunk_text") or "")
    ]
    ok6 = len(bad_hr_annual) == 0
    results.append(
        ExpectationResult(
            "hr_leave_no_stale_10d_annual",
            ok6,
            "halt",
            f"violations={len(bad_hr_annual)}",
        )
    )

    # E7: tất cả nguồn canonical dùng trong bộ test phải còn hiện diện sau clean.
    required_doc_ids = {
        "policy_refund_v4",
        "sla_p1_2026",
        "it_helpdesk_faq",
        "hr_leave_policy",
        "access_control_sop",
    }
    present_doc_ids = {str(r.get("doc_id") or "") for r in cleaned_rows}
    missing_doc_ids = sorted(required_doc_ids - present_doc_ids)
    ok7 = not missing_doc_ids
    results.append(
        ExpectationResult(
            "required_canonical_doc_ids_present",
            ok7,
            "halt",
            f"missing_doc_ids={missing_doc_ids}",
        )
    )

    # E8: exported_at phải parse được để freshness monitor không dựa vào timestamp rác.
    exported_bad = []
    for r in cleaned_rows:
        ts = str(r.get("exported_at") or "").strip()
        try:
            datetime.fromisoformat(ts)
        except ValueError:
            exported_bad.append(r)
    ok8 = len(exported_bad) == 0
    results.append(
        ExpectationResult(
            "exported_at_parseable_iso_datetime",
            ok8,
            "halt",
            f"invalid_exported_at={len(exported_bad)}",
        )
    )

    # E9: marker dữ liệu mơ hồ không được publish vào vector store.
    unclear = [
        r
        for r in cleaned_rows
        if "Nội dung không rõ ràng" in (r.get("chunk_text") or "")
    ]
    ok9 = len(unclear) == 0
    results.append(
        ExpectationResult(
            "no_unclear_content_marker",
            ok9,
            "halt",
            f"unclear_chunks={len(unclear)}",
        )
    )

    # E10: cảnh báo nếu một nguồn canonical có quá ít chunk, thường là allowlist/quarantine sai.
    doc_counts: Dict[str, int] = {}
    for r in cleaned_rows:
        doc = str(r.get("doc_id") or "")
        doc_counts[doc] = doc_counts.get(doc, 0) + 1
    low_volume = sorted(doc for doc in required_doc_ids if doc_counts.get(doc, 0) < 2)
    ok10 = not low_volume
    results.append(
        ExpectationResult(
            "canonical_doc_min_two_chunks",
            ok10,
            "warn",
            f"low_volume_doc_ids={low_volume}; counts={doc_counts}",
        )
    )

    halt = any(not r.passed and r.severity == "halt" for r in results)
    return results, halt
