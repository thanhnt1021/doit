# Mẫu tệp chép sang dự án mới

## 1. Cổng chặn gửi không mã — `.claude/chan-gui-sep-khong-ma.py`
```python
#!/usr/bin/env python3
# Chặn mọi lệnh gửi vào nhóm sếp mà không đi qua CLI hoặc không có mã Task.
# Vì sao: tin gửi bằng sendMessage thẳng không có mã → sếp trả lời sẽ không vào sổ việc.
import json, re, sys

d = json.load(sys.stdin)
if d.get("tool_name") != "Bash":
    sys.exit(0)
cmd = d.get("tool_input", {}).get("command", "")
gui_tg = re.search(r"send(Message|MediaGroup|Document|Photo)", cmd) and ("api.telegram.org" in cmd or "TG_CHAT_SEP" in cmd)
# Nhắn riêng chủ nhà được phép (không phải nhóm sếp).
if not gui_tg or "sep_viec.py" in cmd or "TG_CHU_NHA_ID" in cmd or re.search(r"Task-\d{8}-\d+", cmd):
    sys.exit(0)
print("⛔ Gửi vào nhóm sếp mà KHÔNG có mã Task → sếp trả lời sẽ mất khỏi sổ việc.\n"
      "Tin chữ: python3 scripts/sep-viec/sep_viec.py gui --ma Task-<ngày giao gốc>-NN ...\n"
      "Ảnh/PDF gửi kèm thì ghi mã Task-… vào caption.", file=sys.stderr)
sys.exit(2)
```

## 2. Gắn hook — `.claude/settings.local.json` (CỘNG vào khối `hooks` đang có)
```json
"hooks": {
  "SessionStart": [{ "hooks": [{ "type": "command",
    "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/viec-sep-update.sh\" mo-phien", "timeout": 60 }] }],
  "UserPromptSubmit": [{ "hooks": [{ "type": "command",
    "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/viec-sep-update.sh\"", "timeout": 20 }] }],
  "PreToolUse": [{ "matcher": "Bash", "hooks": [{ "type": "command",
    "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/chan-gui-sep-khong-ma.py\"", "timeout": 10 }] }]
}
```

## 3. Hook mở phiên + nhắc — `.claude/viec-sep-update.sh` (khung)
```bash
#!/usr/bin/env bash
# mo-phien (SessionStart): kéo sổ + in tin chưa đọc ≤6 dòng + nhắc bật con canh.
# không tham số (UserPromptSubmit): «check viec sep» → chèn quy trình + moi; câu khác chỉ đọc tệp trạng thái canh.
# LUÔN exit 0 — hook không bao giờ chặn câu gõ.
DIR="$(cd "$(dirname "$0")/.." && pwd)"
TT="$DIR/.claude/sep-viec/trang-thai.json"; PID="$DIR/.claude/sep-viec/canh.pid"; NHAC="$DIR/.claude/sep-viec/da-nhac.txt"
CLI="python3 scripts/sep-viec/sep_viec.py"
canh_song(){ [ -f "$PID" ] && kill -0 "$(cat "$PID" 2>/dev/null)" 2>/dev/null; }
if [ "${1:-}" = "mo-phien" ]; then
  cd "$DIR" || exit 0
  # nhịp phiên (SKILL 7d.5): tách nền rồi về ngay — không có nó, lúc con canh nghỉ bot báo sai «chưa có phiên».
  bash "$DIR/.claude/nhip-phien.sh" 2>/dev/null || true
  keo=$($CLI keo 2>&1 | head -n 1); moi=$($CLI moi 2>&1)
  echo "[Việc sếp] ${keo:-(không kéo được sổ)}"; printf '%s\n' "$moi" | head -n 6
  canh_song && echo "[Việc sếp] Con canh đang chạy." \
            || echo "[Việc sếp] Bật con canh NỀN (run_in_background, timeout 7200000): $CLI canh"
  exit 0
fi
prompt=$(python3 -c "import sys,json
try: print(json.load(sys.stdin).get('prompt',''))
except Exception: pass" 2>/dev/null)
if printf '%s' "$prompt" | grep -qiE 'check[[:space:]]+(viec|việc)[[:space:]]+(sep|sếp)'; then
  echo "⚡ LỆNH \"check viec sep\" → làm ĐÚNG .claude/commands/check-viec-sep.md. Tin chưa đọc lúc này:"
  (cd "$DIR" && $CLI moi 2>&1) || echo "(không lấy được — tự chạy: $CLI moi)"
  exit 0
fi
# câu khác: đọc $TT (ids chưa đọc), khác bộ id đã nhắc trong $NHAC thì in 1 dòng nhắc rồi ghi lại $NHAC.
exit 0
```

