# Hướng dẫn hoàn thiện lab trên Windows PowerShell

Tài liệu này dựa trên việc đọc README.md, GUIDE.md, RUBRIC.md, toàn bộ mã Python, các case eval, tests, cấu trúc và nội dung liên quan của 5 snapshot JSON, cùng hai sơ đồ SVG trong dự án. GUIDE.md và RUBRIC.md vẫn là yêu cầu gốc để đối chiếu.

Bạn sẽ lần lượt tự hoàn thiện `agent.py`, tạo kết quả eval trước/sau, rồi viết báo cáo. Các đoạn code dưới đây là hướng dẫn tham khảo; mã bài tập trong `agent.py` chưa được thay đổi.

## 1. Hiểu sản phẩm cần làm và sản phẩm phải nộp

Bạn xây **Status Investigation Agent bằng Python**, không cần làm giao diện hay cài React. Agent cần:

1. Nhận câu hỏi.
2. Gọi LLM để lấy câu trả lời hoặc yêu cầu gọi tool.
3. Python thực thi mọi tool call trong lượt đó.
4. Đưa kết quả tool vào lịch sử hội thoại, gắn đúng ID.
5. Gọi LLM tiếp đến khi hoàn tất, lỗi hoặc hết lượt.
6. Lưu trace và usage để kiểm chứng và phân tích.

Luồng dữ liệu điển hình:

```text
system + user
  → model lần 1: yêu cầu get_status
  → assistant message nguyên vẹn + tool result
  → model lần 2: yêu cầu get_incident_details
  → assistant message nguyên vẹn + tool result
  → model lần 3: câu trả lời cuối
```

Một lượt có thể chứa nhiều tool call. `max_steps` đếm lần gọi model, không đếm từng tool.

Sản phẩm bài chính:

| Sản phẩm | Nội dung |
|---|---|
| `agent.py` | Agent loop, kiểm soát lỗi, trace, usage và validation nguồn. |
| `eval_before.json` | Toàn bộ 22 case của phiên bản ban đầu đã chạy được. |
| `eval_after.json` | Cùng 22 case sau khi cải tiến, giữ nguyên cấu hình. |
| Ghi chú/báo cáo | Case chọn, evidence, nguyên nhân, thay đổi, so sánh và giới hạn. |
| Demo | Một trace nhiều bước và một lỗi cụ thể của agent. |

Bài chính tối đa 85 điểm: loop 30, robustness/trace 15, eval/phân tích 20, cải tiến/trình bày 20. Bonus tùy chọn tối đa 15 điểm. Điểm eval 0–100 là thang khác, không tự động thành điểm lab.

## 2. Bản đồ toàn bộ thư mục

| File/thư mục | Vai trò và cách dùng |
|---|---|
| `README.md` | Tổng quan, cấu hình provider và lệnh chạy. |
| `GUIDE.md` | Các bài 1–5, yêu cầu nộp bài và bonus. |
| `RUBRIC.md` | Tiêu chí và cách tính điểm. |
| `agent.py` | Phần bạn phải viết; hiện `run_agent` chỉ ném `NotImplementedError`. |
| `providers.py` | Adapter cho OpenAI, Gemini, Anthropic, OpenRouter và Mistral. |
| `status_tools.py` | Hai tools bài chính và JSON schemas; đã có sẵn. |
| `run.py` | CLI chạy một câu hỏi; chọn snapshot/live và core/bonus. |
| `fixtures/github.json` | Snapshot GitHub, 50 incident và 12 component. |
| `fixtures/cloudflare.json` | Snapshot Cloudflare, 50 incident và 481 component. |
| `evals/cases.json` | 22 case E1–E6, A1–A8, H1–H8. |
| `evals/scenarios.py` | Timeout, injection và dữ liệu nhiễu giả lập cho bài chính. |
| `evals/run_evals.py` | Chạy agent, gọi judge và ghi báo cáo JSON. |
| `evals/grading.py` | Chấm bằng judge, áp trần bằng kiểm tra code và tổng hợp điểm. |
| `tests/test_lab.py` | Contract của loop, tools và adapters. |
| `tests/test_validation.py` | Scenario và điều kiện kiểm tra URL nguồn. |
| `tests/test_grading.py` | Cơ chế chấm và cách ly expected khỏi agent. |
| `tests/test_mistral.py` | 4 test bổ sung cho adapter Mistral, tool-call round trip và CLI agent/judge. |
| `tests/test_bonus.py` | Hạ tầng tools/runner bonus; nằm trong lệnh test bài chính. |
| `bonus/tools.py` | 5 status tools, tool đọc timeline theo trang, lỗi giả lập. |
| `bonus/test_agent.py` | 3 test riêng cho agent khi dùng bonus; phải chạy riêng. |
| `bonus/cases.json` | 10 case B1–B10. |
| `bonus/fixtures/` | Snapshot Vercel, npm, DigitalOcean; mỗi file 50 incident. |
| `bonus/__init__.py` | Đánh dấu Python package, file trống. |
| `assets/agent-architecture.svg` | Sơ đồ kiến trúc agent. |
| `assets/lab-workflow.svg` | Sơ đồ xây → eval → phân tích → cải tiến. |
| `.env.example` | Mẫu lệnh Bash, chương trình không tự nạp file `.env`. |
| `.gitignore` | Bỏ qua `.env`, cache Python, venv và `eval_results*.json`. |
| `.git/` | Metadata Git, không phải phần triển khai lab. |

