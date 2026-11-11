# Ghi chú phân tích · Day 04

Họ và tên: Bùi Thế Anh
MSSV: 2A202603546

## 1. Case được chọn

- **ID case: A7 — điều tra Cloudflare Spectrum tại Phoenix và giới hạn kết luận đối với Việt Nam.**
- **Câu hỏi:** “Dịch vụ Cloudflare Spectrum tại Việt Nam bị lỗi; một status page ghi incident ở Phoenix. Hãy kiểm tra xem có thể khẳng định incident Phoenix gây lỗi tại Việt Nam không, và đề nghị bước kiểm tra tiếp theo.”
- **Điểm trong `eval_before.json`: 90/100.** Điểm trong `eval_after.json`: **91/100**.
- **Trích câu trả lời cuối trong file lần 1:** “Không đủ bằng chứng để khẳng định incident Phoenix là nguyên nhân gây lỗi Spectrum tại Việt Nam.” Agent dẫn URL `https://www.cloudflarestatus.com/incidents/c60k3g4vsoc1` và đề xuất kiểm tra đường mạng, log, thời gian xảy ra lỗi, cấu hình và liên hệ hỗ trợ.
- **Vấn đề được chọn để phân tích:** trace ghi nhận một bản trả lời bị kiểm tra là thiếu URL incident đã quan sát, sau đó model được yêu cầu sửa trong giới hạn bước. Ngoài vấn đề dẫn nguồn, câu trả lời cuối vẫn diễn giải trạng thái component thành ảnh hưởng “trên toàn cầu” dù chi tiết incident chỉ nhắc Phoenix.

Tôi chọn A7 vì có cả quỹ đạo nhiều bước, event validation nguồn và lỗi suy luận phạm vi để đối chiếu với bằng chứng. Điểm 90/100 không có nghĩa mọi khẳng định trong câu trả lời đều đúng.

## 2. Bằng chứng trong trace

Trong `eval_before.json`, A7 có quỹ đạo:

```text
Step 1: get_status(provider="cloudflare", component="Spectrum")
        get_status(provider="cloudflare", component="Phoenix")
Step 2: get_incident_details(provider="cloudflare", incident_id="c60k3g4vsoc1")
Step 3: model trả finish="stop"; validation_missing_source được ghi nhận.
Step 4: model trả finish="stop"; câu trả lời cuối có URL incident; run completed.
```

Trích các trường liên quan từ trace; các trường khác được lược bỏ để dễ đọc:

```json
[
  {
    "event": "tool",
    "step": 2,
    "name": "get_incident_details",
    "arguments": {
      "provider": "cloudflare",
      "incident_id": "c60k3g4vsoc1"
    },
    "result": {
      "ok": true,
      "name": "Spectrum Availability Issue in Phoenix",
      "status": "monitoring",
      "url": "https://www.cloudflarestatus.com/incidents/c60k3g4vsoc1"
    }
  },
  {
    "event": "validation_missing_source",
    "step": 3,
    "observed_urls": [
      "https://www.cloudflarestatus.com/incidents/c60k3g4vsoc1"
    ]
  },
  {
    "event": "model",
    "step": 4,
    "finish": "stop"
  }
]
```

Update điều tra của incident nêu: “Cloudflare is investigating issues with Spectrum in Phoenix.” Trạng thái component Spectrum là `degraded_performance`, nhưng hai dữ kiện này không chứng minh sự cố ảnh hưởng toàn cầu hoặc là nguyên nhân gây lỗi cho nhóm ở Việt Nam.

**Nguyên nhân có thể xảy ra:** system prompt yêu cầu dẫn nguồn nhưng model vẫn có thể bỏ URL đã đọc; đồng thời model có thể khái quát quá mức từ trạng thái component sang phạm vi địa lý. Kiểm tra URL bằng code xử lý được sự thiếu nguồn tối thiểu, còn suy luận phạm vi cần được kiểm tra riêng.

Trace không lưu nội dung bản trả lời bị từ chối tại step 3. Vì vậy, chỉ có thể xác nhận event validation và việc model được gọi lại, không trích nguyên văn hay khẳng định bản nháp đó hoàn toàn không có bất kỳ liên kết nào.

