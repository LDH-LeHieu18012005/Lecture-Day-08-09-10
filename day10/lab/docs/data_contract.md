# Data contract — Lab Day 10

Nguồn cấu hình chính: `contracts/data_contract.yaml`  
Owner: `Lê Dương Hiếu - 2A202600635`  
Alert channel: `#data-pipeline-alerts`

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| `policy_refund_v4` | CSV export từ policy system | chunk stale 14 ngày, duplicate window, text lặp | `refund_no_stale_14d_window`, `hits_forbidden` |
| `sla_p1_2026` | CSV export từ support/SLA docs | thiếu escalation/update chunk, timestamp stale | top1 doc, freshness, `required_canonical_doc_ids_present` |
| `it_helpdesk_faq` | CSV export từ FAQ nội bộ | retrieval nhầm với SLA/HR nếu top-k không rerank | eval `q_lockout`, `q_password_rotation` |
| `hr_leave_policy` | CSV export HR | bản 2025 lẫn vào bản 2026, 10 ngày phép năm stale | `hr_leave_no_stale_10d_annual`, `stale_hr_policy_content` |
| `access_control_sop` | CSV export IT Security SOP | nguồn hợp lệ bị baseline quarantine do thiếu allowlist | `required_canonical_doc_ids_present`, grading `gq_d10_09`-`10` |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| `chunk_id` | string | Có | ID ổn định tạo từ `doc_id`, text sau clean và sequence |
| `doc_id` | string | Có | Chỉ nhận 5 nguồn canonical trong allowlist |
| `chunk_text` | string | Có | Đã sửa stale refund, lặp cụm từ và loại nội dung mơ hồ |
| `effective_date` | date | Có | Chuẩn `YYYY-MM-DD`; hỗ trợ input `DD/MM/YYYY` |
| `exported_at` | datetime | Có | Chuẩn `YYYY-MM-DDTHH:MM:SS`; hỗ trợ input slash date |

---

## 3. Quy tắc quarantine vs drop

Pipeline không drop âm thầm. Dòng bị loại được ghi vào `artifacts/quarantine/quarantine_<run-id>.csv` với `reason`. Run `final-clean` có `210` quarantine trên `247` raw record.

| Reason | Ý nghĩa |
|--------|---------|
| `unknown_doc_id` | Không thuộc allowlist canonical |
| `missing_effective_date` | Không đủ ngày hiệu lực để versioning |
| `stale_hr_policy_effective_date` | HR effective date trước `2026-01-01` |
| `stale_hr_policy_content` | Text ghi bản HR 2025 hoặc 10 ngày phép năm |
| `duplicate_chunk_text` | Nội dung duplicate sau normalize |
| `missing_chunk_text` | Chunk rỗng |
| `unclear_content_marker` | Text có marker “Nội dung không rõ ràng” |
| `invalid_exported_at_format` | Timestamp publish không parse được |

Approve merge lại: Lê Dương Hiếu kiểm tra source of truth, sửa contract/allowlist nếu nguồn thật sự canonical, rồi rerun pipeline với expectation pass.

---

## 4. Phiên bản & canonical

Source of truth hiện tại:

- Refund: `data/docs/policy_refund_v4.txt`, cửa sổ hiện hành là 7 ngày làm việc.
- HR: `data/docs/hr_leave_policy.txt`, bản 2026 từ `2026-01-01`; dưới 3 năm là 12 ngày phép năm.
- Access control: `data/docs/access_control_sop.txt`, Level 4 cần IT Manager + CISO.

Cutoff HR được ghi trong `contracts/data_contract.yaml` là `hr_leave_min_effective_date: "2026-01-01"`. Khi có policy version mới, cần cập nhật contract trước rồi mới chỉnh cleaning rule.