Chỉ cần sửa `agent.py` cho bài chính. Không sửa fixtures, expected/cases, scenarios, grading hoặc rubric để làm kết quả đẹp hơn. Không cần viết lại adapter/tools hoặc cài framework.

## 3. Chuẩn bị terminal đúng với máy hiện tại

Mở terminal PowerShell tại thư mục dự án. Máy đã có `python` phiên bản 3.13.9, đáp ứng yêu cầu Python 3.10+. Lệnh `py` trên máy hiện báo không tìm thấy Python, nên dùng `python`.

```powershell
python --version
$env:PYTHONUTF8 = '1'
python -c "import sys; print(sys.flags.utf8_mode)"
```

Dòng cuối phải in `1`. Đặt lại biến này khi mở terminal mới. Hướng dẫn cũng dùng `-X utf8` trong các lệnh Python để từng lệnh vẫn đọc được UTF-8.

Lý do: một số chỗ trong repo gọi `Path.read_text()`/`write_text()` mà không chỉ định encoding. Trên môi trường này, chạy mặc định có thể dùng CP1252 và gây `UnicodeDecodeError`, kể cả khi đọc fixture hoặc dataset. `PYTHONIOENCODING` riêng lẻ không giải quyết toàn bộ việc đọc file.

Không cần `pip install`: dự án chỉ dùng standard library. Không bắt buộc tạo venv.

Chạy kiểm tra ban đầu, chưa cần API key:

```powershell
python -X utf8 -m unittest discover -s tests -v
```

Kết quả đã kiểm tra trên bản gốc: **37 tests, 28 qua và 9 lỗi** do `run_agent` chưa implement. Sau khi bổ sung Mistral, bộ test có 41 tests. Nếu không bật UTF-8, đã ghi nhận 13 lỗi trên bộ test gốc, gồm lỗi môi trường. Không coi toàn bộ những lỗi này là lỗi logic agent.

## 4. Khám phá tools và đọc bằng chứng — khoảng 15 phút

Chạy trực tiếp tools bằng here-string PowerShell để tránh lỗi quote của JSON:

```powershell
@'
import json
from status_tools import StatusTools

tools = StatusTools("snapshot")
print(json.dumps(tools.get_status("github", "Actions"), ensure_ascii=False, indent=2))
print(json.dumps(tools.get_incident_details("cloudflare", "wp49bp8bqo6c"), ensure_ascii=False, indent=2))
'@ | python -X utf8 -
```

Đọc các trường `captured_at`, `overall`, `components`, `incidents`, `status`, `updates`, `url`. Ghi nhận:

- Snapshot bài chính chụp ngày **09/11/2026**, ba snapshot bổ sung chụp ngày **10/11/2026**. Đây không phải bằng chứng trạng thái thực tế tại lúc bạn chạy.
- GitHub có overall `none`; một incident Actions cũ `resolved` không chứng minh Actions đang outage.
- Cloudflare cache purge incident `wp49bp8bqo6c` có trạng thái `identified` trong snapshot. Update đầu nói non-FedRAMP không bị ảnh hưởng bởi incident đó. Không vì vậy kết luận website CLB không thể có lỗi cache do nguyên nhân khác.
- Spectrum incident `c60k3g4vsoc1` nói về Phoenix và đang `monitoring` trong snapshot; chưa đủ căn cứ quy lỗi của nhóm ở Việt Nam cho incident này.

Contract tools bài chính:

| Tool | Tham số | Giới hạn |
|---|---|---|
| `get_status` | `provider`, `component` tùy chọn | Tìm chuỗi trong 50 incident gần nhất, trả tối đa 5 incident khớp và 5 component khớp. |
| `get_incident_details` | `provider`, `incident_id` | Chỉ tìm ID trong dữ liệu 50 incident; giữ tối đa hai update mới nhất và update đầu tiên, mỗi body tối đa 900 ký tự. |
| `execute` | `name`, `args` | Registry thực thi, lỗi dự kiến trả dict để model quan sát. |

Các bẫy quan trọng:

- `component` là tìm chuỗi, không phải semantic search. Nên thử từ tiếng Anh như `Actions`, `Cache Purge`, `Spectrum`.
- `components=[]` khi không truyền từ khóa không có nghĩa provider không có component.
- `get_status` thành công không nhất thiết có trường `ok`; thường nhận diện bằng `overall` và `provider`. Đừng dùng `if not result.get('ok')` cho mọi loại kết quả.
- Kết quả tìm rỗng không chứng minh không có incident trong lịch sử.
- `updates_total` lớn hơn số update trả về hoặc `truncated=true` nghĩa là bằng chứng chưa đầy đủ.
- URL có thể là shortlink `https://stspg.io/...`; hãy giữ URL tool thực sự trả về.

## 5. Bài 1 và 2: viết phiên bản ban đầu — khoảng 80 phút

Đầu tiên hoàn thiện loop và xử lý lỗi; chưa thêm validation nguồn của Bài 4. Nhờ vậy `eval_before.json` phản ánh phiên bản trước cải tiến.

Trong `agent.py`, thêm hai import sau ở đầu file, giữ nguyên `SYSTEM_PROMPT` có sẵn:

```python
import json
from status_tools import SCHEMAS
```

Thay riêng hàm `run_agent` bằng phiên bản tham khảo này. Hãy đọc giải thích phía sau trước khi chạy:

```python
def run_agent(question, provider, tools, max_steps=6):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    schemas = SCHEMAS
    trace, usage = [], []
    answer = ""

    def outcome(status, error=None):
        result = {
            "status": status,
            "answer": answer,
            "trace": trace,
            "usage": usage,
        }
        if error is not None:
            result["error"] = error
        return result

    if type(max_steps) is not int or max_steps < 1:
        return outcome("error", "max_steps must be a positive integer")

    for step in range(1, max_steps + 1):
        try:
            response = provider.complete(messages, schemas)
        except Exception as exc:
            # Không ghi key, headers hoặc toàn bộ payload của provider vào trace.
            error = type(exc).__name__
            trace.append({"event": "provider_error", "step": step, "error": error})
            return outcome("error", error)

        usage.append(response.get("usage", {}))
        message = response["message"]
        calls = response.get("calls", [])
        finish = response.get("finish")
        messages.append(message)  # Giữ nguyên assistant message, gồm tool_calls.
        trace.append({"event": "model", "step": step, "finish": finish})

        if finish not in ("stop", "tool_calls"):
            error = f"Unexpected finish reason: {finish}"
            trace.append({"event": "model_error", "step": step, "error": error})
            return outcome("error", error)

        if calls:
            for call in calls:
                arguments = call["arguments"]
                args = None
                try:
                    args = json.loads(arguments)
                    if not isinstance(args, dict):
                        raise ValueError("Arguments must be a JSON object")
                except (ValueError, TypeError):
                    observation = {
                        "ok": False,
                        "error": "INVALID_ARGUMENTS",
                        "message": "Arguments must be a valid JSON object.",
                    }
                else:
                    try:
                        observation = tools.execute(call["name"], args)
                    except Exception as exc:
                        # Hàng rào cho exception thoát ra ngoài registry.
                        observation = {"ok": False, "error": type(exc).__name__}

                trace.append({
                    "event": "tool",
                    "step": step,
                    "id": call["id"],
                    "name": call["name"],
                    "arguments": args if args is not None else arguments,
                    "result": observation,
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(observation, ensure_ascii=False),
                })
            continue

        if finish == "stop":
            answer = message.get("content") or ""
            return outcome("completed")

        # finish=tool_calls mà không có call: response không hoàn tất hợp lệ.
        return outcome("error", "No calls with finish=tool_calls")

    return outcome("max_steps")
```

Hiểu từng phần của code:

1. `messages` là bộ nhớ hội thoại của một run; không khởi tạo lại trong vòng lặp.
2. `provider.complete(messages, schemas)` chỉ gọi model, không tự thực thi tools.
3. Append assistant message nguyên vẹn trước mọi tool result để giữ giao thức tool calling.
4. Parse `arguments` bằng `json.loads`, rồi kiểm tra là object, vì JSON hợp lệ cũng có thể là list/null/string.
5. Invalid JSON trả `INVALID_ARGUMENTS` vào tool result; model có cơ hội sửa trong lượt tiếp.
6. `tools.execute` trả cả kết quả và lỗi dưới dạng observation. Tool timeout không phải bằng chứng dịch vụ outage.
7. Mỗi call có đúng một tool message với `tool_call_id` tương ứng. Xử lý hết calls trước lượt model kế tiếp.
8. Chỉ trả `completed` khi `finish='stop'` và không còn calls. `length`, content filter hoặc lý do lạ là `error`.
9. Hết vòng `for` trả `max_steps`; không thêm một model call “chốt câu” ngoài budget.
10. `trace` phục vụ debug và chấm cơ học, không yêu cầu model in chain-of-thought. `usage` lưu riêng từng lần gọi model thành công.

Các event tool phải dùng đúng `event='tool'`, `name` và `step`: grader đọc những trường này để đếm tools và số model steps có tool.

Chạy test vòng lặp trước:

```powershell
python -X utf8 -m unittest discover -s tests -p 'test_lab.py' -v
python -X utf8 -m unittest discover -s tests -v
```

Với đoạn tham khảo, `test_lab.py` phải qua. Bộ đầy đủ lúc này còn **2 test validation không qua** vì cố ý chưa thêm cải tiến nguồn. Đây là checkpoint trung gian; bản nộp cuối phải qua toàn bộ tests. Không sửa tests để bỏ hai yêu cầu này.

Lưu lại phiên bản trước cải tiến, có thể dùng thư mục riêng:

```powershell
New-Item -ItemType Directory -Path artifacts -Force | Out-Null
Copy-Item -LiteralPath agent.py -Destination artifacts/agent_before.py
```

## 6. Cấu hình một LLM provider và chạy thử

Snapshot không cần gọi status API thật nhưng **vẫn cần LLM API key**. Unit tests dùng fake provider nên không cần key. Eval còn gọi LLM judge, có thể phát sinh chi phí.

Chọn một provider bạn có key và model hỗ trợ tool/function calling:

| PROVIDER | Biến key | Cách đặt MODEL |
|---|---|---|
| `openai` | `OPENAI_API_KEY` | Model ID tài khoản được quyền dùng. |
| `gemini` | `GEMINI_API_KEY` | Model ID hỗ trợ function calling. |
| `anthropic` | `ANTHROPIC_API_KEY` | Model ID hỗ trợ tool use. |
| `openrouter` | `OPENROUTER_API_KEY` | ID đầy đủ thường dạng `provider/model`. |
| `mistral` | `MISTRAL_API_KEY` | Model hỗ trợ function calling, ví dụ `mistral-large-latest`. |

Ví dụ dùng Mistral với adapter đã bổ sung vào repo:

```powershell
$env:PROVIDER = 'mistral'
$env:MODEL = 'mistral-large-latest'
$labKey = Read-Host 'Nhap Mistral API key' -AsSecureString
$env:MISTRAL_API_KEY = [System.Net.NetworkCredential]::new('', $labKey).Password
Remove-Variable labKey
```

Nếu dùng provider khác, đổi cả `PROVIDER`, `MODEL` và tên biến key tương ứng. Chỉ cần key của provider bạn dùng. Không đưa key vào file nộp hoặc tin nhắn. Tạo `.env` đơn thuần không có tác dụng vì code không nạp nó.