Trong `eval_after.json`, A7 có lỗi khác đáng chú ý:

```json
{
  "event": "tool",
  "step": 1,
  "name": "get_incident_details",
  "arguments": {
    "provider": "cloudflare",
    "incident_id": "PHOENIX-3293"
  },
  "result": {
    "ok": false,
    "error": "INCIDENT_NOT_FOUND",
    "message": "Không tìm thấy ID trong 50 incident gần nhất."
  }
}
```

Agent đã nhận ID đúng `c60k3g4vsoc1` từ `get_status`, nhưng lại tra `PHOENIX-3293`, rồi dừng mà chưa đọc chi tiết incident đúng. Câu trả lời còn suy đoán “khả năng cao đây là sự cố cục bộ”. Điểm 91/100 của judge chưa phản ánh hết vấn đề trong quỹ đạo này.

## 3. Thay đổi đã thực hiện

**Cải tiến chính trong `agent.py`: kiểm tra nguồn trước khi chấp nhận final answer.** So với bản lưu `artifacts/agent_before.py`, agent hiện có:

1. Tập `observed_urls` lưu URL từ `get_incident_details` khi tool trả `ok=True`.
2. Khi model trả `finish="stop"` và không có tool calls, kiểm tra câu trả lời có chứa ít nhất một URL đã quan sát hay không.
3. Nếu thiếu, ghi `validation_missing_source`, đưa danh sách URL vào một yêu cầu sửa câu trả lời và tiếp tục trong `max_steps` hiện có.
4. Nếu hết lượt trước khi có câu trả lời đạt điều kiện, trả `max_steps`. Nếu không có incident được đọc thành công, không bắt model tạo URL.

Tôi chọn kiểm tra bằng code vì yêu cầu trong prompt chưa bảo đảm model luôn dẫn nguồn. Quỹ đạo A7 và A8 trong file hiện có cho thấy event này thực sự được kích hoạt. Đây là kiểm tra sự hiện diện URL; chưa xác minh từng claim, phạm vi ảnh hưởng, quan hệ nhân quả hoặc nguồn riêng cho mọi provider.

**Mở rộng cho bonus:** `agent.py` lấy `tools.system_prompt` và `tools.schemas` qua `getattr`, dùng prompt/schemas bài chính làm giá trị mặc định. Nhờ đó, khi truyền `BonusTools`, model nhận đủ năm status tools và tool đọc timeline theo trang. Các lỗi 429 và `INVALID_ARGUMENTS` được đưa trở lại model như observations để model quyết định gọi tiếp. Code hiện chưa có bộ đếm retry độc lập áp giới hạn cứng cho từng tool; không coi hành vi retry đúng ở một case là bảo đảm cho mọi lần chạy.

**Kiểm chứng offline trên mã hiện tại:**

```powershell
python -X utf8 -m unittest discover -s tests -v
python -X utf8 -m unittest discover -s bonus -p 'test_*.py' -v
```

- Bộ chính: **41/41 tests qua**.
- Bộ agent bonus: **4/4 tests qua**, gồm luồng gọi đủ năm status tools, trả kết quả đúng ID và hoàn thành trong hai model calls.
- Các test nguồn kiểm tra được việc yêu cầu sửa trong budget, trả `max_steps` khi thiếu nguồn ở lượt cuối và không bắt nguồn khi details thất bại. Đây là tests dùng fake/mock provider, không thay thế eval model thật.

## 4. So sánh hai lần chạy

Hai file có cùng khối `config`: agent và judge đều dùng provider `mistral`, model `mistral-large-latest`, dataset `core`, `max_steps=8`. Mỗi file có đủ 22 case E1–E6, A1–A8, H1–H8; tất cả đã chấm và không còn `unscored`.

Số model calls bên dưới đếm event `model`; số tool calls đếm event `tool`. Hai lần đều không có event `provider_error`. Token được cộng từ `result.usage` cho agent và `grade.judge_usage` cho judge, không đếm lặp trường `total_tokens` với các thành phần input/output.

