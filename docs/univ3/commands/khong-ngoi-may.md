---
description: Không ngồi máy (AFK) — cấm AskUserQuestion, câu hỏi gửi theo danh sách vào inbox, rồi chạy một mạch không xin quyền, canh worker, chốt bằng danh sách câu cần founder quyết
---

# Không ngồi máy (AFK — Away From Keyboard)

Founder gõ lệnh này khi **sắp rời máy**: đi ra ngoài, đi gym, đi ngủ, không ngồi trước màn hình.
Lệnh dùng cho **MỌI dự án, MỌI phiên** — đây là lệnh tầng hệ thống (`~/.claude/commands/`),
không phải lệnh riêng của một kho mã.

Nguyên văn founder (chốt 07/09/2026):

> "tao hay ra ngoài không ngồi máy... cần xử lý toàn bộ các running task và waiting task và
> new task added, để nó quan sát tổng thể và chỉ chạy 1 mạch không chờ tao cấp quyền gì cả.
> Tuy nhiên, cần xả ra 1 loạt các câu hỏi dạng AskUserQuestion đầu tiên, để tao trả lời hết...
> thả worker chờ hợp lý không được đợi hay là ngáo chó... cứ chạy, không được phá vào data gốc
> để hỏng dự án hay server của tao... khi nào chạy xong prod demo deploy hết rồi, không còn
> worker nào run hay trong hàng chờ thì liệt kê ra 1 loạt các câu cần tao quyết."

> ⚠️ Phần «xả AskUserQuestion» trong lời trên **đã được thay** bằng lời chốt 11/10/2026: câu hỏi gửi
> theo danh sách vào **inbox**, cấm `AskUserQuestion` lúc AFK (xem GĐ1).

**Bí danh:** `/afk` — cùng một giao thức, đọc chính file này.
**Cặp đối xứng:** `/dau-ngay` (mở ngày) · `/chot-ngay` (đóng ngày). AFK **không thay thế** hai lệnh đó:
AFK là chế độ chạy giữa ngày khi founder vắng mặt.

---

## GIAO THỨC AFK — SÁU GIAI ĐOẠN, LÀM ĐỦ, ĐÚNG THỨ TỰ

### GĐ0 — Kiểm kê tổng thể (TRƯỚC KHI HỎI BẤT KỲ CÂU NÀO)

Chưa biết đang có gì trong tay thì hỏi ra câu vô nghĩa. Bắt buộc liệt kê **đủ ba loại việc**:

| Loại | Là gì | Lấy ở đâu |
|---|---|---|
| (a) **ĐANG CHẠY** | worker nền còn sống | `ListAgents` + `bash ~/.claude/universal-hooks/bg-progress.sh` |
| (b) **HÀNG CHỜ / BỊ CHẶN** | vé chưa thả, việc bị khoá tài nguyên, dòng `ĐỂ LẠI:` chưa có vé | `ls ~/.claude/worker-queue/<dự án>/` · `bash ~/.claude/universal-hooks/wlock.sh status` · `grep -H 'ĐỂ LẠI:' /tmp/w*-bao-cao*.md` |
| (c) **MỚI GIAO** | việc founder vừa nói trong chính lượt này | đọc lại prompt của founder |

Lệnh chạy nguyên văn:

```bash
bash ~/.claude/universal-hooks/bg-progress.sh                 # tự lấy scope dự án đang đứng
ls -la /tmp/claude-bg-progress/<dự án>/                        # mốc tiến trình từng worker
ls ~/.claude/worker-queue/*/ 2>/dev/null                       # vé hàng chờ
bash ~/.claude/universal-hooks/wlock.sh status                 # khoá tài nguyên dùng chung
python3 ~/.claude/universal-hooks/worker_board.py --liet-ke-bo-do --day-du
```

rồi gọi `ListAgents` để đối chiếu.

> ⛔ **CẤM BỎ SÓT VIỆC ĐANG CHẠY.** Founder ghi thẳng: _"không được để các running task bị ignored"_.
> Worker đang chạy dở mà AFK không nhắc tới = coi như bỏ rơi. Với mỗi worker đang chạy phải trả lời
> được: nó đang ở mấy %, nhãn cuối là gì, có cần founder quyết gì để nó đi tiếp không.

