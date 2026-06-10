# Quality report — Lab Day 10 (nhóm)

**run_id:** `final-clean`  
**Ngày:** 2026-06-10  
**Collection:** `day10_kb`
**Người thực hiện:** Lê Dương Hiếu - 2A202600635

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước / inject-bad | Sau / final-clean | Ghi chú |
|--------|--------------------|-------------------|---------|
| raw_records | 247 | 247 | Cùng file raw |
| cleaned_records | 37 | 37 | Khác nội dung refund vì `--no-refund-fix` |
| quarantine_records | 210 | 210 | Quarantine rules giữ nguyên |
| Expectation halt? | Có, `refund_no_stale_14d_window` fail 2 | Không | Inject dùng `--skip-validate` để tạo evidence |
| Eval failed | 1 dòng (`q_refund_window`) | 0 dòng / 21 | Bad có `hits_forbidden=yes` |
| Grading failed | Không dùng để nộp | 0 dòng / 10 | `grading_run.jsonl` final pass |

---

## 2. Before / after retrieval

Artifact:

- Bad: `artifacts/eval/after_inject_bad.csv`
- Good: `artifacts/eval/after_fix_eval.csv`
- Grading: `artifacts/eval/grading_run.jsonl`

**Câu hỏi then chốt:** `q_refund_window`

| Run | top1_doc_id | contains_expected | hits_forbidden | top1_doc_expected | Preview |
|-----|-------------|-------------------|----------------|-------------------|---------|
| `inject-bad` | `policy_refund_v4` | yes | yes | yes | chứa “14 ngày làm việc” |
| `final-clean` | `policy_refund_v4` | yes | no | yes | chứa “7 ngày làm việc” |

**Merit evidence:** HR versioning và access control đều pass sau fix.

| Câu hỏi | Kết quả final |
|---------|---------------|
| `q_hr_annual_leave_under3` | top1 `hr_leave_policy`, contains `12 ngày`, no forbidden `10 ngày phép năm` |
| `q_access_level4` | top1 `access_control_sop`, contains `IT Manager` và `CISO` |

---

## 3. Freshness & monitor

Run `final-clean` ghi:

```text
freshness_check=FAIL {"latest_exported_at": "2026-04-11T00:00:00", "age_hours": 1446.887, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

Kết luận: pipeline xử lý và publish thành công, nhưng data snapshot mẫu đã stale so với SLA 24h. Đây là `FAIL` hợp lý để runbook yêu cầu source owner cập nhật export; không nên sửa prompt/model để che freshness issue.

---

## 4. Corruption inject (Sprint 3)

Lệnh inject:

```bash
python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate
python eval_retrieval.py --out artifacts/eval/after_inject_bad.csv
```

Kịch bản: tắt rule sửa refund window, để chunk `policy_refund_v4` chứa “14 ngày làm việc” vào vector store. Expectation phát hiện `violations=2`; vì đây là demo có chủ đích, `--skip-validate` cho embed để đo ảnh hưởng. Sau đó chạy lại `final-clean`; pipeline prune 2 vector stale và upsert 37 chunk sạch.

---

## 5. Hạn chế & việc chưa làm

- Freshness vẫn fail vì raw snapshot cũ; cần export mới để PASS.
- Chưa tích hợp Great Expectations thật; expectation hiện là custom Python.
- Hybrid rerank đủ cho lab và giúp eval tiếng Việt ổn định, nhưng production nên có lexical index/BM25 riêng, metric latency và canary query.