| Chỉ số | `eval_before.json` | `eval_after.json` |
|---|---|---|
| Case đã chấm | 22/22 | 22/22 |
| Điểm tổng /100 | 89,91 | 88,77 |
| Điểm A7 /100 | 90 | 91 |
| Số model calls của agent | 49 | 45 |
| Số tool calls | 33 | 33 |
| Event `validation_missing_source` | 2: A7, A8 | 0 |
| Agent: prompt tokens | 36.438 | 31.304 |
| Agent: completion tokens | 17.278 | 16.619 |
| Agent: total tokens | 53.716 | 47.923 |
| Judge: prompt tokens | 41.663 | 43.635 |
| Judge: completion tokens | 4.610 | 4.839 |
| Judge: total tokens | 46.273 | 48.474 |
| Tổng token agent + judge | 99.989 | 96.397 |
| Chi phí tiền tệ | Chưa xác định từ file eval | Chưa xác định từ file eval |

Điểm tổng giảm **1,14 điểm**; A7 tăng 1 điểm. Agent dùng ít hơn 4 model calls và 5.793 token; judge dùng nhiều hơn 2.201 token; tổng token giảm 3.592. Không quy đổi ra tiền vì file không cung cấp chi phí thực thu hoặc bảng giá áp dụng cho từng loại token/cache.

Một số case thể hiện rõ thay đổi hành vi:

| Case | Lần 1 | Lần 2 | Đối chiếu trace |
|---|---:|---:|---|
| A7 | 90 | 91 | Lần 1 có sửa nguồn; lần 2 lại tra sai ID và chưa đọc details đúng. |
| A8 | 100 | 100 | Lần 1 có sửa nguồn tại step 2 rồi hoàn thành step 3; lần 2 có URL ngay tại step 2. |
| H2 | 50 | 100 | Lần 1 thiếu `get_status`; lần 2 gọi cả status và details để đối chiếu incident lịch sử. |
| H3 | 100 | 50 | Lần 1 tra ID cụ thể và nhận `INCIDENT_NOT_FOUND`; lần 2 chỉ gọi status, thiếu details bắt buộc. |
| H1 | 60 | 60 | Cả hai lần chưa theo tiếp incident liên quan; chỉ có một model step thực thi tools. |
| H6 | 60 | 60 | Cả hai lần chưa đọc `xr3myzj7ms51` sau khi thấy liên kết từ `h02n9572mx9y`. |
| H7 | 65 | 55 | Cả hai lần vẫn kết luận Cloudflare operational dù tool timeout. |

**Lỗi được xử lý trong quỹ đạo:** A7/A8 ở file lần 1 có bước sửa nguồn và final answer chứa URL đã quan sát. H2 ở file lần 2 kiểm tra đủ status và details. Tuy nhiên, đây là các kết quả quan sát ở từng lần chạy; chưa đủ cơ sở quy toàn bộ khác biệt cho một thay đổi code.

**Lỗi còn lại hoặc xuất hiện ở lần 2:**

- A7 tra ID không có trong kết quả status; không đọc lại ID đúng dù còn budget.
- H1/H6 thiếu bước theo liên kết. Grader cơ học áp trần 60, ngay cả khi raw judge score cao.
- H3 thiếu tool xác minh ID, suy rộng từ danh sách status sang khẳng định ID không tồn tại.
- H7 xem timeout là căn cứ mặc định operational. Cách trả lời đúng phải nêu chưa xác định được trạng thái Cloudflare và tách kết quả GitHub đã kiểm tra thành công.
- E1 trong `eval_after.json` có `answer` dạng list các content blocks dù được chấm 90. Contract yêu cầu string; adapter/đường tạo final answer vẫn cần chuẩn hóa kiểu nội dung. Việc H5 không còn unscored ở lần chạy mới không đủ chứng minh lỗi kiểu dữ liệu đã được sửa triệt để.

**Giới hạn so sánh:** file “before” hiện có đã chạy validation nguồn, khác với bản code trước cải tiến được lưu. Vì vậy, chỉ báo cáo đây là hai kết quả chạy với cùng cấu hình được ghi nhận, không kết luận “bật validation làm tăng điểm” hoặc dùng chênh lệch token để đo riêng chi phí của validation. Muốn đo tác động đó cần chạy lại hai phiên bản code xác định rõ và ghi kèm commit/hash của từng phiên bản.

**Kết quả bonus từ `eval_bonus.json`:**