Kết thúc GĐ0: in ra cho founder **một bảng gọn** ba loại việc trên (mã `W##` · tên việc · trạng thái · %).

---

### GĐ1 — CÂU HỎI GỬI VÀO INBOX THEO DANH SÁCH — ⛔ CẤM `AskUserQuestion`

> Anh Thành chốt 11/10/2026 (thay luật cũ «xả một loạt AskUserQuestion»): _"tao đã bảo tao đang /afk
> sao mày cứ hỏi cái câu AskUserQuestion thế … đã bảo /afk thì câu hỏi gửi theo list vào inbox mà … fix đi"_.
> Founder đã gõ AFK là đã rời máy — hộp hỏi trong CLI không ai bấm, cả luồng đứng chờ tới lúc về.

**Cổng tất định:** `~/.claude/universal-hooks/afk_hoi_inbox_gate.py` (PreToolUse `AskUserQuestion`)
**chặn cứng** mọi lượt hỏi trong CLI khi cờ AFK đang bật (`~/.claude/afk/trang-thai.json`, do
`afk_mode.py` ghi). Cờ tắt khi founder gõ «tao về rồi» / «ngồi máy rồi» / «tắt afk». Founder nhắn tin
thường từ điện thoại lúc vắng **không** tắt cờ.

**Định nghĩa «đang vắng» (P005, C-HX 18/10/2026 — _"tao đã afk thì mày phải biết mà gửi vào tele chứ"_):**
một hàm duy nhất `afk_trang_thai.dang_vang()` cho MỌI cổng. Founder VẮNG khi: cờ còn hạn · HOẶC cờ đã
quá 8 tiếng mà từ lúc bật founder **chưa gõ lượt CLI thật nào** (thông báo nền, tin liên phiên, lời nhắc
lịch, tóm tắt nén ngữ cảnh, tin kênh Telegram KHÔNG tính) · HOẶC lời mới nhất của founder đến từ Telegram.
Quá 8 tiếng **không** có nghĩa là đã về. Kênh inbox do dự án khai ở `<dự án>/.claude/afk-inbox.txt`
(C-HX: `python3 scripts/sep-viec/sep_viec.py gui …`); mốc Telegram dự án ghi vào
`~/.claude/afk/moc-telegram-<tên dự án>.json`. Lúc vắng, khối «việc chờ founder quyết» chỉ đường inbox
MỘT lần cho mỗi lô vé, không chặn kết lượt lặp lại.

**Cách hỏi:**

- Gom **MỌI** câu cần founder quyết thành **MỘT danh sách** đánh số `1.`, `2.`, `3.`…; mỗi lựa chọn mang
  mã `1A · 1B · 1C` để founder gõ «1B, 2A» là xong. Lựa chọn khuyến nghị đặt **ĐẦU**, ghi **«(đề xuất)»**
  kèm lý do một dòng. Luôn có lựa chọn **«Tự quyết đi»**.
- Gửi **MỘT tin** vào **INBOX founder**:
  - **ChicHub** → tin riêng anh Thành (chạy `--thu` trước, rồi bỏ `--thu` gửi thật):

    ```bash
    # chưa có thẻ: thay «--loai hoi --ma …» bằng «--loai khong-task --ly-do-khong-task "…"»
    TASK_DEV_URL=https://fulfill.thechic.site node scripts/task-dev.mjs tin --rieng \
      --loai hoi --ma <Task-… của việc> \
      --tieu-de "Câu hỏi chờ anh quyết (đang AFK)" \
      --da-lam $'1. <câu 1>\n1A · <đề xuất> (đề xuất) · 1B · <khác>\n2. …' \
      --xem-o "<link màn hoặc: không có màn — chạy ngầm>" \
      --can-lam "**anh Thành** — trả lời kiểu 1A, 2B (Reply tin này)" --thu
    ```

  - **Dự án khác** → kênh inbox founder của dự án đó; **không có** thì ghi danh sách vào
    `~/.claude/afk/cau-hoi-<dự án>.md` và **nhắc lại đầu tiên** khi founder gõ «tao về rồi».
