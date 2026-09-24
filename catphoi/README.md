# Xếp phôi tôn (catphoi)

Công cụ **xếp phôi tôn tự động** từ file DXF bẩn của bản vẽ tàu, chạy **100% trong trình duyệt**.
Không đăng nhập, không thu tiền, **file DXF không bao giờ gửi lên server nào**.
Chỉ riêng **kho tôn thừa** (kích thước tấm còn dư) là dữ liệu chung của xưởng, lưu trên Cloudflare D1.

🔗 **https://catphoi.jst4.fun**

---

## Dùng trong 3 bước

1. **Kéo file `.dxf`** (AutoCAD: *Save As → DXF*) vào ô trên cùng.
   Tool tự lọc các đường khép kín thành chi tiết, bỏ hết chữ, mũi tên chú thích và block rác.
2. **Chỉnh thông số nếu cần** (tấm, khe, lề, bước xoay, số lượng từng chi tiết) rồi bấm **XẾP**.
   Xem tiến độ; bấm **DỪNG** bất kỳ lúc nào để lấy phương án tốt nhất đang có.
3. **Tải về**: `Tải DXF tấm này` cho từng tấm, hoặc `Tải tất cả DXF (.zip)`, rồi nạp vào **FastCAM** như quy trình cũ.
   Có thêm **G-code tham khảo** (`.nc/.txt/.cnc`) nếu muốn nạp thẳng vào máy.

---

## Kết quả thực đo trên file mẫu `Gửi Sơn.dxf` (8,6 MB, AC1021)

| Hạng mục | Kết quả |
|---|---|
| Đọc file + nhận diện | **15/15 chi tiết**, tổng **13,9683 m²** — đúng bảng trong đề bài |
| Thời gian parse | **5–12 ms** (chạy trong Web Worker, UI không đơ) |
| Chi tiết bị loại | 43 MTEXT, 1 TEXT, 2 INSERT, 2 VIEWPORT, 40 LINE mũi tên hở, 2.392 block rác |
| Số tấm 2000×6000 | **3 tấm** (51,0% + 55,3% + 10,1%) — tổng sử dụng tôn **38,8%** |
| Thời gian xếp | 56 s (ngân sách mặc định 60 s), **779 phương án** đã thử |
| Kiểm tra tự động | Không chồng lấn · khoảng cách ≥ khe 10 mm · nằm trong tấm trừ lề 10 mm · đủ 15/15 |

### ⚠️ Về mục tiêu "2 tấm" trong đề bài — KHÔNG đạt, và đây là lý do

Đề bài đặt mục tiêu xếp 15 chi tiết vào **2 tấm**. Con số đó xuất phát từ diện tích
(13,97 m² / 12 m² mỗi tấm → "tối thiểu 2 tấm"), nhưng **hình dạng không cho phép**:

- 10 trong 15 chi tiết là **thanh sườn cong hình lưỡi liềm**: dày khoảng 250 mm,
  dài 3.398–5.253 mm, độ võng 345–914 mm. Chúng chỉ tiết kiệm tôn khi **xếp lồng vào nhau**
  (cùng chiều cong, chồng lên nhau theo bước ~260–300 mm).
- Đo thực tế bằng chính tool: **một tấm 2000×6000 chỉ chứa được tối đa 5 thanh sườn**.
  (Thử riêng 10 thanh sườn, không có 5 miếng chữ nhật → vẫn ra **3 tấm**: 5 + 4 + 1.)
- Bề rộng một chồng lồng nhau ≈ (độ võng của thanh ngoài cùng) + (số thanh × ~260 mm).
  Thanh P0 võng 914 mm nên tấm chứa nó chỉ còn chỗ cho 4 thanh nữa là hết 2.000 mm bề rộng.
- Xếp toàn bộ 15 chi tiết lên **một tấm dài vô hạn** (2000 × 24000) cho ra chiều dài cần
  **12.890 mm** ở hiệu suất 54,2%. Hai tấm 6.000 mm chỉ có 12.000 mm, lại còn bị cắt đứt ở
  mép tấm nên không xếp được thanh vắt qua ranh giới.

**Kết luận trung thực: với khe 10 mm, lề 10 mm và KHÔNG lật gương, bộ chi tiết này cần 3 tấm.**
Tool đã tối ưu để **tấm thứ 3 chỉ chứa 1 chi tiết** (11,3%), phần tôn còn lại giữ nguyên khổ để
dùng cho lô sau. Nếu bật **Lật gương** hoặc giảm khe/lề, kết quả có thể khác — hãy thử trên UI.

---

## Giới hạn (cố ý)