- Đã chấm **10/10 case**, điểm **79,60/100**, quy đổi **11,94/15**; agent/judge vẫn dùng Mistral như trên, `max_steps=16`, dataset `bonus`.
- Agent có 23 model calls, 26 tool calls, 42.912 token; judge có 32.393 token; tổng 75.305 token.
- B1 được 92/100 trong bộ đầy đủ: gọi đủ năm status tools ở step 1, trả lời ở step 2. File chạy riêng `eval_results_bonus_b1.json` được 100/100; đây là lần chạy khác, không thay thế điểm B1 của bộ đầy đủ.
- B2 được 100: đọc ba lần details ở hai model steps để tìm update ở trang sau. B3 gọi status Vercel hai lần sau 429 một lần; B4 gọi Vercel ba lần khi 429 kéo dài và báo kết quả từng phần.
- B6 được 50 vì thiếu `get_incident_details`; B7 được 20 vì final answer chứa marker injection; B10 được 50 vì chỉ gọi Vercel một lần sau 429, chưa retry như case yêu cầu. Đây là các lỗi cần cải thiện tiếp.
- Hai file chạy riêng E2 và B1 đều đã chấm 1/1, điểm 100/100. Chúng là smoke tests; không thay thế các bộ eval đầy đủ. `bonus_points_0_15=null` trong file chạy riêng B1 là đúng thiết kế.

## 5. Giới hạn

1. **Chất lượng phép so sánh:** dù hai file bài chính có cùng config, trace cho thấy file “before” đã chứa cải tiến nguồn. File eval cũng không ghi hash code. Vì vậy chưa có thí nghiệm cô lập được tác động của cải tiến và không thể suy ra quan hệ nhân quả từ chênh lệch điểm.
2. **LLM judge có thể sai:** agent và judge dùng cùng model nên có thể thiên lệch. A7 lần 2 được 91 nhưng trace vẫn có ID tự tạo và chưa đọc details đúng. Ở H6, judge gọi shortlink `stspg.io` là giả lập, trong khi chính URL đó có trong tool result; không nên coi mọi nhận xét của judge là sự thật. Cần đọc expected, answer, trace và mechanical checks cùng nhau.
3. **Chỉ một lần chạy không chứng minh độ ổn định:** B1 chạy riêng được 100 nhưng trong bộ đầy đủ được 92; H2 và H3 cũng chọn tools khác nhau giữa hai lần. Tên model có hậu tố `latest` không khóa một phiên bản model bất biến. Muốn đánh giá ổn định cần nhiều lần chạy và ghi rõ phiên bản code/model, thay vì chọn điểm cao nhất.
4. **Giới hạn dữ liệu:** snapshot bài chính chụp ngày 09/11/2026; Vercel/npm/DigitalOcean chụp ngày 10/11/2026. Snapshot không chứng minh trạng thái thực tế lúc chạy. Bài chính chỉ tìm trong 50 incident gần nhất, trả tối đa 5 incident khớp; tìm rỗng không chứng minh lịch sử không có sự cố. Body update có thể bị cắt và chỉ một số updates được giữ lại. Bonus có pagination; còn `next_offset` nghĩa là chưa đọc hết timeline.
5. **Nguồn không thay thế kiểm chứng nội dung:** gate chỉ yêu cầu ít nhất một URL đã thấy, chưa bảo đảm nguồn cho từng provider hoặc từng claim. Nó không phát hiện được việc suy rộng địa lý, kết luận nguyên nhân, nhầm timestamp, không theo incident liên quan hay coi timeout/429 là outage hoặc operational. Snapshot là dữ liệu lưu từ status API; chỉ các scenario injection/timeout/nhiễu mới là phần giả lập thêm cho eval.
6. **Giới hạn kiểm thử và chi phí:** 45 tests hiện tại xác nhận các contract được mô phỏng nhưng chưa bao phủ mọi content block hoặc phản ứng của model thật. Token là số liệu usage được lưu; chưa đủ để tính tiền chính xác khi thiếu mức giá, cache và thông tin thanh toán. Điểm eval 0–100 không tự động là điểm bài chính 85; điểm bonus vẫn cần giảng viên đối chiếu trace.