- ⛔ **KHÔNG CHỜ trả lời.** Câu chưa có lời đáp → chọn **phương án đề xuất / theo quy trình mã đã có**,
  ghi một dòng `CHỐT: <quyết định> — vì <lý do>`, việc khác chạy tiếp. Founder trả lời trong inbox
  thì làm theo câu trả lời (sửa lại chỗ đã chốt khác nếu cần).
- ⛔ Cấm hỏi bằng văn bản trong CLI rồi đứng chờ — cũng là hỏi mà không ai đọc.
- Việc máy không tự làm được, phải anh tự làm tay (bấm hộp quyền macOS, đăng nhập portal, duyệt áp migration…) → ghi bằng `node scripts/viec-tay-anh/viec-tay.mjs them --du-an … --viec … --vi-sao … --cach … --duoc …` (kho ChicHub; sổ chung `~/.claude/viec-tay-anh/danh-sach.md`, tự gửi inbox anh lúc 20:00 và 22:00; đủ 4 ý lời thường: làm gì · vì sao cần chính anh · bấm/gõ gì · xong thì được gì). Cấm hỏi việc đó trên CLI. Lệnh bị cổng chặn lúc anh vắng mà cần anh thì cổng TỰ ghi vào sổ, khỏi ghi tay.

**Chỉ hỏi cái đáng hỏi.** Bộ lọc bốn cửa:

1. Trả lời khác nhau thì **LÀM khác nhau** → đưa vào danh sách. Trả lời sao cũng làm y thế → **không hỏi**.
2. Đụng **thông tin bí mật** (mật khẩu, khoá API, token) → **luôn hỏi**, không bao giờ tự sinh; việc đó
   đứng chờ, việc khác chạy.
3. Đụng **quyết định kinh doanh** (giá, quy trình, ai được làm gì) → **luôn hỏi**; trong lúc chờ đi theo
   quy trình mã đã có, không tự chế quy trình mới.
4. Còn lại → **tự quyết**, và ghi một dòng `CHỐT: <quyết định> — vì <lý do>` vào báo cáo.

**Bộ câu rà qua khi soạn danh sách** (bỏ câu nào không liên quan; câu nào không trả lời thì dùng mặc định):

- Thứ tự ưu tiên giữa các việc mới + việc đang dở, nếu chạm trần 5 worker thì cắt cái nào?
- Có việc nào đụng **dữ liệu thật / máy chủ** không? Nếu có thì được đi tới đâu?
- Deploy tới đâu: chỉ demo, hay **demo rồi prod**? (Mặc định founder đã chốt: **được đi tới prod**.)
- Việc đang chạy mà bị chặn vì thiếu quyết định — quyết luôn, hay xếp vào danh sách chờ?
- Có ràng buộc thời gian nào không (founder về lúc mấy giờ, có deadline nào trong hôm nay)?
- Có gì **cấm đụng** trong hôm nay (thư mục, bảng dữ liệu, dịch vụ đang chạy)?

Gửi xong, ghi lại **danh sách CHỐT tạm** (phương án đang theo cho từng câu) rồi sang GĐ2 ngay.

---

### GĐ2 — Chạy một mạch, KHÔNG xin quyền nữa

Không chờ founder trả lời danh sách GĐ1 — chạy luôn theo danh sách CHỐT tạm. Từ đây tới lúc founder về:
**không hỏi trong CLI câu nào** (cổng chặn `AskUserQuestion`).

- Việc gặp ngã ba mà GĐ1 chưa phủ → **tự quyết theo hướng an toàn nhất / theo quy trình mã đã có**,
  ghi `CHỐT:` kèm lý do; quyết định founder nên biết thì gửi **thêm vào inbox** (khuôn GĐ1) và đẩy vào
  **danh sách chờ quyết của GĐ5** — không dừng luồng.
- Thả **worker nền song song**, trần **5 worker / dự án**. Trần đầy → **xếp hàng**
  (`~/.claude/universal-hooks/worker_queue.py`), con nào xong thì thả con kế.
- ⛔ **TRÙNG VÙNG TỆP thì BẮT BUỘC GỘP hoặc XẾP HÀNG** — bất kể ước lượng phần trăm là bao nhiêu.
  Hai worker cùng ghi một vùng = gãy bản dựng, đã xảy ra thật.
