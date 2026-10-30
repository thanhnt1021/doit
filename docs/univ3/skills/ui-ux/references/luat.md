# Bộ luật UI/UX cuối — 78 điều (A1–J8)

Hợp nhất 12 sách + phần tra luật của UI UX Pro Max (PM). Mỗi dòng: **luật** — _cách kiểm_ — nguồn.
Viết tắt: **DMMT** Don't Make Me Think (Krug) · **AF** About Face · **DI** Designing Interfaces · **FEW** Information Dashboard Design · **DOET** Design of Everyday Things · **LoUX** Laws of UX · **MI** Microinteractions · **MF** Mobile First · **RUI** Refactoring UI · **RS** Rocket Surgery Made Easy · **WFD** Web Form Design · **DYL** Designing Your Life · **IMP** impeccable (skill thiết kế của Paul Bakaus, github.com/pbakaus/impeccable bản `5e745ac` 29/10/2026, Apache-2.0 — lời viết lại, không chép).

## A. Màn hình và bố cục
- **A1** Việc hằng ngày của một vai xong trên MỘT màn (≤ 1 lần đổi trang); chi tiết + sửa cùng màn, ≤ 3 ô. — _đếm đổi URL trong 1 ca việc_ — DI · AF · DOET · DMMT
- **A2** Dòng dữ liệu đầu: desktop ≤ 400px @1440×900, điện thoại ≤ 600px @390; phần trên bảng ≤ 400 / 200px. — _đo `tbody tr:first` top_ — MF · FEW · DMMT
- **A3** Mỗi màn 1–2 điểm nhấn: 1 nút đặc + 1 số/cảnh báo; ≤ 1 dải thường trực; coi mọi thứ là nhiễu tới khi chứng minh được. — _đếm nút đặc, đếm dải_ — RUI · LoUX · FEW
- **A4** Gọn không mất: ẩn = gập có nút mở rõ, nhớ trạng thái theo người; **cấm xoá trường**; mỗi thứ sống 1 chỗ + link "xem thêm" ở chỗ hay tìm. — _bảng "trường cũ → chỗ mới" đủ 100%_ — AF · DI · WFD
- **A5** Cắt ≥ 50% chữ đầu trang/khối: bỏ câu chào; hướng dẫn đứng cạnh đúng nút, ≤ 1 câu; luật nghiệp vụ vào ⓘ; ≤ 75 ký tự/dòng. — _đếm chữ trước/sau_ — DMMT ch5 · FEW · RUI
- **A6** Nhóm bằng khoảng trắng trước (ngoài nhóm ≥ 2× trong nhóm), viền nhạt sau; không viền lồng viền; bảng bỏ kẻ dọc. — _DevTools_ — RUI · FEW
- **A7** Cùng chức năng cùng chỗ mọi màn; đổi bố cục màn hằng ngày → giữ đường về cũ ≥ 7 ngày + báo người dùng có ảnh. — _so vị trí nút_ — DI · LoUX Jakob
- **A8** Tên trang = chữ vừa bấm (menu, tab, link). — _bảng nhãn menu ↔ tiêu đề, lệch = 0_ — DMMT ch6
- **A9** Mục đang mở (menu, tab) khác ≥ 2 dấu hiệu (nền + đậm / màu + vạch). — _ảnh làm mờ vẫn chỉ ra_ — DMMT · PM
- **A10** Chữ khoá đứng đầu ô/dòng/nút (mã, hạn, đối tác, động từ trước; mô tả sau). — _đọc 3 chữ đầu vẫn hiểu_ — DMMT
- **A11** Ô "Tìm chức năng" dưới logo: ⌘K/Ctrl K hoặc "/" từ mọi trang, gợi ý khi gõ (≤ 8–12 kết quả, nhóm theo menu), nhận có/không dấu + đồng nghĩa Việt/Anh, bấm = nhảy thẳng tới đúng màn/đúng ô (kiểu ô tìm System Settings macOS). — _gõ 10 từ quen → đúng trong top 3_ — DMMT · LoUX Hick/Postel · PM