- **Không đọc `.dwg`.** Hãy *Save As → DXF* trong AutoCAD. Thả file `.dwg` vào sẽ báo đúng câu này.
- **G-code chỉ là tham khảo.** Chưa có file G-code mẫu của máy → dùng dialect phổ thông
  (`G21/G90/G00/M07/G01/M08/M30`), mọi mã đều sửa được trong `⚙ Cài đặt G-code`.
  **Chạy thử không tải trước khi cắt thật.** Đường chính vẫn nên là DXF → FastCAM.
- **Bù kerf: MẶC ĐỊNH TẮT (ô "Bù kerf (mm)" = 0).** Để 0 thì file xuất ra y hệt như trước,
  bù kerf vẫn làm trên máy hoặc trong FastCAM như quy trình hiện tại.
  Đặt > 0 thì tool tự bù ngay trong file: đường bao ngoài nở ra `kerf/2`, lỗ thu vào `kerf/2`
  (lỗ phải cắt nhỏ lại thì lỗ thành phẩm mới đúng cỡ), áp cho **cả DXF lẫn G-code**, và khe
  xếp giữa 2 chi tiết tự cộng thêm `kerf` để hai vệt cắt đã nở không chạm nhau.
  Khi đó **PHẢI TẮT bù kerf bên FastCAM/máy**, kẻo bù hai lần làm chi tiết hụt —
  dòng cảnh báo vàng trên màn hình và comment đầu file G-code đều nhắc điều này.
- **Không xếp chi tiết nhỏ vào lỗ** của chi tiết khác (lỗ vẫn được giữ và vẫn được cắt).
- Không login, không lịch sử, không tracking. Database chỉ có **một bảng duy nhất** cho kho tôn thừa.
- Không bóc tách/khai triển chi tiết từ bản vẽ tàu (khâu đó nằm ngoài phạm vi).
- **Kho tôn thừa nay ĐÃ CÓ** (xem mục riêng bên dưới) — đây là chỗ duy nhất của tool có máy chủ.

### Tên chi tiết tự đặt · kích thước hiển thị · nhãn

- **Kích thước trong danh sách chi tiết là `dài × bề rộng nhỏ nhất khi xoay`** (khung bao nhỏ nhất
  xoay được — minimum-width bounding rectangle, tính bằng rotating calipers trên bao lồi).
  Trước đây tool hiện khung bao theo trục toạ độ gốc nên ra số vô nghĩa với thanh sườn cong nằm chéo:
  P0 hiện `3409×3996` trong khi thanh thật là `5253×1172`. Sai số so với bảng mục 4 của
  PROBLEM_STATEMENT: chiều dài ≤ 0,04%; bề rộng luôn nhỏ hơn hoặc bằng bảng, lệch nhiều nhất là
  P6 (652 so với 666 = −2,04%) — vì bảng gốc đo bằng cách quét xoay từng 1°, còn rotating calipers
  cho đúng giá trị nhỏ nhất.
- **Nhãn nằm trong hình.** Điểm đặt nhãn dùng *pole of inaccessibility* (thuật toán polylabel),
  không dùng trọng tâm: trọng tâm/tâm khung bao của thanh sườn cong chữ S rơi **ra ngoài** hình
  (10/15 chi tiết của file mẫu bị như vậy), làm nhãn bay ra khoảng trống giữa hai chi tiết.
- **Tự đặt tên chi tiết.** Mỗi dòng trong danh sách có ô nhập tên (bỏ trống thì vẫn là `P0`…`P14`).
  Tên hiện trên preview, ghi vào layer `LABEL` của DXF và vào comment `(CHI TIET …)` của G-code.
  Tên được nhớ lại cho lần mở sau, lưu trong `localStorage` theo **tên file + mã chi tiết**
  (khoá `catphoi.names.v1`, bọc `try/catch` nên chế độ riêng tư cũng không làm hỏng app).
- **Dấu tiếng Việt**: UI hiển thị đủ dấu, nhưng **DXF R12 và G-code là định dạng ASCII**, nên khi
  ghi vào file tên được **chuyển sang không dấu** (`Sườn 15 mạn trái` → `Suon 15 man trai`) để
  AutoCAD 2007 / FastCAM / máy cắt không hiện ký tự rác.
- Panel **kho tôn thừa** cắm vào `<div id="remnant-slot">` ở cột trái, ngay dưới khối THÔNG SỐ.
  `src/ui/app.ts` export `getNestOptions()` (và treo luôn lên `window`) để panel đọc được đúng
  thông số đang gõ trên màn hình, kể cả `kerf` và `effectiveGap`.

---

## Kho tôn thừa (chạy trên Cloudflare D1)