- **Brief BẮT BUỘC mở đầu bằng ba dòng khai vùng** (khuôn cố định, cổng `worker_cap_enforce`
  chặn nếu thiếu dòng `GHI:` — từ 07/09/2026 cổng KHÔNG còn đoán vùng từ văn xuôi):

  ```
  GHI: src/lib/fulfill src/app/api/orders
  ĐỌC: docs/FULFILL_WORKFLOW.md
  TÀI NGUYÊN: db-dev
  ```

  `GHI:` = mọi chỗ worker SẼ GHI (cách nhau bằng khoảng trắng); thuần đọc -> `GHI: -`.
  `ĐỌC:` chỉ để người đọc hiểu, cổng KHÔNG tính là tranh chấp. `TÀI NGUYÊN: -` nếu không giành gì.
- **Brief worker phải TỰ CHỨA** — worker không hỏi lại được vì founder đi vắng. Mỗi brief gồm đủ:

  1. Bối cảnh + việc phải làm, viết bằng **tiếng Việt có dấu**.
  2. **Mốc tiến trình bắt buộc** (`echo 'NN|<nhãn có dấu>' > /tmp/claude-bg-progress/<dự án>/w##-<slug>.progress`).
  3. Thi công → **verify bằng lệnh thật** (bản dựng/kiểm thử/lint, curl, truy vấn dữ liệu) — cấm "chắc là xong".
  4. **Commit local** (`fix(W##): …` / `feat(W##): …`), **KHÔNG tự đẩy lên kho chung** trừ khi GĐ1 đã cho phép.
  5. **Deploy demo → smoke demo** (mở đúng màn hình, chụp ảnh nếu có giao diện).
  6. **Deploy prod → verify prod** (mã bản dựng đã đổi, màn hình thật lên đúng).
  7. **Báo cáo có bằng chứng**: commit · output lệnh · `tệp:dòng` · đường dẫn ảnh · dòng `ĐỂ LẠI:`.
  8. Nhắc luật an toàn dữ liệu ở GĐ3 — **chép vào brief, đừng chỉ trỏ tới**.

---

### GĐ3 — LUẬT AN TOÀN DỮ LIỆU (CỨNG, KHÔNG CÓ NGOẠI LỆ)

Founder: _"cứ chạy, không được phá vào data gốc để hỏng dự án hay server của tao"_ ·
_"miễn đéo xóa data của tao là được. và nhỡ làm gì thì phải có backup."_

**Cấm tuyệt đối khi đang ở chế độ AFK:**

- Lệnh xoá bảng / xoá sạch bảng / xoá dòng (`DROP`, `TRUNCATE`, `DELETE FROM`) trên dữ liệu thật.
- Lệnh xoá đệ quy cưỡng bức lên thư mục dự án, thư mục dữ liệu, hoặc bất kỳ thư mục nào trên máy chủ.
- Thao tác git khó đảo ngược trên nhánh chung: đặt lại cứng, đẩy cưỡng bức, xoá nhánh, dọn cưỡng bức.
- Đụng thư mục **không thuộc quyền mình** trên máy chủ dùng chung (VPS dùng chung với sếp:
  chỉ `/root/chichub*` là của mình, thứ khác không đụng).
- Tắt tính năng bảo mật (giới hạn tần suất, kiểm tra phiên, chặn giả mạo) để "cho nhanh".

**Bắt buộc backup TRƯỚC khi:** chạy `UPDATE` trên dữ liệu thật · chạy chuyển đổi lược đồ (migration) ·
ghi đè tệp cấu hình / tệp quan trọng · thay thế thư mục bản dựng.

Backup phải lưu **HAI NƠI, TRONG CÙNG MỘT LỆNH**:

```bash
# ví dụ mẫu — đổi <nguồn>/<slug> cho đúng việc
TS=$(date +%Y%m%d-%H%M); NG=$(date +%d%m%Y)
mkdir -p /tmp/backup-<slug>-$TS docs/handoff/backup-<slug>-$NG && \
  cp -a <nguồn> /tmp/backup-<slug>-$TS/ && \
  cp -a <nguồn> docs/handoff/backup-<slug>-$NG/ && \
  ls -la /tmp/backup-<slug>-$TS/ docs/handoff/backup-<slug>-$NG/
```