## B. Bảng và danh sách
- **B1** Một cách xem chi tiết: desktop = bảng + ô phải (hoặc mở dưới dòng); điện thoại = màn riêng + Trước/Sau; không trộn "mở trang" với "mở tại chỗ" trên cùng dòng. — DI · AF · MF
- **B2** Cột gộp có phân cấp: giá trị chính đậm + 1–2 dòng phụ 11–12px xám; số căn phải, chữ số đều cột (tabular). — RUI · LoUX Miller
- **B3** Trạng thái việc đọc được từ dòng: trễ/kẹt/lỗi = màu + icon trên dòng; dòng bình thường hạ tông. — AF · FEW
- **B4** Nút hành động hiện khi rê chuột (không xô bố cục) + có đường chạm trên điện thoại; việc > 10 lần/ngày không giấu sau ⋯. — DI · MF · MI
- **B5** Phím tắt việc lặp: J/K đi dòng, Enter mở/áp, Y/N duyệt, Esc thoát; chọn nhiều = ô tick + thanh "Đã chọn N · …"; nút vẫn lộ. — DI · AF · MI
- **B6** Lọc áp ngay, nằm trong URL, nhớ theo người; 1 hàng; dòng "Đang lọc" xoá từng chip. — _tải lại vẫn giữ lọc_ — DI · LoUX Hick
- **B7** Phân trang (không cuộn vô tận); không cuộn ngang chữ; chữ cắt có đường xem đủ; nhãn trạng thái 1 dòng. — _`scrollWidth ≤ clientWidth`_ — AF · DI · PM
- **B8** Lựa chọn ≤ 6 → chip bấm 1 lần; hộp thả chỉ cho danh sách ≥ 10 tên đã biết, có tìm; nhãn trong ô lọc không bị cắt cụt. — DMMT · PM
- **B9** Ô Search 1 ô, chữ "Search" nhìn thấy, nhận mọi dạng (mã có/không tiền tố, mã vận đơn, SKU, tên). — _thử 4 dạng cùng 1 bản ghi_ — DMMT · LoUX Postel
- **B10** Bảng sắp xếp báo đang sắp theo cột nào (`aria-sort`); dòng chữ thuần 36–40px, dòng có ảnh 56–72px; bảng đối soát có "Tải CSV". — PM · FEW

## C. Nút và hành động
- **C1** Nhãn nút = động từ + đối tượng (+ số): "Gửi 3 đơn cho X"; cấm OK/Submit; tên quen người dùng, không tên nội bộ. — DI · MI · DMMT
- **C2** 1 nút đặc/màn; phụ = viền; hiếm = link; nút không dùng được thì xám + lý do (không ẩn). — RUI · AF · WFD
- **C3** Hai nút trái nghĩa (Duyệt/Từ chối, Lưu/Huỷ) khác ≥ 2 thuộc tính. — WFD · DOET
- **C4** Không hỏi xác nhận việc có Hoàn tác (≤ 30 giây, nêu đã đổi gì); việc chạm ra ngoài = xem trước ≥ 3 thông tin + hoãn 5 giây có Huỷ. — AF · DI · DOET · MI
- **C5** Bước phụ thuộc chặn bằng nút xám + 1 câu đời thường + nút mở đúng khối cần làm. — DOET · DI · MI
- **C6** Độ lộ theo tần suất: > 10 lần/ngày = lộ 0 click; 1–2 lần/ngày ≤ 2 click; < 1 lần/tuần = menu. — AF · MI · DMMT