Panel **KHO TÔN THỪA** nằm ở cột trái, ngay dưới khối THÔNG SỐ.

**Dùng thế nào**

1. Cắt xong một tấm còn dư → bấm **+ Lưu tấm thừa**, đặt **tên bắt buộc** (ví dụ `thừa lô sườn 15`),
   nhập rộng × dài, chọn hình dạng phần còn lại: *chữ nhật nguyên*, *vát một góc*, hoặc *tự nhập đỉnh*
   (mỗi dòng một đỉnh `x y`, mm, gốc ở góc dưới-trái).
2. Lô sau: **tích chọn** những tấm thừa muốn xài rồi bấm **XẾP**.
   Tool nhét chi tiết vào **tôn thừa trước**, hết chỗ mới mở tấm mới nguyên khổ 2×6 m.
   Tấm lấy từ kho hiện trên preview với tiêu đề `Tấm N — TÔN THỪA "<tên>"`.
3. Xài hết tấm nào thì bấm **Đã dùng** để nó không hiện ra nữa (bấm **Còn** để trả lại).

**Kho là dữ liệu CHUNG của cả xưởng.** Mọi máy mở `catphoi.jst4.fun` đều thấy cùng một kho.
Dữ liệu nằm trong Cloudflare **D1** (`catphoi-db`, bảng `remnants`), API là Cloudflare
**Pages Functions** ở `functions/api/remnants/`. Đây là **ngoại lệ duy nhất** của lời hứa
"không có backend" — **bản vẽ DXF vẫn không bao giờ rời khỏi máy bạn**, chỉ có kích thước và
hình dạng tấm thừa được gửi lên.

**Hạn chế phải biết trước khi tin nó**

- **Chỉ dùng được hình chữ nhật lớn nhất nội tiếp trong tấm thừa.** Engine xếp chỉ nhận một khổ
  chữ nhật và không có khái niệm "vùng cấm", nên phần lồi lõm ngoài hình chữ nhật đó **bị bỏ không**.
  Panel ghi rõ `phần xếp được W×L mm` cho tấm bị vát góc — nhìn số đó để biết thực sự xài được bao nhiêu.
- **Không đăng nhập, không phân quyền.** Ai mở link cũng sửa/xoá được tấm thừa của người khác.
  Founder đã chốt như vậy cho MVP (xưởng nhỏ, mọi người biết nhau).
- **Tool không tự trừ kho sau khi xếp.** Xếp xong vẫn phải tự bấm **Đã dùng**.
- **Tool không tự sinh tấm thừa mới** từ phần dư của tấm vừa cắt — phải tự đo và nhập tay.
- **Mất mạng vẫn dùng được**: danh sách đọc từ bản lưu trong máy (`localStorage`), thêm/sửa/xoá
  được xếp vào hàng chờ và tự gửi lên khi có mạng lại. Panel hiện chữ vàng *"chờ gửi lên"*.
  Đổi lại: lúc mất mạng, máy này **không thấy** tấm thừa máy khác vừa thêm.
- **Nút DỪNG ở đường có tôn thừa**: lượt xếp chạy trong Web Worker nên giao diện không đơ; bấm DỪNG
  sẽ lấy phương án tốt nhất đã xếp được đến thời điểm đó (đã xong tấm thừa nào thì giữ tấm đó).
  Bấm quá sớm, khi chưa có tấm nào xong, thì tool báo "chưa có phương án nào".

---

## Assumption Log (giả định đang dùng · rủi ro nếu sai · cách phát hiện)

| Giả định | Rủi ro nếu sai | Cách phát hiện / xử lý |
|---|---|---|
| Đơn vị file là **mm** (`$INSUNITS` của file mẫu = 0, không xác định) | Chi tiết to/nhỏ gấp 10–1000 lần | Tool cảnh báo khi mọi chi tiết đều to hơn tấm hoặc quá nhỏ; đổi ô **Đơn vị file** (mm/cm/m) |
| Mỗi hình trong file cắt **1 cái** | Thiếu chi tiết mạn đối xứng | Sửa ô **SL** của từng chi tiết trên UI |
| **Không lật gương** (sườn mạn trái/phải là 2 chi tiết khác nhau) | Có thể phí tôn hơn một chút | Bật checkbox **Lật gương** |
| **FastCAM đọc được DXF R12** (AC1009) | Không mở được file | Kiểm tra ở DoD mức 2 với FastCAM thật; dự phòng: xuất thêm bản R2000 LWPOLYLINE |
| **M07/M08** là mã bật/tắt mỏ | G-code chạy sai | Sửa trong `⚙ Cài đặt G-code`; đường chính vẫn là DXF qua FastCAM |
| Không cần bù kerf trong tool | Chi tiết hụt kích thước | FastCAM/máy bù kerf như quy trình hiện tại |
| **Bỏ qua layer** khi nhận diện chi tiết | Nhận nhầm đường không phải chi tiết | Mọi đường khép kín đều thành chi tiết; bỏ chọn thủ công trên UI |
| **Trừ 2 layer `SHEET` và `LABEL`** — đây là quy ước riêng của tool | Bản vẽ khách dùng đúng 2 tên layer này sẽ bị bỏ sót | Cần thiết để đọc lại được file do chính tool xuất ra (nếu không, cả tấm bị hiểu là 1 chi tiết còn 15 chi tiết thật thành 15 cái lỗ) |
| Chi tiết được coi là **đặc** khi xếp (bỏ qua lỗ) | Phí tôn ở chi tiết có lỗ to | Nằm ngoài phạm vi MVP theo đề bài |
| Bước xoay mặc định **5°** là đủ cho thanh sườn cong | Có thể phí thêm vài % | Đổi sang 1°/2° trên UI (chậm hơn) |