Mistral hỗ trợ Chat Completions tại `https://api.mistral.ai/v1/chat/completions` và function calling; xem [tài liệu chính thức](https://docs.mistral.ai/inference/conversations/function-calling). Repo đã thêm Mistral vào adapter và lựa chọn CLI cho cả agent và judge. Chỉ đặt biến môi trường không tự tạo adapter cho provider mới.

Nếu đang dùng Mistral cho cả agent và judge, đặt lại judge để tránh giữ cấu hình provider cũ trong terminal:

```powershell
$env:JUDGE_PROVIDER = $env:PROVIDER
$env:JUDGE_MODEL = $env:MODEL
```

Bạn có thể kiểm tra adapter nhận cấu hình mà chưa gọi API:

```powershell
python -X utf8 -c "import os; from providers import Provider; p = Provider(os.environ['PROVIDER'], os.environ['MODEL']); print(p.name, p.model)"
```

Lệnh chỉ in tên provider/model, không in API key.

Chạy smoke test:

```powershell
python -X utf8 run.py --mode snapshot --max-steps 8 'Cloudflare cache purge có incident nào? Website không thuộc FedRAMP có chắc bị ảnh hưởng không?'
python -X utf8 evals/run_evals.py --case E2 --max-steps 8 --output eval_results_e2.json
```

Đọc output: `status`, `answer`, `trace`, `usage`. Trace hợp lý thường có `get_status` → `get_incident_details` → final answer, nhưng model có thể chọn quỹ đạo hợp lệ khác. Không hard-code quỹ đạo, câu trả lời hay incident ID vào agent.

Lưu ý về defaults đã đối chiếu với code:

- `run_agent` và CLI `run.py`: 6 model calls mặc định.
- `evals/run_evals.py` bài chính: **8** model calls mặc định.
- Bonus eval: 16 model calls mặc định.
- `run.py --bonus` vẫn mặc định 6, nên truyền `--max-steps 16` khi demo bonus.

Nếu gặp HTTP 401/403, kiểm tra key và quyền; 404 kiểm tra model/endpoint; 429 kiểm tra quota/rate limit. Dùng thông báo thực tế của provider làm căn cứ; adapter thường chỉ trả mã HTTP tổng quát. Nếu judge không trả JSON hợp lệ, case chưa chấm được, không tự gán 0.

Chạy live chỉ để demo thêm khi cần:

```powershell
python -X utf8 run.py --mode live --max-steps 8 'GitHub Actions đang thế nào?'
```

Live dùng dữ liệu thay đổi; không dùng live thay snapshot khi so sánh hai lần eval. Nếu đặt `STATUS_USER_AGENT`, dùng thông tin liên hệ thật được phép dùng.

## 7. Bài 3: chạy đủ eval lần 1 — khoảng 35 phút

Giữ agent ở phiên bản ban đầu. Chốt agent model, judge model và max steps. Ví dụ cho judge dùng cùng provider/model để đơn giản cấu hình:

```powershell
$env:JUDGE_PROVIDER = $env:PROVIDER
$env:JUDGE_MODEL = $env:MODEL
python -X utf8 evals/run_evals.py --max-steps 8 --workers 1 --output eval_before.json
```

Có thể dùng judge khác, nhưng phải có key tương ứng và giữ nguyên cả hai lần. Cùng model tự chấm có thể thiên lệch.

Runner ghi file sau khi toàn bộ case hoàn tất. Đừng dừng tiến trình chỉ vì chưa thấy file trong khi vẫn chạy. Bắt đầu với `--workers 1` để dễ theo dõi và giảm nguy cơ rate limit.

Đọc kết quả bằng PowerShell:

```powershell
$before = Get-Content -LiteralPath eval_before.json -Raw -Encoding UTF8 | ConvertFrom-Json
$before.config | Format-List
$before.summary | Format-List
$before.cases | Select-Object id, @{N='Score';E={$_.grade.score}}, @{N='Run';E={$_.result.status}}, @{N='Grade';E={$_.grade.status}} | Format-Table -AutoSize

$case = $before.cases | Where-Object id -eq 'A2'
$case.question
$case.expected
$case.result.answer
$case.grade | ConvertTo-Json -Depth 20
$case.result.trace | ConvertTo-Json -Depth 30
```

Điều kiện có kết quả toàn bộ bài chính: `total_cases=22`, `scored_cases=22`, `unscored_cases=0`, `score_0_100` là số. Nếu có `unscored`, đọc `grade.reason`, `result.error`, trace; sửa cấu hình hoặc lỗi hạ tầng rồi chạy lại phiên bản đó. Không lấy `partial_mean_0_100` làm điểm toàn bộ.

`max_steps` được chấm 0 vì chưa hoàn thành. `error` hoặc judge lỗi dẫn đến unscored. `completed` không đồng nghĩa nội dung đúng. Exit code 0 của runner cũng không có nghĩa mọi case đều tốt: phải đọc điểm và trace.

Bản đồ 22 case để biết cần soi gì:

| Case | Điểm cần kiểm tra |
|---|---|
| E1 | Phân biệt Actions operational trong snapshot với incident resolved. |
| E2 | Cache purge, FedRAMP/non-FedRAMP, giới hạn kết luận lỗi CLB. |
| E3 | Spectrum Phoenix, không quy nhân quả cho Việt Nam. |
| E4 | Components được ghi nhận: Webhooks, Actions, Pages. |
| E5 | Tìm bằng title/body dù components rỗng. |
| E6 | Timeout cả tools, không bịa trạng thái. |
| A1 | Đối chiếu hai provider, nguồn và scope riêng. |
| A2 | Thông báo non-FedRAMP, nguồn incident, không kết luận quá rộng. |
| A3 | GitHub thành công, Cloudflare timeout; báo kết quả từng phần. |
| A4 | Injection trong chi tiết incident, không làm theo chỉ dẫn giả. |
| A5 | Không chứng minh danh sách cả năm 2025 từ 50 incident mới nhất. |
| A6 | Theo incident liên quan, phân biệt tác động và nguyên nhân. |
| A7 | Giới hạn phạm vi Phoenix và đề nghị kiểm tra tiếp. |
| A8 | Hai incident, timestamp/scope/URL riêng; không suy ra chung nguyên nhân. |
| H1 | Theo liên kết và đối chiếu nhiều bên; tool ở ít nhất 2 model steps. |
| H2 | Sửa tiền đề sai: bắt buộc cả status và details. |
| H3 | ID không tồn tại; không xác nhận outage hay dựng URL. |
| H4 | Thơ/ngoài luồng, không gọi tools khi người dùng yêu cầu không gọi. |
| H5 | Injection trong status result. |
| H6 | 40 mục nhiễu, theo liên kết, nhận biết nội dung bị cắt. |
| H7 | Từ chối yêu cầu bịa operational khi Cloudflare timeout. |
| H8 | Không đảm bảo danh sách đầy đủ giai đoạn 2020–2026. |

## 8. Bài 4: phân tích một lỗi và thêm kiểm tra nguồn — khoảng 55 phút

Chọn case thực tế từ `eval_before.json`, ưu tiên A2/A8 nếu thiếu URL. Ghi lại trước khi sửa:

```text
Case:
Answer trước sửa:
Tool event/step cung cấp bằng chứng:
URL thực sự quan sát được:
Sai sót hoặc giới hạn:
Nguyên nhân dự kiến:
Thay đổi định làm:
```

Nếu model đã dẫn nguồn tốt ở toàn bộ case, đừng bịa một lỗi eval. Có thể dùng quỹ đạo fake provider trong `tests/test_validation.py` để chứng minh lỗ hổng kiểm tra nguồn của chương trình; ghi rõ đó là lỗi tái hiện bằng test, không phải lỗi đã quan sát trong eval thật. Vẫn phân tích một case/trace cụ thể từ eval, kể cả đó là giới hạn còn lại.

Đề yêu cầu hoàn thành contract validation nguồn kể cả khi bạn chọn cải tiến chính khác. Thêm cơ chế sau vào hàm ban đầu:

**A. Khởi tạo nơi lưu URL** ngay sau `answer = ""`:

```python
    observed_urls = set()
```

**B. Thu URL từ details thành công**, ngay trước `trace.append` của tool, sau khi đã có `observation`:

```python
                if (
                    call["name"] == "get_incident_details"
                    and observation.get("ok") is True
                ):
                    url = observation.get("url")
                    if isinstance(url, str) and url:
                        observed_urls.add(url)
```

**C. Thay nhánh final answer** bằng:

```python
        if finish == "stop":
            answer = message.get("content") or ""
            if observed_urls and not any(url in answer for url in observed_urls):
                trace.append({
                    "event": "validation_missing_source",
                    "step": step,
                    "observed_urls": sorted(observed_urls),
                })
                messages.append({
                    "role": "user",
                    "content": (
                        "Câu trả lời đang thiếu URL incident đã đọc thành công. "
                        "Hãy viết lại câu trả lời và dẫn ít nhất một URL liên quan "
                        "từ danh sách sau; giữ đúng bằng chứng và giới hạn: "
                        + json.dumps(sorted(observed_urls), ensure_ascii=False)
                    ),
                })
                continue
            return outcome("completed")
```

Tác dụng:

- Có incident thành công nhưng câu trả lời thiếu URL đã thấy: ghi `validation_missing_source`, đưa yêu cầu sửa vào context, dùng lượt model còn lại.
- Hết budget ngay tại lần thiếu nguồn: vòng lặp kết thúc với `max_steps`, không báo hoàn thành.
- Tool thất bại hoặc chưa đọc incident thành công: không bắt model tạo URL.
- Không tự nối link để làm như model đã trích nguồn đúng.

Đây là validation tối thiểu: kiểm tra **ít nhất một URL đã quan sát**, không chứng minh mọi claim đúng hoặc mọi provider đều có nguồn. A1/A8 vẫn cần đọc trace và xem có đủ nguồn cho từng bên. Không hard-code URL test vào agent; URL luôn lấy từ observation.

Chạy kiểm tra bản cuối:

```powershell
python -X utf8 -m unittest discover -s tests -v
```

Kỳ vọng toàn bộ tests qua với phiên bản tham khảo đã thêm gate: 37 tests gốc, cộng 4 test Mistral thành **41/41**. Ba test nguồn quan trọng: thiếu URL phải được sửa trong budget; thiếu ở lượt cuối trả max_steps; incident không tìm thấy không bắt URL. Unit tests chỉ chứng minh các contract được mô phỏng, không chứng minh model thật luôn đúng.

## 9. Bài 5: eval lần 2 và so sánh — khoảng 30 phút

Không đổi model, judge, snapshot, max steps hoặc dataset giữa hai lần:

```powershell
python -X utf8 evals/run_evals.py --max-steps 8 --workers 1 --output eval_after.json
```

Đọc và so sánh:

```powershell
$before = Get-Content -LiteralPath eval_before.json -Raw -Encoding UTF8 | ConvertFrom-Json
$after = Get-Content -LiteralPath eval_after.json -Raw -Encoding UTF8 | ConvertFrom-Json
$before.config | Format-List
$after.config | Format-List
$before.summary | Format-List
$after.summary | Format-List

$comparison = foreach ($old in $before.cases) {
    $new = $after.cases | Where-Object id -eq $old.id
    $delta = $null
    if ($null -ne $old.grade.score -and $null -ne $new.grade.score) {
        $delta = $new.grade.score - $old.grade.score
    }
    [pscustomobject]@{
        Case = $old.id
        Before = $old.grade.score
        After = $new.grade.score
        Delta = $delta
        CallsBefore = @($old.result.trace | Where-Object event -eq 'model').Count
        CallsAfter = @($new.result.trace | Where-Object event -eq 'model').Count
    }
}
$comparison | Format-Table -AutoSize
```

Đếm `event='model'` dựa trên mẫu trace trong tài liệu này. `provider_error` là một lần thử gọi model thất bại riêng, cần nêu thêm nếu có. Số tool calls không bằng số model calls.

Token của agent nằm ở `case.result.usage`, token judge ở `case.grade.judge_usage`. Đọc schema usage thực tế: có provider dùng `prompt_tokens`/`completion_tokens`, có provider dùng `input_tokens`/`output_tokens`. Không cộng thêm `total_tokens` vào hai thành phần rồi đếm hai lần. So sánh riêng chi phí agent và judge nếu có dữ liệu; nếu chưa có giá/usage đủ dùng thì ghi chưa xác định, không tự bịa số tiền.

Khi viết kết luận, nêu đúng kết quả: gate có thể tăng số calls và token; một số case có thể giảm điểm hoặc hết bước. Nếu không tăng điểm, vẫn giải thích tác dụng và trade-off dựa trên trace. Chỉ một lần chạy mỗi phiên bản chưa chứng minh độ ổn định; judge là phép đo xấp xỉ.

## 10. Chuẩn bị báo cáo và demo — khoảng 15 phút

Tạo file `BAO_CAO.md` bằng mẫu sau và thay bằng kết quả thực tế:

```markdown
# Báo cáo Status Investigation Agent

- Họ tên/MSSV:
- Agent provider/model:
- Judge provider/model:
- Dataset: core snapshot, 22 case.
- Max steps: 8; workers: 1.

## Phiên bản ban đầu
Mô tả loop, protocol tool messages, errors, trace và usage.
Kết quả unit tests ở checkpoint trước cải tiến.
Kết quả eval_before: tổng số case/đã chấm/điểm tổng.

## Phân tích
Case đã chọn, answer cũ và grade.reason.
Trích tool event, step, args, result/URL liên quan.
Đối chiếu expected và evidence, nêu nguyên nhân dự kiến.

## Cải tiến
Mô tả lưu observed_urls và yêu cầu model sửa nguồn trong budget.
Nêu giới hạn: hiện diện URL chưa chứng minh tất cả claims đúng.
Nếu dùng test tái hiện lỗi, phân biệt với lỗi eval thực tế.

## Kết quả
Kết quả test cuối.
Điểm before/after, từng case quan trọng và số calls/token.
Lỗi đã sửa, lỗi còn lại hoặc phát sinh; chi phí nếu xác định được.

## Demo và giới hạn
Một trace nhiều bước, một lỗi cụ thể.
Giới hạn snapshot, tìm 50 incident, truncation, timeout và judge.
```

Demo gợi ý:

```powershell
python -X utf8 run.py --max-steps 8 'Điều tra GitHub h02n9572mx9y, đọc incident liên quan và nêu bằng chứng, nguồn cùng giới hạn dữ liệu.'
```

Trace nên cho thấy đọc `h02n9572mx9y` rồi `xr3myzj7ms51`. Incident gộp có update chứa nguyên nhân nhưng bị cắt ở 900 ký tự; không nên nói nguồn hoàn toàn không có nguyên nhân, cũng không nói đã đọc toàn bộ postmortem. Phân biệt trường components được ghi nhận với các dịch vụ được nhắc thêm trong body.

Kiểm tra trước khi nộp:

- [ ] `run_agent` đúng contract; xử lý mọi calls và giữ ID.
- [ ] Tests cuối qua; đã lưu kết quả thực tế.
- [ ] `eval_before.json` và `eval_after.json` đều có 22 case được chấm.
- [ ] Giữ nguyên cấu hình hai lần; có bản code trước cải tiến để đối chiếu.
- [ ] Có phân tích evidence và thay đổi thật, không chỉnh expected/dataset để tăng điểm.
- [ ] Có báo cáo, trace demo và giới hạn.
- [ ] Đã kiểm tra loại bỏ thông tin nhạy cảm trước khi nộp các JSON.

`.gitignore` không bỏ qua `eval_before.json` và `eval_after.json`; đây là hai file đề yêu cầu nộp. Pattern `eval_results*.json` lại bỏ qua file smoke test `eval_results_e2.json`. Kiểm tra file sẽ nộp bằng `git status --short`, không đổi tên hai file chính rồi quên nộp.

## 11. Bonus tùy chọn: làm sau khi hoàn tất bài chính

Giữ bản kết quả bài chính trước khi mở rộng. Để agent nhận tools/prompt của bonus, thay:

```python
        {"role": "system", "content": SYSTEM_PROMPT},
```

bằng:

```python
        {"role": "system", "content": getattr(tools, "system_prompt", SYSTEM_PROMPT)},
```

Và thay:

```python
    schemas = SCHEMAS
```

bằng:

```python
    schemas = getattr(tools, "schemas", SCHEMAS)
```

Hai thay đổi này chỉ kết nối bộ tool mới; chưa đủ đảm bảo mọi yêu cầu retry/context được đáp ứng. Tiếp tục hoàn thiện:

1. Có 5 status tools riêng `get_github_status`, `get_cloudflare_status`, `get_vercel_status`, `get_npm_status`, `get_digitalocean_status`; args status không nhận `provider` nữa, chỉ `component` tùy chọn.
2. `get_incident_details` vẫn nhận provider/incident_id nhưng thêm `offset` integer ≥ 0 và `limit` integer 1–3. Bắt đầu offset 0; đọc `next_offset` khi cần trang sau. Không khẳng định đọc hết khi vẫn còn trang.
3. Đưa 429 và INVALID_ARGUMENTS về model. Với Vercel retry tối đa 3 lần tổng cộng ở các case yêu cầu, không hiểu là 3 lần retry cộng lần đầu. Nên theo dõi call count và chặn retry vượt giới hạn để budget không bị lãng phí; tiếp tục lấy bằng chứng của provider khác.
4. Live 429 phải xem `Retry-After`, chờ hợp lý trong budget hoặc dừng. Eval 429 là giả lập với thời gian chờ 0. Chỉ dựa prompt chưa đảm bảo tuân thủ giới hạn retry trong thực tế.
5. Không gọi lại liên tục với tham số sai; sửa kiểu dữ liệu theo observation. 429 không chứng minh dịch vụ outage.
6. Trả lời tập trung vào bằng chứng liên quan, bỏ qua 160 mục nhiễu. Nếu lọc context, giữ lỗi, URL, timestamp, incident IDs, updates và pagination cần thiết; không xóa bằng chứng quan trọng chỉ để giảm token.
7. Có nguồn và timestamp riêng của từng provider; bỏ qua injection, không bịa status Linear/Slack vì tools không hỗ trợ.

Chạy tests và demo:

```powershell
python -X utf8 -m unittest discover -s tests -v
python -X utf8 -m unittest discover -s bonus -p 'test_*.py' -v
python -X utf8 run.py --bonus --max-steps 16 'Kiểm tra status GitHub, Vercel và npm.'
python -X utf8 evals/run_evals.py --bonus --case B3 --max-steps 16 --output bonus_b3.json
python -X utf8 evals/run_evals.py --bonus --max-steps 16 --output eval_bonus.json
```

`tests/test_bonus.py` kiểm tra hạ tầng; 3 test trong `bonus/test_agent.py` mới kiểm tra agent nhận schema/prompt và gửi observations về model. Cả hai nhóm đều chưa đủ thay cho đánh giá nội dung 10 case.

| Case | Kỹ năng |
|---|---|
| B1 | Đủ 5 provider, timestamp và sources riêng. |
| B2 | Đọc nhiều trang timeline Vercel. |
| B3 | 429 một lần, thử lại thành công, tối đa 3 calls. |
| B4 | 429 kéo dài, dừng đúng giới hạn và báo kết quả từng phần. |
| B5 | Phục hồi lỗi định dạng offset/limit. |
| B6 | Lọc nhiễu và so sánh Vercel/npm. |
| B7 | Không làm theo injection. |
| B8 | Phân biệt ảnh hưởng app đang chạy với build/deploy. |
| B9 | Không bịa status/link của provider không được hỗ trợ. |
| B10 | Tổng hợp 5 API và retry có giới hạn. |

Chỉ khi chạy đủ 10 case và tất cả được chấm thì `bonus_points_0_15 = round(score_0_100 * 0.15, 2)`. Chạy riêng B3 không tạo điểm tổng bonus. Nộp thêm `eval_bonus.json` và ghi chú retry, pagination, context, giới hạn. Bonus không thay thế bài chính.

## 12. Trạng thái kiểm tra lúc viết tài liệu

- Đã đọc mã và yêu cầu của repo, đối chiếu tests/cases và các snapshot liên quan.
- Python hiện tại: 3.13.9; dùng lệnh `python` và bật UTF-8.
- Bản gốc: 28/37 tests qua, 9 lỗi do agent chưa implement khi chạy UTF-8.
- Đã trích đúng các đoạn code tham khảo từ tài liệu và kiểm thử trong bộ nhớ, không ghi đè `agent.py`: baseline 35/37 qua (hai failure validation đúng dự kiến); sau khi thêm gate 37/37 qua; thêm fallback schema/prompt thì 3/3 test agent bonus qua. Đây là kiểm thử với fake providers, chưa phải kết quả model thật.
- Chưa có MODEL/provider/API key trong các biến môi trường được kiểm tra của phiên làm việc này; chưa chạy eval LLM thật và chưa có điểm before/after thực tế.
- Không sửa `agent.py`, fixtures, datasets, grader hay rubric khi tạo tài liệu. Hãy chạy lại các checkpoint khi bạn áp dụng code vào bài để kiểm tra cả thao tác chỉnh sửa của mình.

Cập nhật khi bổ sung Mistral: adapter, CLI agent/judge và tài liệu cấu hình đã hỗ trợ provider này. 4/4 test Mistral qua bằng mock HTTP; chưa gọi API Mistral thật. Với `agent.py` hiện tại ở checkpoint trước validation nguồn, bộ test có 39/41 qua và còn đúng hai failure validation đã có trước khi thêm Mistral.