## D. Phản hồi, lỗi, chờ
- **D1** Nút đổi trạng thái ≤ 100ms; kết quả/khung chờ ≤ 400ms; > 1s quay + tên bước; > 10s ước lượng + Huỷ. — LoUX Doherty · DOET
- **D2** Phản hồi tại chỗ (dòng vừa đổi sáng lên rồi mờ), không thông báo nổi cho việc < 1 giây. — MI · WFD
- **D3** Lỗi 2 tầng (tóm tắt đầu form + ô lỗi), ≤ 20 chữ, nói cần gì + nút sửa; đỏ chỉ cho lỗi; lỗi API ngoài tự thử lại 2 lần rồi báo kèm "Thử lại / Cách khác". — WFD · MI · PM
- **D4** Thay đổi do máy tự làm có dấu trên dòng + "lần cuối · Đồng bộ ngay". — LoUX · MI
- **D5** Rỗng = 1 câu + 1 nút, ẩn lọc/tab; đang tải = khung giữ chỗ không nhảy bố cục. — RUI · DI · PM
- **D6** Chế độ hiện rõ: chọn nhiều có thanh + Esc; ô người nhập tay khác hẳn ô máy tính. — MI · DOET
- **D7** Nói thẳng: màn có khoá/lỗi/chờ/số chưa chốt ghi vì sao + bước tiếp NGAY trên màn; không phạt kiểu nhập; không hỏi ô không cần. — DMMT ch10/12

## E. Form
- **E1** Ô suy được từ dữ liệu có thì điền sẵn; ≥ 1 mặc định thông minh từ lần trước. — WFD · MI
- **E2** Nhãn trên ô, luôn hiện; placeholder chỉ là ví dụ. — WFD · MF · PM
- **E3** Ô tiền/ngày/mã nhận ≥ 3 định dạng + dán có rác, tự chuẩn hoá. — LoUX Postel · DMMT
- **E4** Kiểm khi rời ô, không khi đang gõ; thiếu ô không bắt buộc vẫn lưu. — WFD · AF · PM
- **E5** ≤ 4 lựa chọn → thẻ chọn với ô phụ hiện ngay dưới; > 4 → hộp thả. — WFD
- **E6** Hộp thoại dài: đầu + chân cố định, thân cuộn, nút chính luôn thấy, cao ≤ 90dvh; bấm → "Đang…" ≤ 100ms; form > 5 ô tự lưu nháp. Form một cột kẹp ~670px + cột hướng dẫn phải; bảng thì giãn đầy. — WFD · DOET
- **E7** Số nhập lệch > 3× trung bình lịch sử → hỏi lại 1 câu nêu số, không chặn. — DOET · MI

## F. Dashboard, số, tiền
- **F1** Dashboard vừa 1 màn 1440×900; góc trên-trái = việc cần làm hôm nay; thêm khối phải bỏ/gập 1 khối. — FEW · DI
- **F2** Mọi KPI kèm ≥ 1 so sánh (cùng kỳ tháng trước tới cùng số ngày / mục tiêu / 7 ngày); số là link sang bảng đã lọc. — FEW · AF
- **F3** Nhiều đơn vị (shop, chi nhánh) cùng một màn: bảng + đường nhỏ 30 ngày cùng trục. — FEW · DI
- **F4** Biểu đồ: so mục tiêu = bullet; xu hướng = đường; so sánh = thanh ngang từ 0; cấm tròn/đồng hồ/radar/3D; nhãn số trực tiếp. — FEW · PM
- **F5** Cảnh báo chỉ khi vượt ngưỡng, ≤ 2 mức; không đèn xanh "OK"; đỏ một nghĩa toàn web; màu luôn kèm chữ/icon. — FEW · LoUX
- **F6** Một kiểu hiện tiền cho mỗi đơn vị toàn web, một helper duy nhất (vd `$2,743.37` · `1.644.580 ₫`). — PM · FEW

## G. Điện thoại
- **G1** Điện thoại = vệ tinh: "việc cần tôi" + 1–2 hành động/thẻ + tìm; việc nặng (bảng 13 cột) có "Mở trên máy tính". — MF · AF
- **G2** Vùng chạm ≥ 44×44, cách ≥ 8px; không thông tin chỉ nằm trong hover (có ⓘ bấm được). — MF · LoUX Fitts · PM
- **G3** Nội dung trước điều hướng: phần đầu ≤ 200px; chip cuộn ngang 1 dòng; cảnh báo = chip dưới header, không dải. — MF
- **G4** Form điện thoại: nhãn trên, bàn phím đúng loại, danh sách > 8 mục = màn chọn riêng có tìm. — MF · WFD