## 3b. Nhịp phiên — `.claude/nhip-phien.sh` (SKILL mục 7d.5)
```bash
#!/usr/bin/env bash
# Bật NHỊP PHIÊN nền: lệnh CLI `nhip-phien` gửi `X-Phien: 1` mỗi phút chừng nào phiên Claude của dự án còn mở,
# tự thoát khi hết phiên. Hook SessionStart có trần giây → chỉ TÁCH tiến trình rồi về ngay. LUÔN exit 0.
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID="$DIR/.claude/sep-viec/nhip-phien.pid"; LOG="$DIR/.claude/sep-viec/nhip-phien.log"
mkdir -p "$(dirname "$PID")"
if [ -f "$PID" ] && kill -0 "$(cat "$PID" 2>/dev/null)" 2>/dev/null; then exit 0; fi   # một nhịp mỗi máy
[ -f "$LOG" ] && [ "$(wc -c <"$LOG")" -gt 204800 ] && { tail -c 102400 "$LOG" >"$LOG.tmp" && mv "$LOG.tmp" "$LOG"; }
cd "$DIR" || exit 0
# MỘT lệnh đơn trong nền (không «(cd && …) &» — sót vỏ bash). macOS không có lệnh setsid → python3 os.setsid.
python3 -c 'import os,sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])' \
  python3 scripts/sep-viec/sep_viec.py nhip-phien --thu-muc "$DIR" </dev/null >>"$LOG" 2>&1 &
exit 0
```
Lệnh `nhip-phien` trong CLI tự giữ chỗ bằng tệp pid mở `O_EXCL` (cửa trên chỉ là lối tắt — hai hook cùng lúc vẫn có
thể lọt qua `kill -0`), dò tiến trình `claude` có cwd trong `--thu-muc`, hết thì thoát và xoá tệp pid của mình.

## 4. Lệnh xử lý — `.claude/commands/check-viec-sep.md` (5 bước)
1. `moi` → mở ảnh bằng Read; toàn cảnh: `keo` rồi đọc `SO-VIEC.md`.
2. Từng mục: **việc mới** → nhận (`trang-thai --tt dang-lam`) và làm theo luật dự án · **câu trả lời** → làm tiếp đúng việc ·
   **tin sửa** → so bản cũ/mới, đang làm theo bản cũ thì sửa. Không rõ → hỏi chủ nhà (nhắn riêng), không đoán.
3. `da-doc --id <id đã xử>` — đích danh.
4. BOT thả ❤ tin việc + tin trả lời (nếu bản có `tim`) = báo «đã xử»; bật lại `canh` nền. ❤ chủ nhà thả chỉ là «đã đọc», không phải duyệt (SKILL mục 4.9).
5. Ghi «xử lý xong việc gì» vào sổ tiếp tục của dự án; `keo` cập nhật sổ.

## 5. Tệp dấu — `docs/bot-nhan-viec.json`
```json
{ "trang_thai": "da-co", "bot": "@ten_bot", "nhom": "Tên nhóm", "cli": "scripts/sep-viec/sep_viec.py", "ghi_luc": "2026-10-09" }
```

## 6. Cổng ghi thẻ khi chủ quyết trong CLI — `.claude/ghi-the-enforce.py` (khung)
Một tệp, ba chế độ, cắm ba chỗ trong `.claude/settings.json`. Fail-open (lỗi bất kỳ → cho qua).
```python
#!/usr/bin/env python3
# Vì sao: chủ quyết ngay trong CLI («Task-… 1A», «ừ làm đi») mà máy không ghi thẻ → thẻ đứng sai trạng thái.
# Luật markdown = xác suất → chuyển thành cổng.
import json, os, re, sys
MA = re.compile(r"Task-\d{8}-\d{2,3}")
QUYET = re.compile(r"\b\d[A-D]\b|\b(ừ|ok|oke|chốt|giữ nguyên|bỏ|làm đi)\b", re.I)
TIN_MAY = ("<task-notification>", "[SYSTEM NOTIFICATION")   # thông báo máy KHÔNG phải lời chủ
che_do = sys.argv[1] if len(sys.argv) > 1 else "--pre"
d = json.load(sys.stdin)
kho = f"/tmp/claude_hooks/ghi-the/{d.get('session_id','x')}.json"
if che_do == "--prompt":                       # UserPromptSubmit: lưu {mã, mốc}; không bao giờ chặn
    p = d.get("prompt", "")
    if any(t in p for t in TIN_MAY): sys.exit(0)
    ma = MA.findall(p)
    if ma and QUYET.search(p): ...              # ghi {ma, moc_transcript} vào kho
    sys.exit(0)
if che_do == "--stop":                         # Stop: CỔNG CHÍNH
    # đọc kho; quét transcript từ mốc: có lệnh `<cli> ghi|chuyen --ma <đúng mã>` chưa?
    # có lệnh mang `khong-can-ghi-the: <lý do>` → thoát. Chặn tối đa 3 lần/lượt.
    # thiếu → print(json.dumps({"decision":"block","reason":"Ghi thẻ <mã>: <cli> ghi --ma <mã> --noi-dung '<tình hình ngắn>'"}))
    sys.exit(0)
# --pre (PreToolUse:Bash): nội dung ghi có dấu chép nguyên văn («tao», «mày», trích dài) → chỉ in nhắc, không chặn.
sys.exit(0)
```
Ca thử tối thiểu: lời chủ «Task-… 1A» → Stop chặn; sau `ghi --ma` → qua; `<task-notification>` có mã + «1A» → không đòi.