- Nơi 1: `/tmp/` (nhanh, mất khi khởi động lại máy).
- Nơi 2: **thư mục bền trong kho mã**, ví dụ `docs/handoff/backup-<slug>-<ngày>/`.
- Backup xong phải **kiểm lại** (`ls -la` cả hai nơi) rồi mới sửa. Founder: _"địt cụ thằng nào không backup."_

**Luật deploy an toàn (không gián đoạn người đang dùng):**

- Dựng ra thư mục **mới** (`.next-new`) rồi **hoán đổi**; ⛔ **KHÔNG xoá thư mục đang phục vụ**.
- **Backup bản dựng cũ** trước khi hoán đổi.
- ⛔ **CẤM nối `npm run build` vào ống dẫn** (`| tail`, `| head`) — ống dẫn che mất mã thoát, bản dựng
  hỏng vẫn tưởng là xong rồi nạp lại dịch vụ → sập. Phải **bắt mã thoát riêng**:

  ```bash
  npm run build > /tmp/build-<slug>.log 2>&1; RC=$?
  tail -40 /tmp/build-<slug>.log
  [ $RC -eq 0 ] || { echo "BẢN DỰNG HỎNG rc=$RC — KHÔNG hoán đổi, giữ nguyên bản cũ"; exit 1; }
  ```

- Đổi lược đồ dữ liệu → **sinh mã máy khách trước khi dựng**, thiếu bước này là dịch vụ chết.
- Kiểm dung lượng đĩa trước khi dựng — hết chỗ giữa chừng cũng làm hỏng bản dựng.

---

### GĐ4 — CANH WORKER, CẤM ĐỂ TREO ("ngáo chó")

Founder: _"thả worker chờ hợp lý không được đợi hay là ngáo chó để worker chờ lâu không ai động vào
mà cũng không biết tại sao."_

**Mỗi lần được đánh thức** (worker báo xong, hoặc có thông báo tác vụ):

1. Đọc lại **toàn bộ** mốc tiến trình, so với lần đọc trước:

   ```bash
   bash ~/.claude/universal-hooks/bg-progress.sh
   for f in /tmp/claude-bg-progress/*/*.progress; do printf '%s  %s  ' "$(date -r "$f" '+%H:%M')" "$f"; cat "$f"; done
   ```

2. Đối chiếu với `ListAgents`.

**Luật xử lý bốn tình huống:**

| Tình huống | Dấu hiệu | Xử lý |
|---|---|---|
| **Nghi treo** | mốc **không nhích quá 20 phút** VÀ nhãn không đổi VÀ không gọi công cụ nào | đọc log/output của nó; còn sống thì để chạy tiếp và ghi nhận; **chết thật** → `TaskStop`, **thả worker mới** làm nốt phần dở (brief ghi rõ đã tới đâu), **ghi lý do vào báo cáo**. ⛔ CẤM chờ vô hạn. |
| **Xác treo** | đã trả báo cáo cuối, im **quá 5 phút** | `TaskStop` **ngay**. ⛔ CẤM tắt worker vừa gọi lệnh trong 5 phút gần đây. |
| **Bị chặn vì thiếu quyết định founder** | worker hỏi ngược mà founder vắng | ⛔ **KHÔNG chặn cả luồng**: ghi câu hỏi vào **danh sách chờ quyết (GĐ5)**, đóng việc đó ở trạng thái "chờ quyết", **thả việc khác chạy tiếp**. |
| **Chờ tài nguyên dùng chung** (deploy) | hai worker cùng muốn deploy | dùng **đúng một dòng** khoá, ⛔ cấm tự dựng vòng lặp `until … sleep`, ⛔ cấm dò chữ trong output — chỉ xét **mã thoát** (0 = đã cầm khoá · 75 = hết giờ chờ · 2 = sai cú pháp): |

```bash
W=~/.claude/universal-hooks/wlock.sh; ME=<slug worker>
bash $W wait deploy --owner=$ME --pid=$$ --timeout=900 || exit 75
trap 'bash '"$W"' release deploy --owner='"$ME"' >/dev/null' EXIT INT TERM
```

- **Việc mới LUÔN thả worker mới.** ⛔ Không "đánh thức lại" worker đã báo xong.
- Worker báo xong → `TaskStop` để nó rời bảng, khỏi làm nhiễu số đếm.

