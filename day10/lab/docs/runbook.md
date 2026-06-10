# Runbook — Lab Day 10 (incident tối giản)

---

## Symptom

User hỏi chính sách hoàn tiền và agent trả lời “14 ngày làm việc” thay vì “7 ngày làm việc”. Một biến thể khác là agent không trả lời được câu về `access_control_sop` vì nguồn canonical bị quarantine nhầm.

---

## Detection

- `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=2` trong `run_inject-bad.log`.
- Eval `artifacts/eval/after_inject_bad.csv`: `q_refund_window` có `hits_forbidden=yes`.
- Grading final `artifacts/eval/grading_run.jsonl`: tất cả 10 câu pass sau khi restore `final-clean`.
- Freshness final: `FAIL` vì `latest_exported_at=2026-04-11T00:00:00`, vượt `FRESHNESS_SLA_HOURS=24` tại ngày chạy `2026-06-10`.

---

## Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Mở `artifacts/logs/run_inject-bad.log` | Thấy expectation refund fail nhưng `--skip-validate` vẫn embed để demo |
| 2 | Mở `artifacts/eval/after_inject_bad.csv` | `q_refund_window` có `hits_forbidden=yes` |
| 3 | Mở `artifacts/quarantine/quarantine_final-clean.csv` | Có reason như `stale_hr_policy_content`, `unknown_doc_id`, `duplicate_chunk_text` |
| 4 | Chạy `python eval_retrieval.py --out artifacts/eval/after_fix_eval.csv` | 21 câu tự kiểm không còn failed |
| 5 | Chạy `python grading_run.py --out artifacts/eval/grading_run.jsonl` | 10 dòng `gq_d10_01` đến `gq_d10_10` đều pass |

---

## Mitigation

1. Dừng publish nếu expectation halt fail và không dùng `--skip-validate` trong run production.
2. Rerun pipeline chuẩn:

```bash
python etl_pipeline.py run --run-id final-clean
```

3. Xác nhận log có `PIPELINE_OK`, `embed_prune_removed=2` nếu vừa restore sau inject, và `embed_upsert count=37 collection=day10_kb`.
4. Chạy lại eval/grading:

```bash
python eval_retrieval.py --out artifacts/eval/after_fix_eval.csv
python grading_run.py --out artifacts/eval/grading_run.jsonl
```

5. Nếu freshness vẫn `FAIL`, thông báo data snapshot đang stale và yêu cầu source owner cập nhật export; không coi đây là model/prompt bug.

---

## Prevention

- Giữ `refund_no_stale_14d_window` ở severity `halt`.
- Giữ `required_canonical_doc_ids_present` để phát hiện thiếu `access_control_sop` hoặc nguồn canonical mới.
- Chuẩn hoá `exported_at` trước freshness; timestamp không parse được phải quarantine.
- Dùng hybrid rerank trong eval/grading để giảm top-1 lệch do embedding tiếng Việt trên chunk ngắn.
- Bắt buộc bảng `metric_impact` trong group report để rule mới có bằng chứng số liệu.