---

## Ghi chú kỹ thuật — vì sao **không** dùng NFP/Minkowski

Đề bài khuyến nghị port lõi SVGnest (NFP qua Minkowski + GA). **Đã đổi sang nesting bằng bitmap**, lý do:

- Bước xoay mặc định 5° → **72 góc**. NFP phải dựng và cache no-fit polygon cho **từng cặp
  (chi tiết × góc)** → 72² tổ hợp mỗi cặp chi tiết. Đây đúng là chỗ Deepnest nổ tổ hợp và treo.
- Bitmap xử lý **góc bất kỳ** và **hình lõm** (điều bắt buộc để các thanh sườn cong lồng vào nhau)
  với chi phí ổn định, không phụ thuộc số đỉnh.

Bảo đảm không chồng lấn là **bảo đảm toán học**, không phải "gần đúng":

1. Raster hoá **bảo toàn**: ô lưới được bật nếu ô đó **giao** với đa giác (đi theo cạnh bằng
   thuật toán Amanatides–Woo + tô trong bằng scanline) ⇒ tập ô luôn **chứa trọn** hình thật.
2. **Nở** thêm `m = ceil((khe/2) / cạnh_ô)` ô theo hình vuông ⇒ tập ô chứa `hình ⊕ đĩa(khe/2)`.
3. Hai bitmap đã nở không chồng nhau ⇒ **khoảng cách 2 hình thật ≥ khe**.
4. Vùng đặt được của lưới quy đổi đúng bằng "hình gốc nằm trong tấm trừ lề".

Raster dùng **hình gốc đầy đủ đỉnh** (không dùng hình đã đơn giản hoá) — hình đơn giản hoá
có thể hụt vào trong tới 1 mm và làm chi tiết lọt ra ngoài lề.

Tìm kiếm: **thuật toán di truyền nhẹ** (quần thể 12, lai ghép order-crossover, đột biến đổi
thứ tự + đổi góc) với các cá thể khởi đầu có chủ đích: *to trước*, *dài trước*, *bbox lớn trước*,
*bề rộng nhỏ trước*, và **thứ tự xen kẽ** (tách các đường cong cùng họ thành 2 nhóm lồng khít).
Hàm mục tiêu ưu tiên tuyệt đối **ít tấm nhất**, sau đó **dồn cho tấm cuối càng ít càng tốt**.

Đặt chi tiết: quét bitmap theo 2 luật, GA tự chọn luật nào tốt hơn:
- *Luật 0* — tìm chỗ **không làm tấm dài thêm**, ưu tiên sát mép trái; cho phép chi tiết **trượt dọc**
  để lồng vào chỗ lõm của chi tiết bên cạnh (đây là cơ chế làm các thanh sườn ôm nhau).
- *Luật 1* — bottom-left cổ điển.

---

## Chạy trên máy

```bash
cd catphoi
pnpm install          # BẮT BUỘC pnpm, không dùng npm
pnpm dev              # http://localhost:5173
pnpm build            # kiểm kiểu + build production vào dist/
pnpm test             # chạy toàn bộ test
```

### Fixture để test

Bộ test đọc `catphoi/fixtures/gui-son.dxf`. **File này KHÔNG được commit lên repo**
(bản vẽ tàu thật của khách — xem `.gitignore`, chặn mọi `*.dxf`).

Chép file vào trước khi chạy test:

```bash
cp "Gửi Sơn.dxf" catphoi/fixtures/gui-son.dxf
```