## 7. Nghe tin thoại — bản gọn PHP (`priv/lib.php`, khung)
```php
<?php
// Vì sao: sếp trả lời bằng thoại → không nghe thì thẻ thành «[tin không có chữ]» (skill mục 4b).
// Gọi ở hook.php SAU khi đã echo '{"ok":true}' + fastcgi_finish_request() — nghe mất vài giây, Telegram không được chờ.
function thoai_cua(array $m): ?array {
    foreach ([['voice','audio/ogg'], ['audio','audio/mpeg'], ['video_note','video/mp4']] as [$k, $mime])
        if (!empty($m[$k]['file_id']))
            return ['id' => $m[$k]['file_id'], 'giay' => (int)round($m[$k]['duration'] ?? 0),
                    'mime' => $m[$k]['mime_type'] ?? $mime, 'co' => $m[$k]['file_size'] ?? null];
    return null;
}
function dong_ho(int $s): string { return intdiv($s, 60) . ':' . str_pad((string)($s % 60), 2, '0', STR_PAD_LEFT); }
function nghe_thoai(array $t): array {           // trả ['dong' => chữ thay tin, 'loi' => null|lý do]
    $dau = '🎤 (thoại ' . dong_ho($t['giay']) . ')';
    $hong = fn($l) => ['dong' => "$dau thoại chưa nghe được — $l", 'loi' => $l];
    if (($t['co'] ?? 0) > 19 * 1024 * 1024) return $hong('tệp quá 19 MB');
    $tok = getenv('TG_BOT_TOKEN');
    $f = json_decode(@file_get_contents("https://api.telegram.org/bot$tok/getFile?file_id=" . urlencode($t['id'])), true);
    $duong = $f['result']['file_path'] ?? null;
    if (!$duong) return $hong('Telegram không cho tải tệp');
    $bytes = @file_get_contents("https://api.telegram.org/file/bot$tok/$duong");
    if (!$bytes) return $hong('tải tệp thoại hỏng');
    $nhac = 'Chép NGUYÊN VĂN lời nói trong đoạn ghi âm (chủ yếu tiếng Việt, có thể lẫn tiếng Anh, mã đơn, mã thẻ, mã lựa chọn '
          . 'kiểu 1A 2B). Viết tiếng Việt có dấu, thêm dấu câu. Không giải thích, không tóm tắt. Không nghe ra lời nào thì trả chuỗi rỗng.';
    foreach (explode(',', getenv('GEMINI_THOAI_MODELS') ?: 'gemini-3.5-flash-lite,gemini-flash-lite-latest,gemini-3.5-flash') as $model) {
        $ch = curl_init("https://generativelanguage.googleapis.com/v1beta/models/" . trim($model) . ":generateContent");
        curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 30,
            CURLOPT_HTTPHEADER => ['Content-Type: application/json', 'x-goog-api-key: ' . getenv('GEMINI_API_KEY')],
            CURLOPT_POSTFIELDS => json_encode(['contents' => [['parts' => [['text' => $nhac],
                ['inline_data' => ['mime_type' => $t['mime'], 'data' => base64_encode($bytes)]]]]],
                'generationConfig' => ['temperature' => 0]])]);
        $j = json_decode((string)curl_exec($ch), true);
        $ma = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($ma !== 200) continue;                 // hết lượt / quá tải → model sau
        $chu = trim(implode('', array_map(fn($p) => empty($p['thought']) ? ($p['text'] ?? '') : '',
                     $j['candidates'][0]['content']['parts'] ?? [])));
        return $chu === '' ? $hong('không nghe ra lời nào') : ['dong' => "$dau $chu", 'loi' => null];
    }
    return $hong('hết lượt nghe trong ngày');
}
// hook.php: $t = thoai_cua($m); if ($t && trim($m['text'] ?? '') === '') { $kq = nghe_thoai($t);
//   $m['text'] = trim($kq['dong'] . "\n" . ($m['caption'] ?? '')); if ($kq['loi']) bao_chu_nha(...); }
//   rồi chạy tiếp đúng đường tin chữ (mục 4 của skill) với $m đã có chữ.
```
Bản đầy đủ (Next.js): một tệp `nghe-thoai.ts` cùng 3 hàm (`thoaiCua` · `ngheTinThoai` · `dongThoai`) + webhook trả `ok()` rồi
trong `after()` nghe xong tự `POST` lại chính webhook (secret + header dấu đã nghe) với `message.text` đã thay.
