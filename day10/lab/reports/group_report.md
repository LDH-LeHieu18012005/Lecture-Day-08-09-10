# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** Cá nhân - Lê Dương Hiếu  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| Lê Dương Hiếu - 2A202600635 | Ingestion / Cleaning / Quality / Embed / Monitoring / Docs | 2A202600635 |

**Ngày nộp:** 2026-06-10  
**Repo:** `Lecture-Day-08-09-10/day10/lab`

---

## 1. Pipeline tổng quan

Tôi làm bài một mình nên tự phụ trách toàn bộ các vai trò của nhóm: ingestion, cleaning, quality, embed, monitoring và docs. Pipeline xử lý export bẩn `data/raw/policy_export_dirty.csv` gồm 247 dòng từ nhiều nguồn policy, SLA, FAQ, HR và access-control. Luồng chạy là ingest CSV, chuẩn hoá/clean dữ liệu, ghi quarantine có reason, chạy expectation suite, embed snapshot vào Chroma collection `day10_kb`, ghi manifest và chạy freshness. Run cuối là `final-clean`, log tại `artifacts/logs/run_final-clean.log`, manifest tại `artifacts/manifests/manifest_final-clean.json`. Kết quả cuối: `raw_records=247`, `cleaned_records=37`, `quarantine_records=210`, `embed_upsert count=37`, grading 10/10 pass.

**Lệnh chạy một dòng:**

```bash
python etl_pipeline.py run --run-id final-clean && python eval_retrieval.py --out artifacts/eval/after_fix_eval.csv && python grading_run.py --out artifacts/eval/grading_run.jsonl
```

---

## 2. Cleaning & expectation

Nhóm mở rộng pipeline theo hướng không bỏ lỗi âm thầm: nguồn không canonical, ngày thiếu, HR stale, text mơ hồ, timestamp không parse được đều đi vào quarantine. Baseline thiếu `access_control_sop`, nên nhóm thêm nguồn này vào allowlist/contract để trả lời được câu hỏi access-control. Ngoài ra, pipeline chuẩn hoá `exported_at` dạng slash date, quarantine nội dung HR 2025 dù effective_date mới, loại marker “Nội dung không rõ ràng”, sửa cụm “làm việc làm việc”, và thêm hybrid rerank cho eval/grading để top-1 ổn định trên tiếng Việt.

### 2a. Bảng metric_impact

| Rule / Expectation mới | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ |
|------------------------|-----------------|-----------------------------|----------|
| `access_control_sop` allowlist | 8 raw row access-control bị xem như nguồn ngoài contract | 6 chunk access-control vào cleaned; `gq_d10_09` và `gq_d10_10` pass top1 | `cleaned_final-clean.csv`, `grading_run.jsonl` |
| `exported_at` slash normalization | 16 raw row có slash timestamp | 0 cleaned row fail `exported_at_parseable_iso_datetime` | `expectation[exported_at_parseable_iso_datetime] OK` |
| `stale_hr_policy_content` | 27 raw HR row có marker HR 2025 hoặc 10 ngày phép năm | 8 row quarantine reason `stale_hr_policy_content`; HR eval no forbidden | `quarantine_final-clean.csv`, `after_fix_eval.csv` |
| `unclear_content_marker` | 14 raw row có marker mơ hồ | 7 row quarantine reason `unclear_content_marker`; expectation pass | `quarantine_final-clean.csv` |
| `refund_no_stale_14d_window` | Inject có `violations=2`, eval `q_refund_window` hits_forbidden=yes | Final clean `violations=0`, eval `q_refund_window` hits_forbidden=no | `run_inject-bad.log`, `after_inject_bad.csv`, `after_fix_eval.csv` |
| `required_canonical_doc_ids_present` | Baseline thiếu access-control trong allowlist | Final clean missing_doc_ids=[] | `run_final-clean.log` |

**Ví dụ expectation fail và xử lý:** `inject-bad` cố ý dùng `--no-refund-fix --skip-validate`, log ghi `refund_no_stale_14d_window FAIL (halt) :: violations=2`. Sau đó run lại `final-clean`, expectation pass và `embed_prune_removed=2` loại vector stale.

---

## 3. Before / after ảnh hưởng retrieval hoặc agent

Kịch bản inject là tắt rule sửa cửa sổ refund 14 ngày bằng lệnh `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`. Đây không phải đường production; mục tiêu là chứng minh expectation halt bắt đúng lỗi nhưng vẫn có artifact để đo tác động lên retrieval. File `artifacts/eval/after_inject_bad.csv` cho thấy `q_refund_window` vẫn tìm đúng `policy_refund_v4` và có “7 ngày”, nhưng `hits_forbidden=yes` vì top-k còn chứa “14 ngày làm việc”. Sau khi chạy `final-clean`, file `artifacts/eval/after_fix_eval.csv` có 21/21 câu pass; riêng `q_refund_window` chuyển từ `hits_forbidden=yes` sang `hits_forbidden=no`. File `artifacts/eval/grading_run.jsonl` có đủ 10 dòng `gq_d10_01` đến `gq_d10_10`, tất cả `contains_expected=true`, `hits_forbidden=false`, `top1_doc_matches=true` khi có yêu cầu top1.

---

## 4. Freshness & monitoring

Freshness được đo ở boundary publish bằng `latest_exported_at` trong manifest. Run `final-clean` ghi `latest_exported_at=2026-04-11T00:00:00`, trong khi chạy vào 2026-06-10 nên `age_hours=1446.887`, vượt SLA 24h và trả `FAIL`. Đây là kết quả đúng với dữ liệu mẫu: pipeline sạch và grading pass, nhưng source snapshot đã cũ. Runbook yêu cầu không debug model trước; cần báo source owner cập nhật export hoặc điều chỉnh SLA có chủ đích.

---

## 5. Liên hệ Day 09

Day 09 agent/multi-agent phụ thuộc vào việc retriever đọc đúng corpus. Day 10 cung cấp collection `day10_kb` đã có allowlist, versioning, expectation và manifest, nên có thể dùng làm nguồn knowledge base sạch cho agent Day 09. Nếu tách collection, vẫn có thể dùng cùng `cleaned_final-clean.csv` để rebuild vector store bên Day 09.

---

## 6. Rủi ro còn lại & việc chưa làm

- Cần export mới để freshness PASS thay vì chỉ ghi nhận FAIL hợp lý.
- Chưa dùng Great Expectations/pydantic thật; expectation hiện là custom Python.
- Chưa có owner thật theo tên người trong nhóm, vì repo không cung cấp danh sách thành viên.
- Cần bổ sung lexical index production nếu muốn hybrid retrieval có metric latency và recall rõ hơn.