Thiếu fixture thì các test liên quan **tự bỏ qua** và in cảnh báo rõ ràng, không báo đỏ giả.

### Các test có gì

| File | Kiểm cái gì |
|---|---|
| `tests/parse.test.ts` | 15 chi tiết · 13,97 m² ±0,5% · loại đúng 40 LINE hở và chữ · parse ≤ 10 s · đổi đơn vị · file rỗng · **kích thước 15 chi tiết khớp bảng mục 4** · điểm đặt nhãn nằm trong hình (kể cả sau khi xoay/lật) |
| `tests/nest.test.ts` | Đủ 15/15 · không chồng lấn · khoảng cách ≥ khe · trong tấm trừ lề · ≤ 60 s · nút Dừng · đổi khe/lề · chi tiết to hơn tấm |
| `tests/remnant.test.ts` | Kho tôn thừa: kiểm tra dữ liệu nhập · store có đường lui offline + hàng chờ · hình học (diện tích, chữ nhật nội tiếp lớn nhất) · xếp thật vào tấm thừa (kể cả tấm vát góc) không lọt ra ngoài tôn · không chọn tấm thừa thì xếp y như cũ |
| `tests/export.test.ts` | DXF R12 đủ layer · **round-trip** đọc lại đúng 15 chi tiết sai số ≤ 0,01 mm · 1 file nhiều tấm · tên file · G-code đúng 1 cặp bật/tắt mỏ mỗi vòng, mọi toạ độ trong tấm · đổi được mã mỏ/feed/số dòng N · nhãn của cả 15 chi tiết nằm trong hình · tên tự đặt vào DXF/G-code (bỏ dấu) · kerf 2 mm nở bao ngoài đúng 1 mm mỗi phía và thu lỗ đúng 1 mm |

---

## Deploy

Cloudflare Pages (project `catphoi`), direct-upload, domain `catphoi.jst4.fun`.

```bash
pnpm build
# Đẩy cả dist/ lẫn functions/ — thiếu functions thì API kho tôn thừa chết 404.
pnpm exec wrangler pages deploy dist --project-name=catphoi --branch=main --commit-dirty=true
```

**Binding D1 phải có trên môi trường `production` của Pages project**, không chỉ trong
`wrangler.toml`. Kiểm bằng cách gọi API thật:

```bash
curl https://catphoi.jst4.fun/api/remnants        # phải trả {"ok":true,"remnants":[...]}
```

Tạo bảng lần đầu:

```bash
pnpm exec wrangler d1 execute catphoi-db --remote --file=db/schema.sql
```

---

## Cấu trúc mã

```
src/
  types.ts          hợp đồng kiểu dùng chung + applyPlacement() (quy ước biến hình duy nhất)
  core/
    geometry.ts     convex hull, rotating calipers, Douglas-Peucker, point-in-polygon, khoảng cách
    dxf-parse.ts    parser DXF tối giản — NHẢY QUA section BLOCKS (93% dung lượng file mẫu)
    dxf-export.ts   xuất DXF R12 ASCII, layer CUT/SHEET/LABEL
    gcode.ts        sinh G-code, lead-in, thứ tự cắt lỗ-trước-bao-ngoài-sau
  nest/
    raster.ts       raster hoá bảo toàn + nở bitmap
    engine.ts       nest(), packOnce, findSpot, validateLayout
    worker.ts       Web Worker xếp phôi
  ui/
    app.ts          toàn bộ màn hình (vanilla TS, không framework)
    render.ts       vẽ tấm + thumbnail bằng Canvas 2D
    styles.css
  remnant/
    types.ts        kiểu dữ liệu tấm tôn thừa
    validate.ts     kiểm dữ liệu người nhập
    geometry.ts     diện tích đa giác, hình chữ nhật lớn nhất nội tiếp
    store.ts        gọi API + đường lui localStorage/hàng chờ khi mất mạng
    panel.ts        panel KHO TÔN THỪA (tự bơm CSS, tự cắm vào #remnant-slot)
    plan.ts         nestWithRemnants(): nhét tôn thừa trước, hết chỗ mới mở tấm mới
    nest.worker.ts  Web Worker cho lượt xếp có tôn thừa (giữ giao diện không đơ)
    index.ts        cửa vào, treo window.catphoiRemnant
  workers/
    parse.worker.ts Web Worker đọc DXF
  main.ts           nối UI với worker và các hàm xuất file
functions/
  api/remnants/     Cloudflare Pages Functions: GET/POST/PATCH/DELETE kho tôn thừa
db/
  schema.sql        bảng `remnants` trên Cloudflare D1 (catphoi-db)
wrangler.toml       khai binding D1 tên DB → catphoi-db
```