## H. Chữ, màu, khoảng cách (giá trị token ở `docs/DESIGN.md`)
- **H1** Thang chữ 11·12·13·14·16·18·22px, ≤ 4 cỡ/màn, chữ ≥ 11px; zoom 200% không vỡ. — RUI · DI
- **H2** Khoảng cách 4·8·12·16·24·32·48; bảng dày ô 8/12px. — RUI · PM
- **H3** Nền trung tính; ≤ 6 tông trạng thái; tương phản chữ ≥ 4.5:1 cả sáng/tối. — RUI · PM
- **H4** Bóng 3 mức; lớp chồng chỉ từ một thang z-index. — RUI
- **H5** Chế độ tối đẹp ngang chế độ sáng; chụp cả 2 trước khi khai xong. — FEW · PM
- **H6** Icon 1 bộ, 1 nét, không emoji làm icon; nút chỉ icon có tên cho trình đọc màn hình. — AF · PM

## I. Nghiệm thu và cách đi tới quyết định
- **I1** Màn mới/đổi lớn: 1 ca 3 người dùng thật ≤ 50 phút, nói to suy nghĩ, trên bản thật; người làm màn chỉ quan sát. — DMMT ch9 · RS
- **I2** Kịch bản là tình huống, ≤ 5 việc, không chứa tên nút; thử "đây là gì?" trước. — RS · DMMT
- **I3** Sau ca: mỗi người ghi 3 lỗi nặng; bỏ lỗi "lạc 1 nhịp tự quay lại"; sửa ngay lỗi ai xem cũng thấy; không hiểu → bớt trước khi thêm chữ; làm nổi A thì ghi B bị chìm. — DMMT · RS
- **I4** Màn khó: thử ảnh phác thảo 15 phút với 2 người TRƯỚC khi code; form mới: gửi ảnh hỏi "ô này điền gì?". — DMMT · RS
- **I5** Phép thử "cốp xe": ảnh làm mờ vẫn chỉ ra 6 thứ (web · tên trang · khu chính · lựa chọn ở đây · đang ở đâu · tìm) trong ≤ 10 giây. — DMMT ch6
- **I6** Nghiệm thu bằng số: chụp TRƯỚC/SAU 1440 + 390 (điện thoại = Safari iPhone thật), ghi px/dòng/nút/chữ/tương phản lên ảnh. — FEW
- **I7** Câu "A hay B" không chốt bằng sở thích: dựng cả hai, 2–3 người dùng ≤ 15 phút rồi chọn. — DMMT ch8
- **I8** Màn đổi bố cục lớn: ≥ 2 phác thảo KHÁC HẲN nhau (bố cục, không chỉ màu/chữ), mỗi cái tên ≤ 6 chữ + ≤ 3 câu hỏi nó kiểm. — DYL ch4/5
- **I9** Mỗi phác thảo ghi trước ĐÚNG 1 câu hỏi chính; chưa ghi được câu hỏi thì chưa dựng. — DYL ch6
- **I10** Trước ca thử: ≥ 15 phút nghe người dùng kể lại ca làm thật gần nhất (đang làm gì · ở đâu · với ai/máy nào · dùng gì · ai có mặt); cấm mở đầu bằng "thích bản nào". — DYL ch3/6
- **I11** Câu hỏi việc UI viết theo việc người dùng, không chứa sẵn giải pháp; câu gửi người quyết ≤ 5 lựa chọn + 1 đề xuất. — DYL ch6/9
- **I12** Sau ca thử: mỗi lỗi gắn 1 loại — nhầm lặt vặt (bỏ) · tật cố hữu (thiết kế tránh) · cơ hội sửa (vào danh sách). — DYL ch10
- **I13** Thứ ngoài tầm (đối tác không có API, hạn do bên thứ ba đặt) ghi là "trọng lực" trong phiếu, không đưa vào mục tiêu; màn nói thẳng giới hạn (D7). — DYL ch1