---

### GĐ5 — BẢN TỔNG KẾT KHI FOUNDER VỀ

⛔ **Chỉ được chốt khi hội đủ BA điều** (thiếu một điều là chưa được viết tổng kết):

1. **Không còn worker nào chạy thật** (xác treo không tính, nhưng phải `TaskStop` cho sạch).
2. **Hàng chờ rỗng** — không còn vé chưa thả (vé diện _chờ founder quyết_ thì gom vào mục 2 dưới đây).
3. **Đã deploy CẢ demo LẪN prod** cho mọi việc đã hoàn thành (trừ việc GĐ1 đã chốt là không lên prod).

Kiểm lại **ngay trước khi viết**, không dùng ảnh chụp cũ.

**Nội dung bản tổng kết — bốn mục, đủ cả bốn:**

**1. Bảng việc**

| Mã | Việc | Trạng thái | Commit | Demo | Prod | Bằng chứng |
|---|---|---|---|---|---|---|
| W## | … | xong / bỏ dở / chờ quyết | `abc1234` | có / không | có / không | `tệp:dòng`, output lệnh, mã đơn, đường dẫn ảnh |

- Việc **bỏ dở** phải ghi **lý do đúng thực tế** + dừng ở mấy % + nhãn cuối cùng.
- ⛔ Cấm ghi "xong" mà không có bằng chứng chạy được.

**1b. ĐÃ TỰ Ý LÀM** (chốt 11/10/2026: _"khi tao afk mà mày tự quyết thì chạy xong phải báo cáo là đã tự ý làm gì"_) — liệt kê MỌI `CHỐT:` đã tự quyết lúc vắng, mỗi dòng: **việc · đã làm gì · vì sao · đụng tới đâu · lệnh gỡ**. Từng dòng đã gửi inbox ngay lúc làm xong (gắn thẻ việc), ở đây chỉ gom lại để founder đọc một lượt rồi báo giữ/gỡ.

**2. DANH SÁCH CÂU CẦN FOUNDER QUYẾT** ← đây là thứ founder mở ra đọc đầu tiên

Đánh số `1.`, `2.`, `3.`… Mỗi câu gồm:

- **Bối cảnh một dòng** — vì sao lại vướng.
- **Các lựa chọn** kèm hệ quả ngắn, đánh dấu cái mình nghiêng về.
- **Việc nào đang bị chặn** vì câu này.

Không có câu nào thì ghi thẳng `Không có câu nào cần quyết.` — ⛔ cấm để mục trống lửng lơ.

**3. Danh sách backup đã tạo** — ghi **đủ đường dẫn CẢ HAI nơi** cho từng backup.

**4. Tiến trình nền** — **PID đã dựng** và **PID đã tắt**. Báo cáo thiếu mục này = chưa xong việc.
Dọn nốt rác mồ côi: `bash ~/.claude/universal-hooks/stale-server-reaper.sh`.

---

## Quy ước bắt buộc trong suốt chế độ AFK

- **Tiếng Việt có dấu** trong mọi tin nhắn, nhãn mốc tiến trình, tài liệu, thông điệp commit.
- **Gọi đơn hàng theo MÃ** `{mã_shop}-{mã_đơn_Etsy}` (ví dụ `A67-4157637443`).
  ⛔ Cấm dùng mã nội bộ trong báo cáo/tin nhắn — mã nội bộ chỉ được nằm trong câu truy vấn và đường dẫn.
- ⛔ **KHÔNG BAO GIỜ xin lỗi** — có lỗi thì đưa giải pháp ngay.
- Mọi khẳng định kiểm được bằng một lệnh → **chạy lệnh rồi mới nói**. Cấm đoán từ trí nhớ.

## Khi founder quay lại

Founder gõ "tao về rồi" / "tao ngồi máy rồi" / "tắt afk" → cờ AFK tắt (hỏi `AskUserQuestion` được lại),
in ngay **bản tổng kết GĐ5** (nếu chưa in), đọc lại **danh sách câu cần quyết** — kể cả câu đã gửi inbox
mà founder chưa trả lời, và tệp `~/.claude/afk/cau-hoi-<dự án>.md` nếu có — rồi chờ founder trả lời.
Không tự ý chạy tiếp việc mới.
