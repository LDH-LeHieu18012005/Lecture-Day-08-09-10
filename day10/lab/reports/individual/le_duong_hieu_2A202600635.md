# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Lê Dương Hiếu  
**Mã số:** 2A202600635  
**Vai trò:** Cleaning / Quality / Embed / Monitoring  
**Ngày nộp:** 2026-06-10

---

## 1. Tôi phụ trách phần nào?

Trong lab Day 10, tôi phụ trách chính phần làm sạch dữ liệu, kiểm tra chất lượng và chứng minh pipeline sau khi sửa có ảnh hưởng thật đến retrieval. Các file liên quan trực tiếp gồm `transform/cleaning_rules.py`, `quality/expectations.py`, `eval_retrieval.py`, `grading_run.py`, `retrieval_utils.py`, `contracts/data_contract.yaml` và các artifact trong `artifacts/`. Tôi phân tích file raw `data/raw/policy_export_dirty.csv`, phát hiện baseline chưa xử lý đủ nguồn canonical, đặc biệt là `access_control_sop`. Sau khi sửa pipeline, run cuối `final-clean` tạo được `raw_records=247`, `cleaned_records=37`, `quarantine_records=210`, embed 37 chunk vào collection `day10_kb`.

## 2. Một quyết định kỹ thuật

Một quyết định kỹ thuật quan trọng của tôi là không cho pipeline publish nếu dữ liệu vi phạm các lỗi có thể làm agent trả lời sai chính sách. Vì vậy, các expectation như `refund_no_stale_14d_window`, `hr_leave_no_stale_10d_annual`, `required_canonical_doc_ids_present`, `exported_at_parseable_iso_datetime` và `no_unclear_content_marker` được đặt ở mức `halt`. Ngược lại, `canonical_doc_min_two_chunks` chỉ là `warn`, vì số chunk thấp là tín hiệu cần kiểm tra nhưng chưa chắc là lỗi tuyệt đối. Tôi cũng bổ sung hybrid rerank trong eval/grading để giảm lỗi top-1 khi embedding tiếng Việt gặp các chunk ngắn, nhưng vẫn giữ Chroma làm bước truy xuất chính.

## 3. Một lỗi hoặc anomaly đã xử lý

Anomaly rõ nhất tôi xử lý là dữ liệu HR stale theo nội dung. Ban đầu pipeline đã loại các dòng `hr_leave_policy` có `effective_date` trước `2026-01-01`, nhưng run đầu vẫn halt vì còn 2 chunk chứa nội dung “10 ngày phép năm (bản HR 2025)” dù ngày hiệu lực nhìn như mới. Tôi thêm rule `stale_hr_policy_content` để quarantine các chunk HR có marker “bản HR 2025” hoặc “10 ngày phép năm”. Sau khi sửa, log `final-clean` ghi `expectation[hr_leave_no_stale_10d_annual] OK (halt) :: violations=0`. Eval `q_hr_annual_leave_under3` cũng trả đúng `12 ngày phép năm`, `hits_forbidden=no`, top-1 là `hr_leave_policy`.

## 4. Bằng chứng trước / sau

Tôi tạo bằng chứng before/after bằng run inject. Run xấu dùng lệnh `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`, log ghi `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=2`. File `artifacts/eval/after_inject_bad.csv` cho thấy câu `q_refund_window` có `contains_expected=yes` nhưng `hits_forbidden=yes`, nghĩa là context vẫn còn chunk “14 ngày làm việc”. Sau khi chạy lại `python etl_pipeline.py run --run-id final-clean`, log ghi `embed_prune_removed=2`, `embed_upsert count=37`, và file `artifacts/eval/after_fix_eval.csv` có 21/21 câu pass. File `artifacts/eval/grading_run.jsonl` có 10/10 câu pass.

## 5. Cải tiến tiếp theo

Nếu có thêm thời gian, tôi sẽ chuyển expectation custom sang Great Expectations hoặc pydantic để schema/quality check dễ tái sử dụng hơn. Tôi cũng muốn tự động sinh bảng `metric_impact` từ log và quarantine CSV để báo cáo không phải nhập tay, giảm rủi ro số liệu report lệch artifact.