## J. Độ hoàn thiện và dấu hiệu «máy dựng đại trà» (học từ IMP 29/10/2026)
- **J1** Chọn kiểu màn theo MÀN: Vận hành · Đọc · Thuyết phục · Trải nghiệm; Vận hành/Đọc → tham vọng = chính xác + kiềm chế, dáng quen là ưu điểm; Thuyết phục/Trải nghiệm → được táo bạo, một chủ ý riêng. — _ghi kiểu màn vào phiếu UI_ — IMP SKILL §Modes · operate.md
- **J2** Cấm dấu hiệu máy dựng: viền màu > 1px một bên thẻ/cảnh báo · chữ gradient · gradient tím–xanh, quầng sáng màu · thẻ lồng thẻ · nhãn nhỏ viết hoa giãn chữ trên tiêu đề · số mục 01/02/03 vô nghĩa · ô icon bo vuông trên mỗi tiêu đề · chấm nhấp nháy không gắn dữ liệu sống · easing nảy · marquee · chữ sáo rỗng. — _`may-soi` dòng «Dấu hiệu kỹ thuật» + nhìn_ — IMP craft-floor.md §Refuse · bộ 62 luật phát hiện
- **J3** Mọi control mới đủ trạng thái: mặc định · rê · focus · đang bấm · vô hiệu (+ lý do) · đang tải · lỗi · thành công. — _bảng trạng thái từng control trong phiếu_ — IMP operate.md §Components · polish.md
- **J4** Lớp nổi (menu thả, tooltip, popover) không nằm trong cha `overflow: hidden/auto`: dùng portal / popover / `position: fixed`. — _mở menu ở dòng cuối của bảng cuộn_ — IMP operate.md · luật clipped-overflow-container
- **J5** Nhịp tiêu đề: khoảng trên tiêu đề > khoảng dưới; bậc h1→h2→h3 không nhảy; tiêu đề `text-wrap: balance`, đoạn văn `text-wrap: pretty`; dòng cao ≥ 1.3 (thân 1.5–1.7). — _`may-soi` nhảy bậc · DevTools_ — IMP luật heading-rhythm · skipped-heading · straggler · tight-leading
- **J6** Chữ phụ trên nền màu pha từ chính màu nền / màu chữ, không dùng xám (xám trên nền màu trông bạc). — _đo tương phản trên ô màu_ — IMP craft-floor.md · luật gray-on-color
- **J7** Rỗng tách 5 ca (lần đầu · tìm không ra · do lọc · không có quyền · tải hỏng), mỗi ca 1 câu đúng ca + 1 bước tiếp; lỗi trả lời: hỏng gì · vì sao (khi biết) · gỡ thế nào; mã lỗi nội bộ không làm câu chính; chờ lâu thì nêu đúng việc đang làm, không bịa thanh tiến độ. — _thử đủ 5 ca rỗng_ — IMP clarify.md
- **J8** Phần trình duyệt tự vẽ cũng là thiết kế: vòng focus, màu bôi chọn chữ, thanh cuộn, gạch chân link, chữ số bảng `tabular-nums` lấy từ DESIGN.md. — _nhìn khi bôi chọn + Tab_ — IMP craft-floor.md §Browser surfaces

**Không dùng** cho web vận hành nội bộ: khuôn landing/bán hàng, "chọn phong cách" màu/font theo ngành của Pro Max, lời chào trang chủ, âm thanh/rung, biểu đồ tròn/đồng hồ/radar, persona đầy đủ + nghiên cứu nặng, wizard cho việc hằng ngày, tự ẩn nút theo thói quen máy đoán; lệnh «bạo hơn / thêm màu / thêm vui / vượt giới hạn» của IMP trên màn Vận hành; tiêm chế độ sửa trực tiếp của IMP vào bản đang chạy thật.
