#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""worker_cap_enforce.py — TRẦN SỐ WORKER ĐỒNG THỜI + ép gửi việc vào worker đang chạy.

BÀI HỌC THẬT (2026-08-25, máy founder — 10 nhân, 16 GB): điều phối thả **11 worker song
song** trên cùng một dự án. Đo được:
  - load average 228–566, có lúc chỉ còn ~63 MB RAM trống, founder không làm việc được;
  - 8 shell nền, trong đó **6 shell là vòng `until ps aux | grep ftp_push; sleep N`** —
    mỗi worker tự dựng một vòng canh riêng cho CÙNG một tài nguyên;
  - 4 `http.server` mồ côi (8484, 8877, 8899, 8911), 264 tiến trình CoreSimulator;
  - hai worker ghi đè CSS của nhau: một con xoá nhầm 1250 dòng rồi khôi phục từ backup,
    cuốn mất thay đổi của con kia; cache-bust lệch nhau -> giao diện vỡ không đồng nhất;
  - hai worker đẩy FTP cùng lúc -> 9 tệp lệch.

Nguyên văn founder: *"mày phải có quy định là như nào tối đa thôi để máy tính của tao còn
làm được việc. lag quá. chưa kịp thì cho hàng chờ. cái nào cùng worker đang xử lý thì mới
add vào worker chứ???"*

WHY hook chứ không thêm dòng markdown: luật "song song hoá" nằm sẵn trong
`rules/AGENTS-ORCH.md` mà vẫn thả 11 con, vì **không ai NHÌN được tổng số worker đang
chạy tại khoảnh khắc bấm spawn** — mỗi lần gọi `Agent` là một quyết định cục bộ. Chỉ hook
`PreToolUse` mới đọc được trạng thái toàn máy đúng lúc đó.

CÁCH ĐẾM (đo thực nghiệm, không đoán):
  Mỗi subagent có một transcript riêng `~/.claude/projects/<project>/<session>/subagents/
  agent-<id>.jsonl`, được GHI THÊM sau mỗi lượt nó làm việc -> mtime của tệp này là nhịp
  tim. Đã kiểm 3 cách khác và loại:
    - `*.meta.json` KHÔNG có trường trạng thái (chỉ agentType/description/toolUseId);
    - đếm số lần `toolUseId` xuất hiện trong transcript cha: KHÔNG phân biệt được
      (con đang chạy 6 lần, con xong từ hôm qua cũng 2–6 lần);
    - tìm `tool_use_id` trong khối kết quả: worker NGẦM trả kết quả "đã thả nền" NGAY lúc
      spawn -> con đang chạy cũng bị coi là xong.
  `session_id` trong payload hook KHÔNG phải id phiên cha khi hook chạy trong subagent
  (đã kiểm bằng các tệp cờ do hook khác để lại) -> phải suy ra dự án từ `cwd`.

NHÁNH THỨ HAI — cấm mỗi worker tự dựng một VÒNG CANH riêng: lệnh Bash dạng
`until/while ... ps|pgrep ... sleep` bị hỏi lại và chỉ sang khoá dùng chung
`wlock.sh`. Chính sáu vòng canh kiểu này đã ngốn 6 shell nền cùng lúc,
lại canh theo TÊN SCRIPT nên worker dùng script tên khác vẫn lọt qua.

LOẠI XÁC TREO RA KHỎI SỐ ĐẾM (thêm 2026-08-25, sau khi founder nổi giận):
  Worker **đã trả báo cáo cuối** vẫn hiện `running` trên khung điều phối và transcript của
  nó vẫn được ghi thêm mỗi khi một thông báo nền chạm vào (nó trả lời "việc đã xong" rồi
  ngủ tiếp) -> nằm gọn trong cửa sổ 15 phút -> **chiếm chỗ trong trần dù không làm gì**.
  Hôm đó `a31808898ec601ae9` ("Sửa giỏ hàng") hiện 1h38m, gửi lại đúng bản báo cáo cũ 4
  lần; `a5f3e7d9d3deb1f7c` 3 lần. Worker mới bị chặn oan.

  DẤU HIỆU TẤT ĐỊNH — `message.stop_reason` (SỬA 28/08/2026, xem "BẢN CŨ SAI" bên dưới):
  harness ghi transcript agent theo TỪNG KHỐI nội dung, mỗi khối một dòng JSONL; chỉ khối
  CUỐI CÙNG của một lượt model mới mang `stop_reason` khác `null`. Đó chính là tuyên bố
  "lượt này đã kết thúc", và với subagent, hết lượt = **đã trả kết quả về cha**. Nên: đọc
  ngược từ đuôi transcript, bỏ nhiễu (`type=="attachment"`, bản ghi user `isMeta` — tức
  SYSTEM NOTIFICATION / Stop hook feedback), rồi xét bản ghi thật đầu tiên gặp:
    - assistant `stop_reason` ∈ {end_turn, stop_sequence} -> ĐÃ TRẢ BÁO CÁO CUỐI (xác treo)
    - user text MỞ ĐẦU bằng "[Request interrupted by user]" -> ĐÃ BỊ DỪNG        (xác treo)
    - còn lại — kể cả assistant `stop_reason == null` — -> ĐANG CHẠY
  Fail-safe: không đọc/không hiểu được -> coi là ĐANG CHẠY (thà đếm dư còn hơn kill oan).

  BẢN CŨ SAI THẾ NÀO (2 lần kill oan trong ngày 28/08/2026): luật cũ là "assistant có khối
  `text` mà không kèm `tool_use` -> đã xong". Nhưng worker VỪA NÓI VỪA LÀM: nó in một câu
  tường thuật (một bản ghi `text`, `stop_reason: null`) rồi mới gọi tool ở bản ghi kế tiếp.
  Hook chụp đúng khe đó -> phán "đã xong" -> điều phối `TaskStop` thật. Hai nạn nhân đo
  được: một con đang cập nhật phiếu, dừng ở câu *"Cuối cùng: cập nhật §7 các bước và §9 thứ
  tự thi công, §11 cửa duyệt."*; một con đang viết tài liệu, dừng ở *"Now the markdown guide
  — rewritten around the MỚI/CŨ split…"*. Cả hai lúc đó im 0–1 phút.

  ĐO TRÊN DỮ LIỆU THẬT (728 transcript agent của dự án EtsyFulfillChichub):
    - phân bố `(khối, stop_reason)`: `(text, end_turn)` 28 · `(text, null)` 158 ·
      `(tool_use, tool_use)` 877 · `(tool_use, null)` 191 · `(thinking, null)` 565
      -> `text` KHÔNG kèm tool xảy ra 158/186 lần GIỮA CHỪNG, chỉ 28 lần là kết lượt thật;
    - replay từng khoảnh khắc (phán "đã xong" mà transcript CÒN bản ghi sau = sai tất định):
      hàm CŨ sai **12.137** khoảnh khắc, hàm MỚI **392** — và 392 ca đó không phải sai:
      377 ca `end_turn` rồi Stop-hook feedback đánh thức worker (đúng định nghĩa xác treo),
      18 ca `stop_sequence` tương tự, 2 ca là brief TRÍCH NGUYÊN VĂN chuỗi "[Request
      interrupted by user]" (đã bịt bằng `startswith`), 1 ca cha gửi việc mới.

  KHÔNG dùng mốc "im ≥ N phút" làm cách nhận diện, kể cả làm lưới phụ: đo 11.536 khe giữa
  một bản ghi `text/null` và bản ghi kế tiếp của CÙNG worker -> p50 1,9 s · p99 98 s, nhưng
  **51 khe > 3 phút, 4 khe > 5 phút, khe dài nhất 15,5 phút** mà worker vẫn chạy tiếp. Mọi
  ngưỡng dưới 15 phút đều giết oan, còn ngưỡng 15 phút thì trùng `ACTIVE_MIN` -> vô nghĩa.
  Khoảng trống duy nhất (worker xong thật mà harness không đóng dấu `stop_reason`) đã có
  nguồn khác bịt: `<task-notification><status>` của harness về tới transcript cha sau
  **0,1–0,2 giây** (đo 5 ca trong phiên 28/8) và `running_workers` đã hỏi nó qua
  `worker_relapse.ids_ket_thuc`.

  Ba hướng khác đã cân nhắc và LOẠI:
    - tệp `.output` của tác vụ: **không tồn tại** (`find ~/.claude/projects -name '*.output*'`
      ra rỗng); `.meta.json` vẫn không có trường trạng thái nào;
    - so mtime transcript với mốc `100|...` trong `/tmp/claude-bg-progress/<dự án>/*.progress`:
      **không có cách nối** slug tệp progress với `agent-<id>` — worker tự đặt tên slug;
    - hạ cửa sổ 15 phút xuống ngắn hơn: sai bản chất — worker build/deploy dài im lặng 20
      phút vẫn đang chạy, mà xác treo lại bị thông báo nền đánh thức nên luôn "mới".

KHÔNG tự kill: xem §"vì sao không tự dọn" trong rules/AGENTS-ORCH.md §LUẬT SỐ 1. Tóm tắt:
  cả phiên chỉ có MỘT tiến trình `claude` (đã đếm `pgrep`: 42 subagent / 1 tiến trình) nên
  hook không có cách giết riêng một worker mà không giết cả phiên; việc kill để coordinator
  làm bằng `TaskStop` ngay trong lượt nhận báo cáo. Hook chỉ ĐẾM ĐÚNG và NHẮC.

CHẶN (deny) khi: số worker ĐANG THỰC SỰ CHẠY của DỰ ÁN NÀY >= trần (mặc định 3).
HỎI (ask) khi: còn chỗ trống nhưng việc mới TRÙNG MẢNG với một worker đang chạy —
  luật founder: trùng mảng thì `SendMessage` vào chính worker đó, không đẻ con mới.
CHO QUA: dưới trần và không trùng mảng · gọi tool khác · có cửa thoát `worker-cap-ok`.

Fail-open tuyệt đối: lỗi bất kỳ -> exit 0.
"""
import glob
import json
import os
import re
import subprocess
import sys
import time
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import worker_queue as WQ          # hàng chờ có lưu bền (worker_queue.py)
except Exception:                       # fail-open: thiếu module thì hook vẫn chạy
    WQ = None
try:
    import worker_relapse as WR        # worker bị dừng giữa chừng -> tự quay lại hàng chờ
except Exception:
    WR = None
try:
    import worker_de_lai as WD         # worker XONG mà tự khai để lại việc -> tự đẻ vé
except Exception:
    WD = None
try:
    import ram_guard as RG             # P147 E: mức bộ nhớ máy (xanh/vàng/đỏ)
except Exception:
    RG = None

AGENT_TOOLS = {"Agent", "Task"}

# vòng canh tài nguyên tự chế: phải có ĐỦ 3 mảnh mới tính (while/until + ps/pgrep + sleep)
VONG_CANH = (re.compile(r"(?<![\w-])(while|until)(?![\w-])"),
             re.compile(r"(?<![\w-])(ps|pgrep|pidof)(?![\w-])"),
             re.compile(r"(?<![\w-])sleep(?![\w-])"))

# 26/08/2026: worker `import-pod-folder` ĐƯỢC CẤP khoá ngay lần đầu, nhưng nó tự bọc
# `acquire` trong `until … sleep 60` rồi DÒ CHỮ tiếng Anh (`acquired|ok|granted`) trong
# output — mà wlock in tiếng Việt "ĐÃ CẤP" -> tưởng trượt -> ngủ 60s -> xin lại ->
# XẾP HÀNG SAU CHÍNH MÌNH, kẹt 15 phút và chặn worker khác. Có `wlock wait` rồi thì
# tự viết vòng lặp quanh wlock là SAI, và dò chữ trong output là CẤM.
VONG_WLOCK = (re.compile(r"(?<![\w-])(while|until)(?![\w-])"),
              re.compile(r"wlock"),
              re.compile(r"(?<![\w-])sleep(?![\w-])"))
RX_DO_CHU = re.compile(r"(grep|=~|case\s)[^\n]{0,80}"
                       r"(acquired|granted|ĐÃ CẤP|DA CAP|đã cấp)", re.I)

# Trần mặc định 3: máy founder 10 nhân / 16 GB, mà mỗi worker còn đẻ thêm build,
# iOS Simulator, http.server... 11 con đã đẩy load lên 566.
MAX_WORKERS = int(os.environ.get("UNIV3_WORKER_MAX", "5"))  # founder chốt 25/8: "tối đa 4-5 — ưu tiên xong nhanh"
# Coi là ĐANG CHẠY nếu transcript được ghi thêm trong bấy nhiêu phút.
# W23 05/09/2026 (lỗi A/Phụ, phiếu P-DEM-DUNG-05092026) — ĐỔI 15 -> 45: ba nơi khai
# biến này (đây · worker_board.py:78 · worker_queue.py:514) từng có BA giá trị khác
# nhau (15/45/45), là nguồn trực tiếp của "cổng nói đủ trần, bảng nói còn chỗ" (§4.1
# phiếu). Chốt theo 45 (không phải 15) vì `khong_ro`/`xac` đã bị LOẠI khỏi đếm trần
# ngay dưới (dòng "xac if (ket or khong_ro or ...)") — nới cửa sổ không làm xác treo
# chiếm trần lâu hơn (đã đo, xem worker_relapse — W20 phản biện Q2), chỉ đỡ oan cho
# worker đang chạy im lâu hợp lệ. Đổi giá trị Ở ĐÂY THÔI; hai nơi kia đã sẵn 45.
ACTIVE_MIN = float(os.environ.get("UNIV3_WORKER_ACTIVE_MIN", "45"))
# W64 04/09/2026 — TRẦN CỨNG cho worker mà HARNESS NÓI LÀ CHƯA KẾT THÚC.
# `ACTIVE_MIN` chỉ còn là đường lui khi KHÔNG đọc được nguồn tất định (xem WHY trong
# `running_workers`). Nhưng "chưa kết thúc" cũng không được phép sống vĩnh viễn: worker
# bị giết cứng, không notification, không báo cáo cuối thì sẽ treo chỗ trong trần và giữ
# khoá vùng mãi mãi. 6 tiếng = gấp ~6 lần lượt im lâu nhất đo được (một lượt `wlock wait
# deploy` ~1 tiếng), đủ rộng để không khai tử oan, đủ hẹp để không treo qua đêm.
SONG_TOI_DA = float(os.environ.get("UNIV3_WORKER_ALIVE_MAX_MIN", "360"))
PROJECTS_ROOT = os.environ.get("UNIV3_PROJECTS_ROOT",
                               os.path.expanduser("~/.claude/projects"))
ESCAPE = "worker-cap-ok"
# CỬA THOÁT CỔNG TRÙNG VÙNG — khai bằng LỆNH:
#     python3 ~/.claude/universal-hooks/cua_thoat.py mo trung-vung "<lý do >= 15 ký tự>"
# 04/09/2026 — VÌ SAO PHẢI CÓ: cổng đọc vùng của worker đang sống bằng máy; máy đo sai
# (W01 chỉ ĐỌC một tệp `~/.claude/...` mà bị tính giữ `tools/univ3`) thì điều phối KHÔNG
# có đường nào nói lại — vé W02 nằm chết 13 phút. `worker_de_trung_vung_gate.py` (cổng
# tầng LỜI NÓI) đã có cửa này từ 28/08, cổng tầng THẢ AGENT thì chưa -> khai vào brief
# vẫn bị chặn, đúng lời founder. Nay hai cổng dùng CHUNG một cờ cửa thoát `trung-vung`.
# 04/09/2026 — CHUYỂN CHỖ KHAI: cửa thoát nay là TỆP CỜ dùng-một-lần (`cua_thoat.py`), KHÔNG
# còn là chuỗi gõ vào `description`/`prompt`. WHY: cùng một chuỗi `khac-vung-that:` dùng chung
# với cổng tầng LỜI NÓI (`worker_de_trung_vung_gate`) -> main quen tay dán thẳng vào câu trả
# lời gửi founder (3 lượt liên tiếp sáng 04/09). Founder không đọc code; ký hiệu hiện ra vừa là
# rác vừa trông như công khai lách luật. Tệp cờ giữ nguyên độ chặt (lý do >= 15 ký tự, dùng một
# lần, hết hạn 15 phút, nhật ký 2 nơi) mà không bắt main viết gì ra màn hình.
TEN_CONG_VUNG = "trung-vung"
try:
    import cua_thoat as CT
except Exception:
    CT = None
NHAT_KY_CUA_THOAT = os.path.expanduser("~/.claude/logs/cua-thoat.log")
# W146 06/09/2026 (phiếu P-GO-KET-DIEU-PHOI-06092026, AC0) — SỔ RIÊNG cho MỌI LẦN cổng
# trùng vùng `deny`, không chỉ lần DÙNG cửa thoát. WHY: `_ghi_cua_thoat` (ngay dưới) là
# hàm ghi DUY NHẤT trước bản vá này, mà nó chỉ chạy khi ai đó MỞ cửa thoát — tức 24 ca
# oan trong sổ cũ là phần bị PHẢN ĐỐI, không phải tử số của một phân số (mẫu số hoàn
# toàn không biết, xem §4C.1 phiếu). Sổ này ghi cả chặn ĐÚNG lẫn chặn OAN, không đổi
# quyết định nào — chỉ đo, để AC9/ngưỡng bỏ cuộc có mẫu số thật sau 3 ngày.
# `UNIV3_LOG_DIR` — LUẬT CA THỬ (W07 07/09/2026): ca thử chạy qua cổng thật PHẢI trỏ mọi
# đường ghi sang sandbox, nếu không nó ĐỐT tài sản thật. Đã xảy ra hai lần trong một buổi:
#   · ca thử nhánh allow đốt mất cờ cửa thoát của main (cờ dùng-một-lần) -> đặt
#     `UNIV3_CUA_THOAT_DIR`.
#   · ca thử nhánh deny đẻ vé rác `fa5a848f74` vào sổ THẬT, chiếm số W05 đúng lúc có
#     worker W05 thật -> đặt `UNIV3_WQUEUE_ROOT` (worker_queue.py:36 đã có sẵn env này).
# Biến thứ ba này để nhật ký chặn cũng không lẫn số đo của ca thử vào sổ thật.
NHAT_KY_CHAN_DO = os.path.join(
    os.path.expanduser(os.environ.get("UNIV3_LOG_DIR", "~/.claude/logs")),
    "cong-trung-vung.log")

# Lời chặn khi brief KHÔNG khai vùng ghi. Tách hằng ra ngoài để ca thử đọc thẳng, khỏi
# phải dựng cả payload hook mới xem được nội dung.
THIEU_KHAI_GHI = (
    "⛔ BRIEF THIẾU DÒNG `GHI:` — CỔNG KHÔNG CÒN ĐOÁN VÙNG TỪ VĂN XUÔI NỮA.\n\n"
    "Founder chốt 07/09/2026 (AskUserQuestion): *\"Bắt brief khai vùng theo khuôn cố định, "
    "cấm đoán hẳn.\"* Brief worker BẮT BUỘC mở đầu bằng khối ba dòng máy đọc được.\n\n"
    "DÁN KHỐI NÀY LÊN ĐẦU BRIEF rồi thả lại (sửa đường dẫn cho đúng việc):\n\n"
    "    GHI: src/lib/fulfill src/app/api/orders\n"
    "    ĐỌC: docs/FULFILL_WORKFLOW.md\n"
    "    TÀI NGUYÊN: db-dev\n\n"
    "  · `GHI:` = MỌI đường dẫn worker SẼ GHI (Edit/Write/`git add`/`>`), cách nhau bằng "
    "khoảng trắng. Việc thuần đọc / chỉ viết báo cáo ra `/tmp` -> `GHI: -`.\n"
    "  · `ĐỌC:` = chỗ chỉ đọc. Cổng KHÔNG BAO GIỜ tính dòng này là tranh chấp — viết thoải "
    "mái cho người đọc hiểu, không sợ bị chặn oan.\n"
    "  · `TÀI NGUYÊN:` = thứ KHÔNG phải tệp mã (db-dev · db-that · dev-3000 · prisma · "
    "build). Không giành gì -> `TÀI NGUYÊN: -`.\n\n"
    "Nhận cả biến thể: `GHI:` · `GHI :` · `VUNG GHI:` · `VÙNG GHI:` · `VÙNG:` · `ZONE:`. "
    "Nhãn `GHI`/`WRITE` phải VIẾT HOA (chữ \"ghi\" thường là động từ trong văn xuôi).\n\n"
    "VÌ SAO CẤM ĐOÁN: 07/09/2026 cổng phải vá BỐN lần trong một buổi vì suy vùng từ câu chữ "
    "(khai giữa dòng · dòng lệnh CHẠY bị tính là GHI · thư mục nhật ký gộp với thư mục hook · "
    "phần VÍ DỤ nhắc tên thư mục worker khác đang giữ). Lần thứ tư chặn oan đúng cái brief đi "
    "vá nó. Khai theo khuôn thì cổng hết chỗ đoán sai."
)


def _ghi_chan_do(desc: str, vung_moi, vung_giu: str, ai: str, nguon: str,
                loai: str = "trung-vung"):
    """Mỗi lần cổng `deny` (kể cả không dùng cửa thoát) đều để lại dấu —
    thiếu sổ này thì không tính nổi tỉ lệ chặn-oan/chặn-đúng (AC0, §4C.1).

    `loai` = BỆNH THẬT của lần chặn. P094 Đ6 (W08 14/09/2026): ba lần chặn 09:57-10:00 là
    "brief thiếu dòng GHI:" nhưng log ghi nhãn `trung-vung` + cột "worker đang giữ (không
    ai)" -> đọc lại thành tranh chấp vùng trong khi chẳng ai giữ gì, hậu kiểm sai bệnh.
    """
    try:
        os.makedirs(os.path.dirname(NHAT_KY_CHAN_DO), exist_ok=True)
        with open(NHAT_KY_CHAN_DO, "a", encoding="utf-8") as fh:
            if loai == "trung-vung":
                fh.write("%s\tCHẶN\t%s\tVIỆC «%s»\tvùng việc mới %s\tvùng bị giữ %s"
                         "\tnguồn suy vùng: %s\tworker đang giữ %s\n"
                         % (time.strftime("%Y-%m-%d %H:%M:%S"), loai, (desc or "")[:60],
                            ",".join(sorted(vung_moi)) or "-", vung_giu, nguon, ai))
            else:
                # Không có tranh chấp nào -> KHÔNG in hai cột vùng/worker-đang-giữ.
                fh.write("%s\tCHẶN\t%s\tVIỆC «%s»\tlý do: %s\n"
                         % (time.strftime("%Y-%m-%d %H:%M:%S"), loai, (desc or "")[:60], nguon))
    except Exception:
        pass


def _ghi_cua_thoat(desc: str, prompt: str, vung, cv: str, ai: str, ly_do: str = ""):
    """Mỗi lần dùng cửa thoát đều để lại dấu — cửa thoát không có nhật ký là cửa mở toang."""
    try:
        os.makedirs(os.path.dirname(NHAT_KY_CUA_THOAT), exist_ok=True)
        with open(NHAT_KY_CUA_THOAT, "a", encoding="utf-8") as fh:
            fh.write("%s\tDÙNG (chi tiết)\ttrung-vung\tVIỆC «%s»\tvùng mới %s\tvùng chung %s"
                     "\tworker giữ %s\tLÝ DO: %s\n"
                     % (time.strftime("%Y-%m-%d %H:%M:%S"), (desc or "")[:60],
                        ",".join(sorted(vung)) or "-", cv, ai,
                        (ly_do or "")[:200].replace("\n", " ")))
    except Exception:
        pass

# từ quá phổ thông, không dùng để đo trùng mảng
STOP = {"fix", "sua", "lam", "cho", "tren", "trong", "voi", "cua", "va", "the", "cai",
        "lai", "them", "bo", "ra", "vao", "moi", "cu", "hai", "lan", "mot", "hai",
        "worker", "rule", "task", "check", "test", "verify", "kiem", "tra", "soat",
        "trang", "web", "app", "code", "file", "tep", "nhom", "toan", "dien", "not"}


def khong_dau(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def tokens(s: str):
    return {t for t in re.split(r"[^a-z0-9]+", khong_dau(s)) if len(t) >= 3 and t not in STOP}


def project_dir(cwd: str):
    """Thư mục ~/.claude/projects/<ma-hoa-duong-dan> ứng với cwd (đi ngược lên cha)."""
    # WHY dùng `re.sub` chứ không phải `replace("/", "-")`: Claude Code đặt tên thư mục
    # transcript bằng cách thay MỌI ký tự không phải chữ/số thành gạch nối, không riêng
    # dấu `/`. Dự án có dấu chấm trong tên (`chiemtinh.jst4.fun`) thì quy tắc cũ dựng ra
    # `...-chiemtinh.jst4.fun` — thư mục KHÔNG tồn tại — rồi vòng lặp leo lên cha
    # `-Users-buddhy-PycharmProjects` (thư mục của dự án KHÁC) => không thấy agent nào,
    # bảng in "❓ mất dấu agent" cho mọi worker và statusLine in RỖNG (ca 09/09/2026).
    p = os.path.abspath(cwd or os.getcwd())
    while True:
        cand = os.path.join(PROJECTS_ROOT, re.sub(r"[^A-Za-z0-9]", "-", p))
        if os.path.isdir(cand):
            return cand
        parent = os.path.dirname(p)
        if parent == p:
            return None
        p = parent


# đọc ngược từ đuôi transcript: đủ để thấy lượt cuối, không nuốt cả tệp 30 MB
TAIL_BYTES = 256 * 1024
TAIL_CAP = 8 * 1024 * 1024
NGAT = "[Request interrupted by user]"

# `stop_reason` mà harness đóng dấu khi MODEL KẾT LƯỢT (đã trả kết quả về cha).
# Cố ý CHỈ liệt kê hai giá trị QUAN SÁT ĐƯỢC trên 728 transcript thật. Giá trị lạ
# (`max_tokens`, `refusal`…) rơi vào nhánh mặc định = ĐANG CHẠY — lệch về phía an toàn:
# đếm dư một xác treo trong ≤15 phút rẻ hơn nhiều so với kill oan worker đang làm.
KET_LUOT = {"end_turn", "stop_sequence"}

# NGƯỠNG "CÒN NHÚC NHÍCH" — bao lâu không gọi lệnh nào thì mới được KHUYÊN tắt.
#
# CA THẬT 29/08/2026 (W11 bị tắt oan): worker đang gửi ảnh cho founder, 02:17:02 nó viết
# một tin TRUNG GIAN ("curl bị chặn đọc file local trong sandbox. Chuyển sang Node fetch."),
# 02:17:32 gọi tiếp `Bash`, 02:17:50 bị `TaskStop`. Cách lệnh cuối đúng 18 GIÂY — không hề
# treo. Máy nhìn tin trung gian tưởng là báo cáo cuối.
#
# ĐO ĐỂ CHỌN SỐ (776 agent của dự án này, 49.344 khoảng nghỉ giữa hai lệnh liên tiếp):
#   p50 = 6 giây · p90 = 25 giây · p95 = 45 giây · p99 = 3,9 phút · p99,5 = 6,2 phút.
#   Số khoảng nghỉ > 5 phút: 362/49.344 = 0,73%.
# -> 5 phút bao 99,27% nhịp làm việc thật. Im QUÁ 5 phút mà không gọi lệnh nào thì gần như
# chắc chắn đã dừng hẳn -> VẪN PHẢI khuyên tắt (xác để lại sẽ gửi lặp báo cáo cũ, 25/8 lặp
# 4 lần một con). Cố ý KHÔNG lấy p99,9 (10 phút): nới gấp đôi chỉ mua thêm 0,5% nhịp thật
# mà xác nằm lại lâu gấp đôi. Cùng số 5 phút `worker_board.NGHI_PHUT` đang dùng để vẽ 💤.
NGUONG_NHUC_NHICH_PHUT = 5.0


def phut_tu_lenh_cuoi(path: str):
    """Số PHÚT kể từ `tool_use` cuối cùng trong transcript worker. None = không thấy lệnh nào.

    Đo cùng nguồn với cột `⚙ <lệnh> Np` của bảng worker: bản ghi assistant có khối
    `tool_use`. CỐ Ý không đòi lệnh phải còn dở (chưa có `tool_result`) — worker vừa chạy
    xong một lệnh và đang nghĩ lệnh kế tiếp vẫn là ĐANG LÀM VIỆC.
    """
    import datetime as _dt
    moc = None
    try:
        for r in _tail_records(path):
            c = (r.get("message") or {}).get("content")
            if not isinstance(c, list):
                continue
            if not any(isinstance(k, dict) and k.get("type") == "tool_use" for k in c):
                continue
            try:
                moc = _dt.datetime.fromisoformat(
                    str(r.get("timestamp") or "").replace("Z", "+00:00")).timestamp()
            except Exception:
                pass
    except Exception:
        return None
    return None if moc is None else max((time.time() - moc) / 60.0, 0.0)


def _tail_records(path: str):
    """Các bản ghi JSONL cuối tệp; nới dần cho tới khi thấy ít nhất một bản ghi assistant."""
    size = os.path.getsize(path)
    chunk = TAIL_BYTES
    while True:
        start = max(0, size - chunk)
        with open(path, "rb") as fh:
            fh.seek(start)
            raw = fh.read()
        lines = raw.split(b"\n")
        if start > 0:
            lines = lines[1:]          # dòng đầu bị cắt giữa chừng
        recs = []
        for ln in lines:
            ln = ln.strip()
            if not ln:
                continue
            try:
                recs.append(json.loads(ln))
            except Exception:
                pass
        if start == 0 or chunk >= TAIL_CAP or any(r.get("type") == "assistant" for r in recs):
            return recs
        chunk *= 4


def da_tra_bao_cao(path: str) -> bool:
    """True = worker ĐÃ TRẢ BÁO CÁO CUỐI (hoặc đã bị dừng) -> xác treo, không tính vào trần.

    Đọc ngược, bỏ nhiễu (attachment · user isMeta = SYSTEM NOTIFICATION / Stop hook feedback),
    xét bản ghi thật đầu tiên và HỎI ĐÚNG MỘT TRƯỜNG: `message.stop_reason`.

    Vì sao là trường này chứ không phải "text mà không gọi tool" (luật cũ, đã kill oan 2
    worker ngày 28/08/2026) — xem khối "DẤU HIỆU TẤT ĐỊNH" ở docstring đầu tệp. Tóm tắt:
    một lượt model được ghi thành NHIỀU bản ghi (thinking · text · tool_use), chỉ bản ghi
    CUỐI của lượt mới có `stop_reason` khác `null`. Worker vừa nói vừa làm sinh ra bản ghi
    `text` với `stop_reason: null` ở GIỮA CHỪNG — luật cũ đọc trúng khe đó là phán nhầm.

    Mọi bất trắc -> False (coi như đang chạy).
    """
    try:
        for r in reversed(_tail_records(path)):
            if r.get("type") == "attachment":
                continue
            if r.get("type") == "user" and r.get("isMeta"):
                continue
            msg = r.get("message") or {}
            content = msg.get("content")
            texts = []
            if isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "text":
                        texts.append(str(b.get("text") or ""))
            elif isinstance(content, str):
                texts.append(content)
            if r.get("type") == "user":
                # Cha vừa gửi việc mới -> đang chạy. Chỉ bản ghi NGẮT thật mới tính, mà bản
                # ghi ngắt luôn MỞ ĐẦU bằng chuỗi đó (đo: 66/67 bản ghi ngắt thật). Ca thứ
                # 67 là một brief TRÍCH chuỗi ấy để dặn dò -> `in` sẽ khai tử worker ngay
                # bản ghi đầu tiên của nó, nên phải so bằng `startswith`.
                return any(t.strip().startswith(NGAT) for t in texts)
            if r.get("type") == "assistant":
                return msg.get("stop_reason") in KET_LUOT
        return False
    except Exception:
        return False


# ===================== VÙNG TỆP (chống hai worker cùng ghi một vùng) ==========
# Ngày 26/08/2026: cổng "trùng mảng" cũ so bằng TỪ KHOÁ trong mô tả nên worker "A35 chia
# tab" và worker "fix lỗi đẩy đơn" không trùng chữ nào -> lọt; hai con cùng ghi
# src/lib/fulfill/ -> `git add` của con này cuốn phần dang dở của con kia -> main không
# biên dịch được, lô deploy gãy. Nên phải so bằng VÙNG TỆP THẬT, không so chữ.
VUNG_GOC = ("src", "scripts", "e2e", "workers", "packages", "app", "lib", "docs")
RX_DUONG = re.compile(r"(?:^|[\s\"'`(=,])\.?/?((?:%s)/[\w./@\-\[\]]+)"
                      % "|".join(VUNG_GOC))
VUNG_TAIL = 3 * 1024 * 1024   # đọc 3 MB cuối transcript là đủ thấy tệp đã chạm

# 26/08/2026 chiều — CẮT VÙNG QUÁ THÔ, chặn oan 21 phút: một việc sửa nhánh
# `src/lib/drive` bị chặn vì "trùng vùng" với worker đang sửa `src/lib/pipeline`
# (đường dẫn thư mục 3 đoạn `src/lib/drive/` bị luật cũ cắt mất đoạn cuối -> cả hai
# đều thành `src/lib`). Nên: đoạn đường dẫn chỉ là HỘP CHỨA (src, lib, app, api,
# components…) thì phải đi sâu thêm một tầng nữa mới ra vùng thật.
CHUA = {"src", "app", "lib", "api", "components", "component", "ui", "utils", "util",
        "helpers", "helper", "common", "shared", "core", "modules", "module",
        "services", "service", "routes", "route", "pages", "hooks", "types", "type",
        "styles", "style", "server", "client", "packages", "workers", "scripts",
        "e2e", "public", "assets", "config", "features", "domain", "test", "tests"}
# Tệp nằm THẲNG trong hộp chứa (src/lib/db.ts, src/lib/datetime.ts, src/types/*.ts,
# src/app/globals.css, packages/*/…) = tài sản dùng chung: ai đụng cũng chặn nhau.
CHUNG = "dung-chung"
# Công cụ điều phối trong ~/.claude — KHÔNG BAO GIỜ trùng vùng với kho mã dự án.
TOOL = "tools/univ3"
MAX_TANG = 4
RX_TEP = re.compile(r"\.[A-Za-z0-9]{1,6}$")
RX_HE_THONG = re.compile(r"^(private/)?(tmp|var|etc|usr|opt|dev|Applications)(/|$)")
# Thư mục DỮ LIỆU CHẠY dưới ~/.claude — KHÔNG phải mã univ3 (xem WHY trong `chuan_vung`).
RX_CLAUDE_DU_LIEU = re.compile(
    r"[~/]?\.?claude/(logs|worker-counter|worker-queue|cua-thoat|projects)(/|$)")


def chuan_vung(duong: str) -> str:
    """Đường dẫn -> VÙNG. Cắt tới tầng mà hai worker thật sự đụng file của nhau:
      src/lib/drive/folders.ts   -> src/lib/drive
      src/lib/pipeline/board.ts  -> src/lib/pipeline   (KHÁC vùng trên)
      src/app/api/orders/route.ts-> src/app/api/orders
      src/lib/db.ts              -> dung-chung          (tệp dùng chung tầng trên)
      ~/.claude/universal-hooks/ -> tools/univ3         (không dính kho mã)
    """
    p = (duong or "").strip().strip("\"'`,)").replace("\\", "/")
    if not p:
        return ""
    # ~/.claude có hai loại thư mục KHÁC HẲN NHAU, gộp chung là chặn oan:
    #   · MÃ univ3 (universal-hooks, skills, agents, commands) — hai worker cùng sửa là gãy.
    #   · DỮ LIỆU CHẠY (logs, worker-counter, worker-queue, cua-thoat, projects) — mỗi worker
    #     ghi tệp riêng của nó, chồng nhau không hỏng gì.
    # CA THẬT 07/09/2026: vé W03 `c45caa267d` khai «VÙNG GHI DUY NHẤT: /tmp/nghien-cuu-lam-chuan/
    # và bản sao ~/.claude/logs/nghien-cuu-lam-chuan/» -> dòng khai TỬ TẾ vẫn ra `tools/univ3`
    # vì `/.claude/` khớp trần, nên việc nghiên cứu CHỈ-ĐỌC bị treo sau W154 lần thứ ba.
    if RX_CLAUDE_DU_LIEU.search(p):
        return ""
    if "universal-hooks" in p or "/.claude/" in p or p.startswith("~/.claude"):
        return TOOL
    if RX_HE_THONG.match(p.lstrip("~").lstrip("/")):
        return ""                            # /tmp, /var… không phải vùng mã
    ph = [x for x in p.split("/") if x and x != "."]
    if not ph:
        return ""
    if p.startswith("/") or p.startswith("~"):
        # đường dẫn tuyệt đối -> cắt từ thư mục gốc mã đầu tiên nhận ra được
        idx = next((i for i, x in enumerate(ph) if x in VUNG_GOC), -1)
        if idx < 0:
            return ""
        ph = ph[idx:]
    if ph[0] == "docs":
        return "docs"                        # tài liệu: cả docs coi là một vùng
    thu_muc = ph[:-1] if RX_TEP.search(ph[-1]) else ph
    if not thu_muc:
        return ""                            # tệp ở gốc kho -> regex không bắt tới
    phan, het_hop = [], True
    for seg in thu_muc[:MAX_TANG]:
        phan.append(seg)
        # nhóm route Next.js `(dashboard)`, đoạn động `[id]`, `_private`, `@slot`
        # cũng chỉ là hộp chứa -> đi tiếp một tầng nữa
        hop = seg in CHUA or seg[:1] in ("(", "[", "_", "@")
        if len(phan) >= 2 and not hop:
            het_hop = False
            break
    if len(phan) == 1:
        return phan[0]                       # 'scripts', 'e2e'… rộng -> vung_hep loại
    return CHUNG if het_hop else "/".join(phan)


def vung_tu_text(text: str):
    return {v for v in (chuan_vung(m.group(1)) for m in RX_DUONG.finditer(text or "")) if v}


def vung_hep(vs):
    """Chỉ vùng ĐỦ HẸP mới đem so trùng: bỏ `docs` (ai cũng ghi tài liệu riêng, không gãy
    build) và bỏ vùng một tầng (`src`, `app`…) vì rộng tới mức worker nào cũng dính.
    GIỮ `dung-chung` (tệp dùng chung tầng trên — đúng chỗ đáng chặn)."""
    return {v for v in (vs or set())
            if v and (v == CHUNG or ("/" in v and not v.startswith("docs")))}


# ══════ TÀI NGUYÊN DÙNG CHUNG — khoá phải canh CẢ THỨ KHÔNG PHẢI TỆP MÃ (W64) ══════
# CA VỠ THẬT, tối 04/09/2026 (founder: *"sao phá chung chỗ thì đéo gộp lại luôn thành 1
# cái hoặc xếp hàng?? phá hỏng tốn bao nhiêu thời gian"*): W50 chạy bộ kiểm e2e — `beforeAll`
# gieo lại và `afterAll --clear` XOÁ SẠCH lô đơn trong `chichub_dev`. W56 cần đúng lô đơn
# đó, tra hai lượt liền đều ra bảng rỗng, tưởng dữ liệu hỏng. Cổng trùng vùng CHO CẢ HAI
# CHẠY vì chúng sửa hai TỆP MÃ khác nhau. Đo lại được bằng `--ca-thu-tai-nguyen`.
#
# GỐC: y hệt cả lô W64 — khoá có, nhưng KHOÁ SAI THỨ. Khoá deploy canh tiến trình thay vì
# canh việc (W57 vá); cổng vùng canh tệp mã thay vì canh thứ hai worker thật sự tranh nhau.
#
# CÁCH LÀM: tài nguyên được đặt tên như một VÙNG (`tai-nguyen/...`) rồi thả vào đúng bộ máy
# vùng sẵn có — nên chặn / gộp / xếp hàng / vé / bảng worker ăn theo, không chép đôi logic.
#
# CHỈ GHI MỚI TÍNH, ĐỌC KHÔNG TÍNH (chống chặn oan): hai con cùng `SELECT` kho dữ liệu thử
# thì kệ; chỉ khi có bên gieo lại / xoá sạch / migrate / sinh lại client / dựng lại dev
# server mới là tranh nhau.
TN_DB_DEV = "tai-nguyen/db-dev"          # kho dữ liệu thử chichub_dev
TN_DB_THAT = "tai-nguyen/db-that"        # kho dữ liệu sống chichub_bigdb (ghi hàng loạt)
TN_DEV3000 = "tai-nguyen/dev-3000"       # máy chủ thử cổng 3000
TN_PRISMA = "tai-nguyen/prisma-client"   # `prisma generate` — hỏng client trong RAM dev server
TN_BUILD = "tai-nguyen/build-next"       # thư mục dựng .next / .next-new tại máy

_GHI_SQL = r"(?:insert|update|delete|trunc" + r"ate|drop|alter|create\s+table)"
# Mỗi mẫu -> tập tài nguyên mà lệnh đó GIÀNH. Cố ý hẹp: mỗi mẫu là một hành vi GHI đo được.
TN_MAU = (
    (re.compile(r"seed-orders|prisma\s+db\s+seed|--clear\b", re.I), {TN_DB_DEV}),
    (re.compile(r"prisma\s+(?:migrate|db\s+push)", re.I), {TN_DB_DEV}),
    # `prisma generate` ghi đè client mà DEV SERVER ĐANG CHẠY nạp trong RAM -> /login 500
    # (trí nhớ dự án: `prisma-generate-breaks-running-dev`). Nên nó giành CẢ cổng 3000.
    (re.compile(r"prisma\s+generate", re.I), {TN_PRISMA, TN_DEV3000}),
    # Bộ kiểm e2e vừa gieo lại kho dữ liệu thử vừa lái máy chủ thử — chính ca vỡ tối nay.
    (re.compile(r"test:e2e|playwright\s+test", re.I), {TN_DB_DEV, TN_DEV3000}),
    (re.compile(r"(?:pnpm|npm|yarn)\s+(?:run\s+)?dev(?::clean)?\b|next\s+dev", re.I), {TN_DEV3000}),
    (re.compile(r"chichub_dev[\s\S]{0,200}?" + _GHI_SQL, re.I), {TN_DB_DEV}),
    (re.compile(r"chichub_bigdb[\s\S]{0,200}?" + _GHI_SQL, re.I), {TN_DB_THAT}),
    (re.compile(r"(?:pnpm|npm)\s+(?:run\s+)?build\b|next\s+build|\.next-new", re.I), {TN_BUILD}),
)
# Lệnh ĐANG SOI CHỮ chứ không chạy thật: `grep 'prisma generate' …`, script python dựng
# regex để rà nhật ký (đúng thứ chính lượt vá này chạy). Không lọc thì cổng tự bắt mình.
TN_KHONG_CHAY = re.compile(r"re\.compile|^\s*(?:grep|rg|ack|ripgrep)\b", re.I)
# Thân heredoc là DỮ LIỆU ĐANG ĐƯỢC GHI RA TỆP, không phải lệnh đang chạy. Đo ngay trong
# lượt vá này: worker soạn tệp ca thử có chữ `playwright test` bằng `cat > … <<'PY'` là
# lập tức bị tính ĐANG GIỮ kho dữ liệu thử + máy chủ thử -> chặn oan con kế tiếp.
# Đuôi lệnh có thể nằm NGAY SAU marker (`<<'MSG' && git log …`) — bản đầu đòi xuống
# dòng ngay nên trượt, và nguyên văn commit message bị đọc thành lệnh: chính W64 bị
# tính giữ `tai-nguyen/db-dev` vì message có chữ «chichub_dev … --clear», chặn oan vé W67.
RX_HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\r?\n.*?\r?\n\s*\1\b", re.S)
# Mã nguồn truyền qua `-c`/`-e` cũng là DỮ LIỆU, không phải lệnh shell đang chạy:
# `python3 -c "... playwright test ..."` là đang tự kiểm phép đo, không đụng tài nguyên.
RX_MA_NHUNG = re.compile(r"(?:python3?|node)\s+-(?:c|e)\s+([\'\"])(?:\\.|(?!\1).)*\1", re.S)


HAU_DOC = "?doc"          # đuôi đánh dấu "việc mới chỉ ĐỌC tài nguyên này"
# Cờ MÙ: không đọc được transcript của worker đang chạy -> không dám nói nó giữ gì.
KHONG_DO = "khong-do-duoc/vung-worker"


def doi_chieu_vung(vung_moi, vung_giu):
    """Vùng/tài nguyên hai bên THẬT SỰ đụng nhau — KHOÁ ĐỌC–GHI, không phải giao tập thô.

    Worker ĐANG CHẠY chỉ bao giờ khai tài nguyên nó GHI (đọc không tính, y luật vùng tệp).
    Việc MỚI thì khai cả tài nguyên nó chỉ ĐỌC, gắn đuôi `?doc`. Nên:
      · ghi × ghi  -> đụng          · ghi × đọc -> ĐỤNG (đúng ca W50 xoá sạch, W56 đọc rỗng)
      · đọc × đọc  -> KHÔNG đụng (bên kia không hề khai đọc nên không bao giờ giao nhau)
    Founder chốt: *"Hai con cùng đọc kho dữ liệu thì không sao; chỉ chặn khi có bên ghi"*.
    """
    giu = vung_giu or set()
    if KHONG_DO in giu:
        # Mù về bên đang giữ -> KHÔNG được kết luận là trống. Mọi vùng của việc mới đều
        # coi như đụng; lời chặn in đúng cờ này để người đọc biết là mù chứ không phải
        # đo ra trùng.
        return set(vung_moi or set()) | {KHONG_DO}
    ra = set()
    for v in (vung_moi or set()):
        goc = v[:-len(HAU_DOC)] if v.endswith(HAU_DOC) else v
        if goc in giu:
            ra.add(goc)
    return ra


def tai_nguyen_tu_lenh(cmd: str):
    """Tài nguyên dùng chung mà MỘT LỆNH BASH giành lấy (chỉ hành vi GHI)."""
    c = RX_MA_NHUNG.sub(" ", RX_HEREDOC.sub(" ", str(cmd or "")))
    if not c or TN_KHONG_CHAY.search(c):
        return set()
    ra = set()
    for rx, tn in TN_MAU:
        if rx.search(c):
            ra |= tn
    return ra


# Phía VIỆC MỚI: brief khai `TÀI NGUYÊN:` (tin tuyệt đối), hoặc suy từ chữ khi quên khai.
RX_TN_KHAI = re.compile(r"^[ \t>*\-]*(?:T[ÀA]I\s*NGUY[ÊE]N|RESOURCE)\s*[:=]\s*(.+)$", re.I | re.M)
TN_TEN = {"db-dev": TN_DB_DEV, "chichub_dev": TN_DB_DEV, "db-that": TN_DB_THAT,
          "chichub_bigdb": TN_DB_THAT, "dev-3000": TN_DEV3000, "3000": TN_DEV3000,
          "prisma": TN_PRISMA, "prisma-client": TN_PRISMA, "build": TN_BUILD,
          "build-next": TN_BUILD, "next": TN_BUILD}
# Suy từ chữ: chỉ những cách nói CHẮC CHẮN có ghi. "đọc DB", "tra đơn" KHÔNG nằm ở đây.
TN_SUY = (
    (re.compile(r"ch[ạa]y\s+(?:b[ộo]\s+ki[ểe]m|e2e|playwright)|test:e2e|b[ộo]\s+ki[ểe]m\s+e2e", re.I),
     {TN_DB_DEV, TN_DEV3000}),
    (re.compile(r"gieo\s*l[ạa]i|seed\b|d[ữu]\s*li[ệe]u\s*th[ửu]\s*(?:m[ớo]i|l[ạa]i)|"
                r"xo[áa]\s*s[ạa]ch\s*d[ữu]\s*li[ệe]u|--clear\b", re.I), {TN_DB_DEV}),
    (re.compile(r"prisma\s+generate|sinh\s*l[ạa]i\s*client|generate\s*client", re.I),
     {TN_PRISMA, TN_DEV3000}),
    (re.compile(r"dev\s*server|(?:pnpm|npm)\s+(?:run\s+)?dev\b|localhost:3000|c[ổo]ng\s*3000",
                re.I), {TN_DEV3000}),
    (re.compile(r"prisma\s+(?:migrate|db\s+push)|ch[ạa]y\s+migration", re.I), {TN_DB_DEV}),
    (re.compile(r"chichub_bigdb[\s\S]{0,120}?(?:ghi|c[ậa]p\s*nh[ậa]t|xo[áa]|ch[èe]n|migration)|"
                r"(?:ghi|c[ậa]p\s*nh[ậa]t|xo[áa]|ch[èe]n)[\s\S]{0,60}?chichub_bigdb", re.I),
     {TN_DB_THAT}),
    (re.compile(r"(?:pnpm|npm)\s+(?:run\s+)?build\b|next\s+build", re.I), {TN_BUILD}),
)
# DÙNG mà KHÔNG ghi — vẫn phải biết, vì bên kia GHI thì việc này đọc ra rác (ca W56 tra
# hai lượt đều ra bảng rỗng). Gắn đuôi `?doc`: chỉ đụng với bên đang GHI, không đụng nhau.
TN_SUY_DOC = (
    (re.compile(r"chichub_dev|kho\s*d[ữu]\s*li[ệe]u\s*th[ửu]|db\s*dev|d[ữu]\s*li[ệe]u\s*th[ửu]",
                re.I), {TN_DB_DEV}),
    (re.compile(r"chichub_bigdb|db\s*s[ốô]ng|d[ữu]\s*li[ệe]u\s*th[ậa]t", re.I), {TN_DB_THAT}),
    (re.compile(r"localhost:3000|c[ổo]ng\s*3000|m[áa]y\s*ch[ủu]\s*th[ửu]", re.I), {TN_DEV3000}),
)


def tai_nguyen_tu_brief(text: str):
    """Tài nguyên mà VIỆC MỚI sẽ giành. Có dòng khai thì tin khai, không suy thêm."""
    t = str(text or "")
    if not t:
        return set()
    khai, co_khai = set(), False
    for m in RX_TN_KHAI.finditer(t):
        co_khai = True
        for tu in re.split(r"[\s,;]+", m.group(1).strip()):
            k = tu.strip().strip("`\"'").lower()
            if k in TN_TEN:
                khai.add(TN_TEN[k])
            elif k.startswith("tai-nguyen/"):
                khai.add(k)
    if co_khai:
        return khai
    # Câu dặn KHÔNG đụng / chỉ đọc thì không tính dòng đó (y luật phía vùng tệp).
    ra = set()
    for dong in t.splitlines():
        for rx, tn in TN_SUY:
            # Dòng dặn "không đụng / chỉ đọc" thì phần GHI của dòng đó không tính.
            if not RX_KHONG_DUNG.search(dong) and rx.search(dong):
                ra |= tn
        for rx, tn in TN_SUY_DOC:
            # W146 06/09/2026 — Đ1a: đối xứng với TN_SUY ngay trên. Trước bản vá này
            # nhánh ?doc KHÔNG lọc RX_KHONG_DUNG -> câu "kho dữ liệu thử — KHÔNG đụng"
            # vẫn đẻ vùng (Ca B, phiếu P-GO-KET-DIEU-PHOI-06092026).
            if not RX_KHONG_DUNG.search(dong) and rx.search(dong):
                ra |= {x + HAU_DOC for x in tn}
    # Đã giành quyền GHI thì khỏi ghi thêm bản "chỉ đọc" của cùng tài nguyên.
    return {v for v in ra
            if not (v.endswith(HAU_DOC) and v[:-len(HAU_DOC)] in ra)}


# --- suy VÙNG của việc MỚI: ưu tiên KHAI BÁO, cấm đoán bừa từ chữ trong brief ---
# HAI KHUÔN, cố ý tách:
#  (1) nhãn ĐẦU DÒNG — khuôn cũ, giữ nguyên kể cả viết thường (re.I).
#  (2) nhãn GIỮA DÒNG, CHỮ HOA — thêm 07/09/2026 (W154).
# CA THẬT ĐANG KẸT LÚC VÁ: vé W03 `ced74a9609` nằm chờ 19 phút vì cổng suy vùng ra
# `tools/univ3`, trong khi brief khai vùng ghi HAI LẦN mà khuôn cũ trượt cả hai:
#     "W03 Nghien cuu cach lam chuan — VÙNG: /tmp/nghien-cuu-lam-chuan — TÀI NGUYÊN: -"
#         -> nhãn nằm GIỮA dòng, sau dấu "—"  -> `^` không khớp
#     "VÙNG GHI DUY NHẤT: `/tmp/nghien-cuu-lam-chuan/`"
#         -> có chữ "DUY NHẤT" xen giữa "VÙNG GHI" và ":" -> `\s*[:=]` không khớp
# Trượt khai -> rơi xuống nhánh SUY -> nhặt chữ "univ3" trong đúng câu DẶN KHÔNG ĐỤNG.
# Đây là nhóm báo động giả LỚN NHẤT đo được: 9/27 lần mở cửa thoát `trung-vung` trong
# `~/.claude/logs/cua-thoat.log` đều ghi lý do "may doc cau canh bao thanh vung ghi".
# VÌ SAO KHUÔN (2) BẮT BUỘC CHỮ HOA (không `re.I`): brief luôn gõ nhãn in hoa `VÙNG:`,
# còn văn xuôi thì viết thường ("vùng này của W12") — chữ hoa là mốc phân biệt tất định,
# không phải phỏng đoán. Nới mà bỏ mốc đó thì mỗi câu văn có chữ "vùng:" đều thành lời khai.
# 07/09/2026 (W07) — NHÃN CHÍNH THỨC LÀ `GHI:`; các nhãn cũ (`VÙNG:`, `ZONE:`…) giữ làm
# biến thể để vé cũ trong hàng chờ và brief đang trôi không chết.
# VÌ SAO `GHI` BẮT BUỘC CHỮ HOA (bọc `(?-i:...)` dù regex có `re.I`): chữ "ghi" là động từ
# thường gặp nhất trong brief tiếng Việt ("ghi: đã xong", "· ghi báo cáo"). Nhận cả chữ
# thường thì một câu kể chuyện cũng thành LỜI KHAI -> cổng trùng vùng tự tắt mà không ai
# biết. Chữ hoa là mốc tất định, không phải phỏng đoán.
_NHAN_GHI = (r"(?:V[ÙU]NG(?:\s+GHI)?|(?-i:GHI)|ZONE|WRITE[- ]?ZONE|(?-i:WRITE))")
RX_KHAI_DAU_DONG = re.compile(
    r"^[ \t>*\-]*" + _NHAN_GHI + r"\s*[:=]\s*(.+)$", re.I | re.M)
RX_KHAI_GIUA_DONG = re.compile(
    r"(?:^|[—–·|]\s*)" + _NHAN_GHI
    + r"(?:\s+(?:DUY\s+NH[ẤA]T|CH[ÍI]NH|G[ỐO]C|Y[Ế E]U))?\s*[:=]\s*([^—–·|\n]+)", re.M)


class _RxKhaiGop:
    """Gộp hai khuôn thành MỘT đối tượng có `.finditer` — chỗ dùng không phải đổi."""

    @staticmethod
    def finditer(text):
        for rx in (RX_KHAI_DAU_DONG, RX_KHAI_GIUA_DONG):
            for m in rx.finditer(text):
                yield m


RX_KHAI = _RxKhaiGop
RX_KHONG_DUNG = re.compile(
    r"(kh[ôo]ng\s+[đd][uụ]ng|kh[ôo]ng\s+s[ửu]a|kh[ôo]ng\s+ghi|c[ấa]m\s+s[ửu]a|"
    r"ch[ỉi]\s+[đd][ọo]c|read[- ]only)", re.I)
RX_VI_DU = re.compile(
    r"(v[íi]\s*d[ụu]|\bvd\b|\be\.g\b|minh\s*ho[ạa]|tham\s*kh[ảa]o|xem\s+th[êe]m|"
    r"[đd][ọo]c\s+(file|t[ệe]p))", re.I)
RX_TOOL_TEXT = re.compile(r"(universal-hooks|~/\.claude|\$HOME/\.claude)", re.I)

# 04/09/2026 (W09 đo) — PHÍA VIỆC MỚI VẪN TÍNH ĐỌC LÀ GHI.
# `vung_viec_moi("Đọc ~/.claude/universal-hooks/worker_board.py rồi ghi báo cáo")` trả
# `{'tools/univ3'}` -> brief chỉ ĐỌC univ3 mà GHI vào `docs/` vẫn bị deny vì worker khác
# đang giữ univ3. Chính lời chặn cũng thừa nhận *"CHỈ ĐỌC VẪN BỊ TÍNH"*. Bộ lọc cũ chỉ bỏ
# CẢ DÒNG khi thấy "chỉ đọc"/"đọc file" — dòng vừa đọc vừa ghi thì không cứu được.
# NAY bỏ ĐÚNG cụm «<động từ đọc> <đường dẫn>», giữ nguyên phần ghi trong cùng dòng.
# Phía worker đã chữa xong từ trước (Read/Grep/Glob không đẻ vùng) — nay hai phía cùng luật.
# Chữ đệm cho phép giữa động từ và đường dẫn. Danh sách ĐÓNG là cố ý: gặp chữ lạ
# ("cách cũ, rồi sửa") thì KHÔNG khớp -> phần GHI phía sau được giữ nguyên.
_DEM = (r"(?:\s+(?:l[ạa]i|th[ửu]|qua|k[ỹy]|n[ộo]i\s*dung|file|t[ệe]p|th[ưu]\s*m[ụu]c|"
        r"trong|[ởo]|t[ừu]|-\w+))*")
# MỘT HOẶC NHIỀU đường dẫn nối nhau bằng `,` / `và` / `+`. Bản cũ chỉ nuốt đường dẫn
# ĐẦU nên "Chỉ đọc A.ts và B.ts" vẫn đẻ vùng từ B.ts.
_DUONG = r"[~./\w@$-]*[/][\w@.\-/*]+"
# BẮT BUỘC có khoảng trắng (hoặc `:` rồi khoảng trắng) trước đường dẫn ĐẦU, và bắt buộc
# có dấu nối rõ ràng trước mỗi đường dẫn sau. Bỏ ràng buộc này là hồi quy ngay: "doc"
# trong chữ "docs/handoff" khớp luôn động từ đọc -> nuốt mất vùng GHI (W07 đo 04/09).
_DS_DUONG = (r"(?:\s*[:：])?\s+" + _DUONG
             + r"(?:\s*(?:,|v[àa]|and|\+|&)\s*" + _DUONG + r")*")
RX_DOC_DUONG_DAN = re.compile(
    r"\b(?:[đd][ọo]c|xem|so[ií]|r[àa]|tham\s*kh[ảa]o|[đd][ốo]i\s*chi[ếe]u|m[ởo]|read|cat|grep|less|head|tail)\b"
    + _DEM + _DS_DUONG, re.I)
# 04/09/2026 — LỖ AN TOÀN (W09 báo, W07 đo lại: 6/6 cụm đều thủng). `RX_VI_DU` và
# `RX_KHONG_DUNG` bản cũ bỏ CẢ DÒNG. Brief mở đầu bằng "Tham khảo cách cũ, rồi sửa
# src/lib/fulfill/send.ts" mất TOÀN BỘ vùng ghi -> cổng trùng vùng im lặng CHO QUA dù
# worker khác đang ghi đúng chỗ đó (kịch bản gãy build 26/08). Hướng lỗi là LỌT, không
# phải chặn oan, nên thống kê chặn-oan không bao giờ bắt được. Nay bỏ theo CỤM.
RX_VI_DU_CUM = re.compile(
    r"\b(?:v[íi]\s*d[ụu]|vd|e\.g|minh\s*ho[ạa]|tham\s*kh[ảa]o|xem\s+th[êe]m)\b"
    + _DEM + _DS_DUONG, re.I)
# KHÔNG thêm cụm CẤM ở đây: mệnh đề cấm đã bị `_bo_menh_de_cam` cắt tới hết dòng TRƯỚC
# khi tới vòng lặp này (quyết định W188 của founder: thà bỏ sót vùng còn hơn chặn oan).
# Thêm nữa là mã chết. Hệ quả còn lại — dòng "Không đụng A, chỉ sửa B" mất luôn vùng B —
# đã ghi vào báo cáo để founder quyết, không tự đổi.


# W188 29/08/2026 — CÂU CẤM KHÔNG PHẢI LỜI KHAI VÙNG GHI.
# CA THẬT founder chỉ mặt: brief W190 («điều tra thẻ hiện hai chip A14», CHỈ ĐỌC) và W191
# («đẩy 8 bản lưu lên demo/prod», vùng `scripts/deploy-batch.sh`) đều có dòng ràng buộc
# «KHÔNG đụng ~/.claude/universal-hooks/ (W187, W188 đang giữ)». Cổng đọc thấy tên thư mục
# đó rồi CHẶN cả hai với lý do «ghi vào VÙNG worker khác ĐANG GIỮ: tools/univ3».
# Nguyên văn founder: «toàn đẩy chờ nhưng khi có task liên quan đéo tự động phân tích để
# gộp. tốn nguồn lực và thời gian vãi lồn.»
# Càng viết ràng buộc cẩn thận thì càng bị chặn — ngược hoàn toàn ý đồ.
# Hai lỗ đã bịt ở đây:
#   (1) nhánh cũ `co_tool and RX_KHONG_DUNG -> {TOOL}, "khai"` HIỂU NGƯỢC: nó đọc câu
#       "KHÔNG đụng universal-hooks" thành "chỉ sửa universal-hooks". Bỏ hẳn nhánh đó.
#   (2) dòng khai `VÙNG:` bị nuốt cả mệnh đề cấm nằm trong ngoặc cùng dòng -> `chuan_vung`
#       thấy chữ "universal-hooks" là trả TOOL. Nay cắt mệnh đề cấm TRƯỚC khi bóc vùng.
RX_CAM_RONG = re.compile(
    r"(kh[ôo]ng\s+[đd][uụ]ng|kh[ôo]ng\s+s[ửu]a|kh[ôo]ng\s+ghi|kh[ôo]ng\s+ch[ạa]m|"
    r"c[ấa]m\s+[đd][uụ]ng|c[ấa]m\s+s[ửu]a|c[ấa]m\s+ghi|tr[áa]nh\s+[đd][uụ]ng|"
    r"n[ée]\s+v[ùu]ng|[đd]ang\s+gi[ữu]|worker\s+kh[áa]c\s+gi[ữu]|"
    r"ch[ỉi]\s+[đd][ọo]c|read[- ]only)", re.I)


def _bo_menh_de_cam(text: str) -> str:
    """Bỏ MỆNH ĐỀ CẤM khỏi brief trước khi suy vùng ghi.

    Cắt hai lớp, đúng thứ tự:
      · cụm nằm trong ngoặc đơn có chữ cấm  -> xoá cả cụm  «(KHÔNG đụng ~/.claude/…)»
      · phần còn lại từ chữ cấm tới hết dòng -> xoá        «… , không ghi tệp mã nguồn»
    Thà bỏ sót một vùng còn hơn chặn oan: vùng suy sai thì brief khai thẳng `VÙNG:` là xong,
    còn chặn oan thì việc nằm chết trong hàng chờ và founder không biết.
    """
    ra = []
    for dong in (text or "").splitlines():
        d = re.sub(r"\([^()]*\)", lambda m: " " if RX_CAM_RONG.search(m.group(0)) else m.group(0), dong)
        m = RX_CAM_RONG.search(d)
        if m:
            d = d[:m.start()]
        ra.append(d)
    return "\n".join(ra)


# Dấu tách giữa nhiều đường dẫn trên MỘT dòng khai: dấu câu, chữ "và", và KHOẢNG TRẮNG.
# W46 29/08/2026 — vì sao thêm khoảng trắng: brief khai «VÙNG: src/app/pipeline
# src/components/card» thì bản cũ nuốt cả cụm thành MỘT vùng tên «src/app/pipeline src»
# -> hai vùng khai ra biến mất sạch, mọi phép so trùng vùng sau đó trượt. Điều phối khai
# càng đầy đủ thì cổng càng mù.
RX_KHAI_TACH = re.compile(r"[,;|+]|\s+v[àa]\s+|\s+")
# Token nào MỚI là đường dẫn: chỉ chữ/số ASCII và `. - _ @ [ ] ( ) / ~`. Dòng khai thật
# hay lẫn văn xuôi tiếng Việt («VÙNG: enforce/claude/hooks/ — các tệp hệ vé») và gạch dài;
# không lọc thì `chuan_vung("các")` đẻ ra vùng ma, in lên lời chặn founder đọc không hiểu.
RX_TOKEN_DUONG = re.compile(r"^[~./]*[A-Za-z0-9_@.\-\[\]()]+(?:/[A-Za-z0-9_@.\-\[\]()]*)*/?$")


def _bo_ngoac(s: str) -> str:
    """Bỏ cụm trong ngoặc đơn khỏi dòng khai — chú thích, không phải đường dẫn."""
    # P138 11/10/2026 — ngoặc đứng NGAY SAU `/` là MỘT ĐOẠN ĐƯỜNG DẪN (nhóm route Next.js
    # `(app)`, `(dashboard)`), không phải chú thích. Bản cũ xoá luôn nên brief P137 khai
    # `src/app/(app)/layout.tsx` ra tiền tố thô `src/app/` -> cổng commit cho qua MỌI tệp
    # dưới `src/app` (đo: `git_add_scope_enforce.tien_to_khai` trên vé 9e5d43d6e9). Siết, không nới.
    return re.sub(r"(?<!/)\([^()]*\)", " ", s or "")


# W39 01/10/2026 (P114 mục 4.5, ca W21 30/09 21:22–21:24, ba lượt mở cửa thoát) — gốc kho
# của lượt đang xét, do `main()` / `git_add_scope_enforce` gán từ `cwd` của payload. Dùng để
# nhận CHỮ TRƠN là tên thư mục THẬT ở gốc kho: brief khai `GHI: db functions public …` mà
# `functions` không nằm trong `VUNG_GOC` nên bị vứt như chữ thường -> commit `functions/api/…`
# bị chặn "ngoài vùng". Đo trên đĩa (`os.path.isdir`), không đoán theo chữ.
_GOC_KHO = ""


def la_thu_muc_goc(tok: str, goc: str = "") -> bool:
    goc = goc or _GOC_KHO
    ds = [g for g in (goc if isinstance(goc, (list, tuple)) else [goc]) if g]
    # W45: chỉ gỡ TIỀN TỐ `~/` · `./` · `/`, giữ dấu chấm của tên (`GHI: .claude`).
    t = re.sub(r"^(?:~/|\./|/)+", "", (tok or "").strip()).rstrip("/")
    if not ds or not t or "/" in t or not re.match(r"^\.?[A-Za-z0-9_][A-Za-z0-9_.-]*$", t):
        return False
    try:
        return any(os.path.isdir(os.path.join(g, t)) for g in ds)
    except Exception:
        return False


# W45 01/10/2026 — `.strip("….")` cũ gọt dấu chấm Ở CẢ HAI ĐẦU: brief W44 khai đích danh
# `GHI: … .claude/xung-ho-enforce.py`, token thành `claude/xung-ho-enforce.py` -> vùng
# `claude`, trong khi `git add .claude/…` ra vùng `.claude` -> chặn oan đúng tệp đã khai
# (`cong-git-vung.log` 01:55:08, cửa thoát mở lúc 01:55:32). Dấu chấm chỉ là DẤU CÂU khi
# nằm CUỐI token («docs/ticket.»); ở đầu token nó là một phần tên (`.claude`, `.husky`).
def bo_dau_token(tok: str) -> str:
    return (tok or "").strip().strip("\"'`,;").rstrip(".").strip()


def _vung_khai(dong: str):
    """Bóc TẤT CẢ đường dẫn trong phần sau dấu `:` của một dòng `VÙNG:`."""
    ra = set()
    for tok in RX_KHAI_TACH.split(_bo_ngoac(dong)):
        tok = bo_dau_token(tok)
        if not tok or not RX_TOKEN_DUONG.match(tok):
            continue
        if "/" not in tok and tok.strip("~./") not in VUNG_GOC and not la_thu_muc_goc(tok):
            continue                      # một chữ trơ trọi ("univ3", "sửa") — không phải vùng
        v = chuan_vung(tok)
        if v:
            ra.add(v)
    return ra


# CHẠY một script KHÁC HẲN GHI vào nó. Ca thật 07/09/2026: vé W05 `2f66c06aba` bị chặn oan
# vì đúng một dòng — dòng mà MỌI brief deploy trong hệ này đều có:
#     Chờ khoá deploy bằng đúng một dòng: `bash ~/.claude/universal-hooks/wlock.sh wait deploy …`
# `RX_TOOL_TEXT` nhặt chuỗi `~/.claude` trong đó rồi gán vùng `tools/univ3`, nên hễ có worker
# univ3 nào còn sống là MỌI worker deploy đều bị treo. Cùng nhóm với 11/27 lần mở cửa thoát
# `trung-vung` ghi lý do "worker chỉ ĐỌC / ghi vùng khác hẳn" (`~/.claude/logs/cua-thoat.log`).
# CHỈ bóc CẶP «trình thông dịch + đường dẫn script» — phần còn lại của lệnh giữ nguyên, nên
# `bash x.sh > ~/.claude/…` vẫn tính là GHI (nhánh chuyển hướng `_duong_ghi_bash` không đụng).
RX_CHAY_SCRIPT = re.compile(
    r"\b(?:bash|sh|zsh|python3?|node|source|\.)\s+(['\"`]?)([~./][^\s;|&<>\"'`]*)\1", re.I)


def _bo_lenh_chay_script(text: str) -> str:
    """Bỏ đường dẫn SCRIPT ĐƯỢC CHẠY khỏi văn bản trước khi suy vùng ghi."""
    return RX_CHAY_SCRIPT.sub(lambda m: m.group(0)[:m.start(2) - m.start()], text or "")


def vung_viec_moi(text: str):
    """(tập vùng, nguồn) — nguồn: 'khai' (brief khai dòng `GHI:`, tin tuyệt đối) ·
    'khai-rong' (CÓ dòng khai nhưng không bóc ra đường dẫn nào, vd `GHI: -` -> cho qua,
    cảnh báo) · 'thieu-khai' (KHÔNG có dòng khai nào -> bên gọi CHẶN, xem WHY cuối hàm).

    KHÔNG CÒN nguồn 'suy'/'khong': cổng không đoán vùng từ văn xuôi nữa.
    Dòng `ĐỌC:` trong brief cố ý KHÔNG được đọc ở đây — vùng chỉ-đọc không phải tranh chấp.

    CÓ DÒNG KHAI THÌ KHÔNG BAO GIỜ SUY NỮA — kể cả khi dòng khai bóc ra rỗng. Đó là ý
    founder (W46): *"khi có khai báo thì DÙNG khai báo, KHÔNG suy từ các đường dẫn khác
    trong brief"*; brief nào cũng nhắc dăm đường dẫn để ĐỌC, suy tiếp là chặn oan.
    """
    text = _bo_menh_de_cam(text or "")
    co_dong_khai = False
    khai = set()
    for m in RX_KHAI.finditer(text):
        co_dong_khai = True
        khai |= _vung_khai(m.group(1))
    # W64: tài nguyên dùng chung đi CÙNG mọi đường về — brief khai `VÙNG:` tử tế vẫn có
    # thể gieo lại kho dữ liệu thử, mà đó mới là thứ làm hỏng việc của con bên cạnh.
    tn = tai_nguyen_tu_brief(text)
    if co_dong_khai:
        # W146 06/09/2026 — Đ1b: có dòng khai (VÙNG: hoặc TÀI NGUYÊN:) rồi thì CHỈ còn
        # tin phần GHI suy từ tn; bỏ hẳn phần `?doc` (suy từ VĂN XUÔI, không phải khai
        # cứng) — nó chỉ bảo vệ CHÍNH việc mới khỏi đọc rác (ca W56), KHÔNG bảo vệ kho
        # mã, nên người đã khai vùng tử tế có quyền tự chịu rủi ro đọc rác. Trước bản vá
        # này `khai |= tn` nuốt luôn cả ?doc -> Ca B (W145 chỉ khai VÙNG: docs/ticket,
        # cổng vẫn đẻ tai-nguyen/db-dev?doc từ câu mô tả bệnh "kho dữ liệu thử").
        khai |= {v for v in tn if not v.endswith(HAU_DOC)}
        return khai, ("khai" if khai else "khai-rong")
    # 07/09/2026 (W07) — BỎ HẲN ĐƯỜNG SUY VÙNG TỪ VĂN XUÔI.
    # Founder chốt qua AskUserQuestion: *"Bắt brief khai vùng theo khuôn cố định, cấm đoán
    # hẳn."* Trong ĐÚNG MỘT buổi 07/09 nhánh `suy` phải vá BỐN lần, lần nào cũng lòi lỗ mới:
    #   ① khai giữa dòng không đọc được (univ3 4.70.1 · 6e71721)
    #   ② dòng LỆNH CHẠY `bash …/wlock.sh wait deploy` bị tính là GHI -> mọi worker deploy
    #      treo khi có worker univ3 sống (4.70.2 · f05b7ae)
    #   ③ thư mục NHẬT KÝ (dữ liệu chạy) gộp chung với thư mục hook (mã univ3) (4.70.3 · 8faf67d)
    #   ④ brief đi vá chính cổng này bị chặn oan vì phần VÍ DỤ có nhắc tên một thư mục mã
    #      worker khác đang giữ — `cong-trung-vung.log` 11:37:33, "nguồn suy vùng: suy".
    # Mỗi khuôn brief mới lại đẻ một lỗ vì máy đang ĐOÁN ý người từ câu chữ. Nay đổi giao
    # kèo: brief KHAI, cổng ĐỌC KHAI. Không khai -> chặn, không đoán bừa nữa.
    return set(), "thieu-khai"


# Tool GHI thật sự. `Read`/`Glob`/`Grep` KHÔNG nằm đây — xem WHY ở `vung_worker`.
GHI_TOOL = ("Edit", "Write", "MultiEdit", "NotebookEdit")
# Lệnh Bash có GHI ra tệp: `git add`, chuyển hướng `>`/`>>`, `tee`.
RX_GIT_ADD = re.compile(r"\bgit\s+add\s+([^\n;|&]+)")
# Chuyển hướng ghi. `(?<![-=|>])` loại MŨI TÊN trong văn xuôi (`->`, `=>`, `|>`, `>>` đã
# tính ở nhánh chính) — brief và bình luận tiếng Việt đầy mũi tên, không lọc thì mỗi câu
# "deploy -> ssh đọc BUILD_ID" đẻ một vùng ma.
RX_CHUYEN_HUONG = re.compile(r"(?<![-=|>])>>?\s*([^\s;|&<>\"'`]+)")
RX_TEE = re.compile(r"\btee\s+(?:-a\s+)?([^\s;|&<>\"'`]+)")
# Token phải TRÔNG NHƯ đường dẫn thật: chỉ chữ/số ASCII và `. - _ @ ~ /`. Loại thẳng thứ
# có `$` (biến shell), ngoặc, dấu regex — chúng là mảnh văn bản, không phải tệp.
RX_TEP_HOP_LE = re.compile(r"^[~./A-Za-z0-9_@][A-Za-z0-9_@.\-/]*$")


def _duong_ghi_bash(cmd: str):
    """Đường dẫn mà MỘT lệnh Bash thật sự GHI vào (git add · `>`/`>>` · tee)."""
    tho = []
    for m in RX_GIT_ADD.finditer(cmd or ""):
        tho += [d for d in m.group(1).split() if not d.startswith("-")]
    for rx in (RX_CHUYEN_HUONG, RX_TEE):
        tho += [m.group(1) for m in rx.finditer(cmd or "")]
    ra = []
    for d in tho:
        d = d.strip().strip("\"'`,;")
        if not d or not RX_TEP_HOP_LE.match(d):
            continue
        if "/" not in d and "." not in d:
            continue                      # một chữ trơ trọi -> không phải đường dẫn
        ra.append(d)
    return ra


# ══ W18 09/09/2026 — VÙNG CHỈ BỊ GIỮ KHI WORKER CÒN THẬT SỰ GHI VÀO NÓ ══════════
# Trước W18 khoá vùng tính theo "worker CÒN SỐNG", nên một worker đã xong chặng ghi mà
# vẫn còn thở thì giữ vùng tới lúc chết. CA THẬT 09/09/2026 14:22 (đo bằng lệnh, không
# đoán): W13 `a9e38e02a1782c514` ghi lần cuối vào `src/lib/orders` / `src/lib/fulfill`
# lúc 13:10:52, tức **74,7 phút trước**; `src/app/orders` 79,2 phút trước. Nó đã commit
# `da5406f0`, đã đẩy demo+prod cùng `BUILD_ID QJPAQGA0ACNwfofxNxJSa`, và lúc đó chỉ đang
# NGỒI CANH bộ kiểm bằng vòng `until … sleep 30`. Ba vé W12·W16·W17 của founder nằm chờ
# 50 / 37 / 10 phút vì đúng ba vùng đó.
#
# TIÊU CHÍ NHẢ (đo được, không phải cảm tính) — vùng được coi là ĐÃ BUÔNG khi:
#   (a) worker KHÔNG ghi vào CHÍNH vùng ấy trong `VUNG_IM_PHUT` phút gần nhất, VÀ
#   (b) sau lần ghi cuối vào vùng ấy nó đã QUA MỘT MỐC BÀN GIAO máy đọc được:
#       `git commit`, hoặc chạy deploy (`deploy-remote.sh` / `promote demo|prod`), hoặc
#       xin khoá deploy (`wlock … deploy`) — tức phần dở của nó đã nằm trong commit,
#       không còn gì để `git add` của worker sau cuốn nhầm.
#   Riêng vùng TÀI NGUYÊN (`tai-nguyen/*`: cổng 3000, kho dữ liệu thử, thư mục dựng)
#   không có khái niệm commit -> chỉ cần (a) với ngưỡng đầy đủ `VUNG_IM_PHUT`.
#   Worker đang NGỒI CANH (lệnh cuối là vòng `until|while … sleep`, `wlock … wait`, hay
#   `sleep` trơ) mà ĐÃ qua mốc bàn giao -> hạ ngưỡng xuống `VUNG_IM_CHO_PHUT`: canh không
#   phải là ghi. Đây là tín hiệu PHỤ, không bao giờ dùng một mình (vẫn phải có (b)).
#
# VÌ SAO KHÔNG SỢ LẶP LẠI CA 26/08 (hai worker cùng ghi `src/lib/fulfill`, `git add` cuốn
# phần dở của nhau, main gãy build):
#   · Ngưỡng đo trên 929 transcript worker thật của dự án này, 3.793 khoảng cách giữa hai
#     lần ghi LIÊN TIẾP vào CÙNG một vùng. Tỉ lệ "nhả rồi worker lại quay về ghi tiếp":
#         chỉ im lặng 30' -> 2,27%   ·  im 45' + đã commit -> 0,45%
#         luật kết hợp (45'+commit, hoặc 15'+commit+đang ngồi canh) -> 1,19%
#   · Cơ chế GÂY GÃY của ca 26/08 (`git add -A` / `git add .` / `commit -a` / `--amend`)
#     đã có cổng tất định riêng chặn từ 26/08: `git_add_scope_enforce.py`. Khoá vùng là
#     lớp thứ hai, không phải lớp duy nhất — nới nó không mở lại cái cửa đã bịt.
#   · Worker CÒN ĐANG GHI (ghi trong vòng ngưỡng) thì vùng GIỮ NGUYÊN, không nới một giây.
VUNG_IM_PHUT = float(os.environ.get("UNIV3_VUNG_IM_PHUT", "45"))
VUNG_IM_CHO_PHUT = float(os.environ.get("UNIV3_VUNG_IM_CHO_PHUT", "15"))
TN_TIEN_TO = "tai-nguyen/"
# Mốc BÀN GIAO: sau lệnh này thì phần việc đã nằm trong commit / đã đi deploy.
RX_QUA_CHANG_GHI = re.compile(
    r"\bgit\s+(?:-\S+\s+)*commit\b"
    r"|\bdeploy-remote\.sh\b|\bdeploy-batch\.sh\b"
    r"|\bpromote\s+(?:demo|prod)\b"
    r"|\bwlock(?:\.sh)?\b[^\n]{0,80}?\bdeploy\b")
# Đang NGỒI CANH chứ không làm: vòng canh, chờ khoá, hoặc `sleep` trơ >= 10 giây.
RX_NGOI_CHO = re.compile(
    r"\b(?:until|while)\b[\s\S]{0,400}?\bsleep\b"
    r"|\bwlock(?:\.sh)?\b[^\n]{0,80}?\bwait\b"
    r"|^\s*sleep\s+\d{2,}\s*$", re.M)


def _moc_ban_ghi(o) -> float:
    """Mốc epoch của một bản ghi transcript. Không đọc được -> `time.time()` (coi như VỪA
    XONG) — thà giữ vùng thừa còn hơn nhả oan vì mất dấu thời gian."""
    try:
        import datetime as _dt
        return _dt.datetime.fromisoformat(
            str(o.get("timestamp") or "").replace("Z", "+00:00")).timestamp()
    except Exception:
        return time.time()


def vung_worker(jl: str, tat_ca: bool = False):
    """Vùng mà worker ĐANG CHẠY thật sự CÒN GIỮ — ĐỌC KHÔNG TÍNH, GHI XONG RỒI CŨNG KHÔNG TÍNH.

    `tat_ca=True` -> trả MỌI vùng từng ghi (không lọc theo mốc im lặng), dùng để báo cáo.

    04/09/2026 — CA THẬT, ĐO ĐƯỢC BẰNG LỆNH (founder: *"cũng cứ bị chờ mãi dù task trần
    không chạm trần. quá ngu dốt"*): W01 chỉ ghi `scripts/*.mjs` + `docs/handoff/` (ba lệnh
    `git add` trong transcript, không có Edit/Write nào vào `~/.claude`) mà vẫn bị tính là
    ĐANG GIỮ vùng `tools/univ3`, chặn W02 mất 13 phút. Nguyên do: bản cũ quét THÔ chuỗi
    `"file_path"` trên raw transcript — mà `Read` cũng dùng đúng tên trường đó. W01 ĐỌC
    một tệp vé `~/.claude/worker-queue/...md` là lập tức "giữ" cả vùng công cụ.
    Cùng lỗi quét thô: `git add` được dò trên RAW (gồm cả KẾT QUẢ lệnh) nên chữ
    "git add <đường dẫn cụ thể>" trong tài liệu worker vừa `cat` ra cũng đẻ vùng ma
    (đo trên W02: vùng `([^`, `vùng`, `ra`, `src/app/pipeline`).

    NAY: chỉ đọc khối `tool_use` do CHÍNH agent phát, và chỉ lấy:
      · `file_path` của Edit/Write/MultiEdit/NotebookEdit — GHI thật;
      · lệnh Bash có `git add`, chuyển hướng `>`/`>>`, `tee` — cũng là GHI thật.
    Độ chặt phía GHI KHÔNG hề nới (bài học 26/08 hai worker cùng ghi `src/lib/fulfill`):
    trước chỉ bắt `git add`, nay bắt thêm cả `>`/`tee`.

    W18 09/09/2026: thêm chiều THỜI GIAN — xem khối WHY ngay trên đầu hàm.
    """
    try:
        size = os.path.getsize(jl)
        with open(jl, "rb") as fh:
            fh.seek(max(0, size - VUNG_TAIL))
            raw = fh.read().decode("utf-8", "replace")
    except Exception:
        # W64 04/09/2026 — KHÔNG ĐỌC ĐƯỢC ≠ KHÔNG GIỮ GÌ. Bản cũ trả tập rỗng, tức
        # tuyên bố chắc nịch "worker này không ghi vào đâu cả" trong khi thật ra vừa mù.
        # Cổng đọc tập rỗng -> cho worker thứ hai vào cùng vùng = ca gãy build 26/08.
        # Nay trả một CỜ MÙ, `doi_chieu_vung` coi nó đụng MỌI vùng -> chặn kèm lời nói rõ.
        return {KHONG_DO}
    ghi = {}                 # vùng -> mốc epoch lần GHI cuối vào chính vùng đó
    moc_ban_giao = 0.0       # mốc epoch lệnh commit/deploy gần nhất
    moc_lenh_cuoi = 0.0      # mốc epoch tool_use gần nhất (bất kể loại)
    moc_ngoi_cho = 0.0       # mốc epoch lệnh NGỒI CANH gần nhất
    # Chỉ bỏ dòng đầu khi ĐÃ CẮT theo byte (dòng đó cụt, `json.loads` hỏng). Transcript
    # ngắn hơn VUNG_TAIL thì dòng đầu vẫn nguyên — bỏ là mất luôn Edit đầu tiên của worker.
    dong_ds = raw.split("\n")
    for dong in (dong_ds[1:] if size > VUNG_TAIL else dong_ds):
        if '"tool_use"' not in dong:
            continue
        # W64: thêm `"command"` — lệnh giành TÀI NGUYÊN (`playwright test`, `prisma
        # generate`, `pnpm dev`) không có `file_path` cũng chẳng có `>`/`tee`, bản cũ
        # loại nó ngay ở đây nên cổng không bao giờ nhìn thấy.
        if '"file_path"' not in dong and "git add" not in dong \
                and ">" not in dong and "tee " not in dong and '"command"' not in dong:
            continue
        try:
            o = json.loads(dong)
        except Exception:
            continue
        if o.get("type") != "assistant":
            continue
        _t = None
        for c in ((o.get("message") or {}).get("content") or []):
            if not isinstance(c, dict) or c.get("type") != "tool_use":
                continue
            if _t is None:
                _t = _moc_ban_ghi(o)
            moc_lenh_cuoi = max(moc_lenh_cuoi, _t)
            ten = str(c.get("name") or "")
            inp = c.get("input") if isinstance(c.get("input"), dict) else {}
            vs = set()
            if ten in GHI_TOOL:
                vs.add(chuan_vung(str(inp.get("file_path") or "")))
                for e in (inp.get("edits") or []):
                    if isinstance(e, dict) and e.get("file_path"):
                        vs.add(chuan_vung(str(e["file_path"])))
            elif ten in ("Bash", "BashOutput"):
                _cmd = str(inp.get("command") or "")
                for d in _duong_ghi_bash(_cmd):
                    vs.add(chuan_vung(d))
                # W64: tài nguyên dùng chung (kho dữ liệu thử, máy chủ thử, client
                # Prisma, thư mục dựng) — thứ hai worker phá nhau mà KHÔNG chung tệp mã.
                vs |= tai_nguyen_tu_lenh(_cmd)
                if RX_QUA_CHANG_GHI.search(_cmd):
                    moc_ban_giao = max(moc_ban_giao, _t)
                if RX_NGOI_CHO.search(_cmd):
                    moc_ngoi_cho = max(moc_ngoi_cho, _t)
            for v in vs:
                if v:
                    ghi[v] = max(ghi.get(v, 0.0), _t)
    if tat_ca:
        return {v for v in ghi if v}
    # Lệnh CUỐI CÙNG của worker là vòng canh -> nó đang ngồi chờ, không phải đang làm.
    ngoi_cho = bool(moc_ngoi_cho) and moc_ngoi_cho >= moc_lenh_cuoi
    bay_gio = time.time()
    con = set()
    for v, t in ghi.items():
        if not v:
            continue
        im = (bay_gio - t) / 60.0
        ban_giao = moc_ban_giao >= t          # commit/deploy SAU lần ghi cuối vào vùng này
        nguong = VUNG_IM_CHO_PHUT if (ban_giao and ngoi_cho) else VUNG_IM_PHUT
        if im < nguong:
            con.add(v)                        # còn ghi gần đây -> GIỮ, không nới một giây
            continue
        if v.startswith(TN_TIEN_TO):
            # Tài nguyên (cổng 3000, kho dữ liệu thử, thư mục dựng): không commit được,
            # nên chỉ đòi im đủ lâu. Dưới ngưỡng đầy đủ thì vẫn phải có mốc bàn giao.
            if im >= VUNG_IM_PHUT or ban_giao:
                continue
            con.add(v)
            continue
        if ban_giao:
            continue                          # đã commit/deploy -> không còn phần dở
        con.add(v)
    return con


_PCS_NHO = {"luc": 0.0, "khoa": None, "ra": None}
# sessionId -> {pid} của tiến trình đang sống, `_phien_con_song_do` điền mỗi lần đo.
_PID_CUA_PHIEN = {}
_MO_NHO = {"luc": 0.0, "ra": None}


def phien_mo_luc():
    """{sessionId: giờ khởi động TIẾN TRÌNH (epoch giây)} của các phiên còn sống.

    W35 28/10/2026 (Task-28102026-36) — PHIÊN SỐNG LẠI CÙNG MÃ, THỢ CŨ ĐÃ CHẾT.
    13:18 phiên chính được mở lại bằng `claude --continue`: tiến trình mới (pid 1235) mang
    ĐÚNG sessionId cũ, nên phép «phiên cha còn sống» trả SỐNG cho cả năm thợ W11/W13/W15/
    W17/W19 thả từ tiến trình trước — mà thợ chạy BÊN TRONG tiến trình cha, tiến trình cũ
    chết là chúng chết theo. Harness không ghi notification kết thúc -> năm con ma chiếm
    trần 5 (`DANG_CHAY=9`), vé 97b6476f3a kẹt 2h35 sau `cho_worker: W19`. Đọc giờ khởi
    động bằng `ps` chứ không bằng `startedAt` trong sổ phiên: không rõ harness có ghi lại
    trường đó khi đổi mã phiên giữa chừng (compact) hay không, còn giờ của tiến trình thì
    hệ điều hành giữ, không ai ghi đè được.
    """
    if time.time() - _MO_NHO["luc"] < 3 and _MO_NHO["ra"] is not None:
        return dict(_MO_NHO["ra"])
    phien_con_song()
    pid_sid = {p: sid for sid, ps in _PID_CUA_PHIEN.items() for p in ps}
    ra = {}
    if pid_sid:
        try:
            out = subprocess.run(
                ["ps", "-o", "pid=,lstart=", "-p", ",".join(str(p) for p in pid_sid)],
                capture_output=True, text=True, timeout=5,
                env=dict(os.environ, LC_ALL="C", LANG="C")).stdout
        except Exception:
            out = ""
        for dong in out.splitlines():
            m = re.match(r"\s*(\d+)\s+(.+?)\s*$", dong)
            if not m or int(m.group(1)) not in pid_sid:
                continue
            try:
                t = time.mktime(time.strptime(m.group(2), "%a %b %d %H:%M:%S %Y"))
            except ValueError:
                continue
            sid = pid_sid[int(m.group(1))]
            ra[sid] = min(t, ra.get(sid, t))   # nhiều pid một mã -> lấy con mở sớm nhất
    _MO_NHO.update(luc=time.time(), ra=ra)
    return dict(ra)


def cha_con_giu(ds):
    """Còn tiến trình phiên cha nào có thể đang chạy agent này không? None = không đo được.

    `ds` = [tệp transcript THẬT, *symlink ở phiên nối tiếp] (như `gom_theo_agent`).
    Agent chỉ sống khi MỘT phiên cha của nó còn tiến trình VÀ tiến trình đó đã mở TRƯỚC lần
    ghi cuối của agent — agent ghi transcript ngay lúc được thả, nên tiến trình mở SAU lần
    ghi cuối không thể là kẻ đang chạy nó (ca 13:18 28/10, xem `phien_mo_luc`). Không đo
    được giờ mở -> coi là còn giữ: phán sống thừa chỉ chậm một nhịp, phán chết oan là mất việc.
    """
    song = phien_con_song()
    if song is None or not ds:
        return None
    try:
        mt = os.path.getmtime(ds[0])
    except OSError:
        mt = None
    mo = phien_mo_luc() if mt is not None else {}
    for d in ds:
        sid = os.path.basename(os.path.dirname(os.path.dirname(d)))
        if sid not in song:
            continue
        st = mo.get(sid)
        if st is None or mt is None or mt >= st - 5:
            return True
    return False


def phien_con_song():
    """Bản nhớ đệm 3 giây của `_phien_con_song_do` — bảng gọi một lần cho MỖI agent (1460 lần/
    lượt đo 17/10, 0,84 giây chỉ để đọc lại cùng mấy tệp sổ phiên)."""
    khoa = (os.environ.get("CLAUDE_HOME"), os.environ.get("CLAUDE_CONFIG_DIR"),
            os.environ.get("UNIV3_PROJECTS_ROOT"))
    if _PCS_NHO["khoa"] == khoa and time.time() - _PCS_NHO["luc"] < 3:
        r = _PCS_NHO["ra"]
        return set(r) if r is not None else None
    r = _phien_con_song_do()
    _PCS_NHO.update(luc=time.time(), khoa=khoa, ra=r)
    return set(r) if r is not None else None


def _phien_con_song_do():
    """set sessionId của các phiên Claude còn tiến trình sống; None = không đo được.

    01/10/2026: founder thoát phiên để cập nhật Claude -> mọi subagent chết theo phiên cha,
    nhưng harness không kịp ghi notification kết thúc vào transcript cha, nên cổng vẫn đếm
    ba thợ ma là ĐANG CHẠY tới trần cứng 6 tiếng: chiếm trần, giữ vùng, chặn thả lại đúng
    ba việc đó. Harness ghi `~/.claude/sessions/<pid>.json` cho mỗi phiên đang mở — pid
    không còn thì phiên đó đã chết, kéo theo mọi subagent của nó.
    """
    nha = os.environ.get("CLAUDE_HOME") or os.path.expanduser("~/.claude")
    # W08 17/10/2026 (Task-17102026-03) — SỔ PHIÊN NẰM Ở THƯ MỤC CẤU HÌNH CỦA TÀI KHOẢN.
    # Máy anh chạy nhiều tài khoản: `CLAUDE_CONFIG_DIR=~/.claude-acc-acc3`, harness ghi
    # `~/.claude-acc-acc3/sessions/<pid>.json`, còn `projects/` là symlink sang
    # `~/.claude/projects`. Bản cũ chỉ đọc `~/.claude/sessions` -> thấy MỖI phiên của dự án
    # khác (NHATRANGdream) -> mọi phiên ChicHub bị coi là chết. Đo 09:2x 17/10: `quet_agent`
    # trả `song=[]` trong khi W04/W06/W07/W08 đang chạy; `dong_bo_trang_thai` vì thế ghi
    # `done` cho thợ còn sống (W04, W01, W03 sáng nay) -> thợ chết thật sau đó bị che là «xong».
    # Gộp MỌI thư mục cấu hình: phán SỐNG thừa chỉ làm chậm một nhịp, phán CHẾT oan là mất việc.
    cac_nha = [nha]
    if os.environ.get("CLAUDE_CONFIG_DIR"):
        cac_nha.append(os.environ["CLAUDE_CONFIG_DIR"])
    if not os.environ.get("CLAUDE_HOME"):
        cac_nha += sorted(glob.glob(os.path.expanduser("~/.claude-acc-*")))
    cac_nha = list(dict.fromkeys(os.path.abspath(os.path.expanduser(x)) for x in cac_nha))
    # Gốc transcript bị đổi (hộp cát ca thử) mà sổ phiên không đi theo -> hai nguồn không
    # cùng một thế giới, không được dùng sổ phiên thật để khai tử agent giả.
    goc_tx = os.environ.get("UNIV3_PROJECTS_ROOT")
    if goc_tx and os.path.realpath(goc_tx) not in {
            os.path.realpath(os.path.join(x, "projects")) for x in cac_nha}:
        return None
    ra = set()
    _PID_CUA_PHIEN.clear()
    doc_duoc = False
    for _nha in cac_nha:
        d = os.path.join(_nha, "sessions")
        try:
            ten = os.listdir(d)
        except OSError:
            continue
        doc_duoc = True
        for n in ten:
            if not n.endswith(".json") or not n[:-5].isdigit():
                continue
            try:
                os.kill(int(n[:-5]), 0)
            except ProcessLookupError:
                continue
            except OSError:
                pass
            try:
                with open(os.path.join(d, n), encoding="utf-8") as fh:
                    sid = json.load(fh).get("sessionId")
            except Exception:
                continue
            if sid:
                ra.add(str(sid))
                _PID_CUA_PHIEN.setdefault(str(sid), set()).add(int(n[:-5]))
    if not doc_duoc:
        return None
    # Phiên đang chạy hook này chắc chắn còn sống (harness tự khai qua biến môi trường).
    if os.environ.get("CLAUDE_CODE_SESSION_ID") and not goc_tx:
        ra.add(os.environ["CLAUDE_CODE_SESSION_ID"])
    # Hook luôn chạy bên trong một phiên đang sống -> tập rỗng nghĩa là đọc hỏng, không
    # phải "mọi phiên đều chết"; trả None để không giết oan cả bảng.
    return ra or None


def running_workers(cwd: str):
    """(dang_chay, xac_treo) — mỗi phần tử là (tuoi_phut, agent_id, mo_ta).

    Cả hai đều nằm trong cửa sổ ACTIVE_MIN; khác nhau ở chỗ xác treo ĐÃ trả báo cáo cuối
    nên KHÔNG được tính vào trần (xem docstring đầu tệp).
    """
    root = project_dir(cwd)
    if not root:
        return [], []
    now = time.time()
    song, xac = [], []
    _chet = {}      # {phiên: {agent_id: trạng thái}} — harness đã báo kết thúc
    _song_ids = phien_con_song()
    # Gom theo agent id: phiên cha nối tiếp thì harness đặt SYMLINK sang transcript thật ở
    # phiên cũ, glob khớp cả hai -> MỘT worker chiếm HAI chỗ trong trần (28/8: trần đếm 5
    # khi chỉ có 4 con sống, con thứ 5 bị chặn oan). Tệp thật đứng đầu, các đường dẫn còn
    # lại chỉ để biết agent thuộc phiên cha nào mà hỏi notification kết thúc.
    _gom = {}
    for _jl in sorted(glob.glob(os.path.join(root, "*", "subagents", "agent-*.jsonl"))):
        _aid = os.path.basename(_jl)[len("agent-"):-len(".jsonl")]
        _ds = _gom.setdefault(_aid, [])
        (_ds.insert(0, _jl) if not os.path.islink(_jl) else _ds.append(_jl))
    for aid, ds in _gom.items():
        jl = ds[0]
        try:
            age = (now - os.path.getmtime(jl)) / 60.0
        except OSError:
            continue
        desc = ""
        try:
            with open(jl[:-len(".jsonl")] + ".meta.json", encoding="utf-8") as fh:
                desc = str(json.load(fh).get("description") or "")
        except Exception:
            pass
        # Worker BỊ GIẾT mà lượt cuối đang gọi tool thì `da_tra_bao_cao` trả False ->
        # bản cũ đếm nó là ĐANG CHẠY, chiếm chỗ trong trần dù đã chết (27/8: 2 con chết
        # vẫn giữ chỗ). Hỏi thẳng harness qua `worker_relapse.ids_ket_thuc`.
        # Hỏi MỌI phiên cha của agent: notification chỉ nằm ở phiên đã thả nó, mà qua
        # symlink agent còn xuất hiện ở phiên nối tiếp (phiên đó không có notification).
        #
        # ── W64 04/09/2026 — HỎI HARNESS TRƯỚC, `mtime` CHỈ LÀ ĐƯỜNG LUI (chỗ Đỏ Đ5) ──
        # BẢN CŨ SAI THẾ NÀO: cắt theo `mtime > ACTIVE_MIN` (15 phút) NGAY TRƯỚC khối này,
        # nên worker đang chạy MỘT lệnh dài mà không ghi transcript (build 2 app, `wlock
        # wait deploy` ~1 tiếng) bị phán chết trong khi harness vẫn nói nó CHƯA kết thúc.
        # Danh sách này là nguồn của `worker_queue.vung_dang_giu()` -> khoá vùng bị nhả ->
        # worker thứ hai được thả vào cùng tệp = đúng ca gãy build 26/08.
        # `WR.ids_ket_thuc()` trả None = KHÔNG ĐỌC ĐƯỢC, khác hẳn tập rỗng = "chưa ai kết
        # thúc". Bản cũ viết `or {}` gộp hai cái đó làm một — chính cái bệnh của cả lô này.
        ket, chac = False, False
        if WR is not None:
            for _d in ds:
                phien = os.path.dirname(os.path.dirname(_d)) + ".jsonl"
                if phien not in _chet:
                    try:
                        _chet[phien] = WR.ids_ket_thuc(phien)
                    except Exception:
                        _chet[phien] = None
                if _chet[phien] is None:
                    continue                # phiên này mất nguồn -> không kết luận gì
                chac = True
                if aid in _chet[phien]:
                    ket = True
                    break
        # `khong_ro` = mất nguồn tất định VÀ transcript đã nguội: KHÔNG được kết luận là
        # chết. Bản trước của chính W64 vẫn `continue` ở đây, tức "không đo được -> nhả
        # khoá" — đúng cái nếp mà cả lô này sinh ra để dẹp. Nhả nhầm tệ hơn giữ thừa:
        # giữ thừa thì một việc phải chờ, nhả nhầm thì hai worker ghi đè nhau.
        # Không phiên cha nào của agent còn tiến trình -> agent đã chết theo phiên cha.
        # W35 28/10: phiên cha mở lại cùng mã (`--continue`) cũng là phiên cha đã chết.
        if not ket and _song_ids is not None and cha_con_giu(ds) is False:
            ket = True
        khong_ro = False
        if ket:
            if age > ACTIVE_MIN:
                continue                    # xác cũ: giữ nguyên lưới cũ, khỏi liệt kê
        elif chac:
            if age > SONG_TOI_DA:
                continue                    # trần cứng chống xác treo vĩnh viễn
        elif age > ACTIVE_MIN:
            if age > SONG_TOI_DA:
                continue                    # quá trần cứng thì mới chịu buông
            khong_ro = True
        # Phần tử thứ 5 = số phút từ `tool_use` cuối. Harness đã báo kết thúc (`ket`) thì
        # ghi -1: `TaskStop` lúc đó là lệnh rỗng, không có gì để tắt oan.
        _pl = -1.0 if ket else phut_tu_lenh_cuoi(jl)
        # Phần tử thứ 6 = cờ KHÔNG RÕ. Xếp vào `xac` để KHÔNG chiếm chỗ trong trần (không
        # chặn oan con thứ 5), nhưng `vung_dang_giu()` vẫn đếm nó là ĐANG GIỮ vùng.
        (xac if (ket or khong_ro or da_tra_bao_cao(jl)) else song).append(
            (age, aid, desc, vung_worker(jl), _pl, khong_ro))
    song.sort()
    xac.sort()
    return song, xac


def dem_ba_so(cwd: str):
    """(dang_chay, tran, xac, khong_ro, nguon) — MỘT nguồn sự thật duy nhất.

    W23 05/09/2026 (lỗi A, phiếu P-DEM-DUNG-05092026) — AC-A3/AC-A4: cổng trần
    (`running_workers`, hàm NGAY TRÊN) và bảng worker (`worker_board.py --dem`)
    phải đọc CHUNG một hàm, không tự đếm riêng bằng ngưỡng khác nhau — đúng bệnh
    "cổng nói đủ trần 5, bảng nói còn 1 chỗ" đã bắt được ở §4.1. `xac` ở đây gồm
    cả worker đã trả báo cáo (`ket`) lẫn "trông như xong" (`da_tra_bao_cao`);
    `khong_ro` tách riêng phần tử thứ 6 (`khong_ro=True`) của `running_workers`
    — mất nguồn tất định, KHÔNG suy ra là đã chết.
    """
    # KHÔNG ĐO ĐƯỢC phải khác KHÔNG CÓ AI. `running_workers` trả ([], []) cả khi
    # `project_dir(cwd)` không tra ra thư mục transcript nào — người gọi đứng ở thư mục
    # khác là ra 0 worker trong khi máy đang chạy 5 con (đo thật 07/09/2026 19:33).
    if project_dir(cwd) is None:
        return 0, MAX_WORKERS, 0, 0, "khong-do-duoc"
    song, xac = running_workers(cwd)
    khong_ro_n = sum(1 for w in xac if w[5])
    xac_thuc = len(xac) - khong_ro_n
    nguon = "harness" if WR is not None else "transcript"
    # W127: số đầu = số CHIẾM TRẦN (thợ chỉ ngồi chờ lô deploy không tính) — cùng
    # `so_tinh_tran` mà cổng thả dùng, để bảng và cổng không bao giờ ra hai đáp án.
    return so_tinh_tran(song, cwd), MAX_WORKERS, xac_thuc, khong_ro_n, nguon


# ── W127 09/10/2026 — THỢ CHỈ CHỜ LÔ DEPLOY KHÔNG CHIẾM TRẦN ─────────────────────────
# CA THẬT 18:00–18:37 (anh Thành: «35 PHÚT ĐÉO THẢ RA»): 4/5 chỗ trong trần bị giữ bởi
# thợ ĐÃ commit + ĐÃ đăng ký vé `deploy-batch.sh register`, chỉ ngồi `sleep` chờ lô deploy
# (chain.log: lô 17:51 mất 19p57s, rồi lô nối tiếp #1, #2, lô 18:22 mất 11p). Bảng ghi
# «đang xếp hàng deploy» 82–98% suốt ~30 phút, trong khi hàng chờ có 4 vé không thả được
# vì «đủ trần 5». Trần 5 sinh ra để giữ máy founder không quá tải (25/08: load 566) và
# để hai thợ không ghi đè nhau — thợ ngồi chờ lô không làm nặng máy (bản dựng chạy trên
# máy chủ dưới tên `deploy-batch`, không phải tên thợ) và vùng tệp của nó VẪN được tính
# là đang giữ (`running_workers` không đổi), nên tách nó khỏi trần không mở lỗ nào.
# Thợ chờ lô có TRẦN RIÊNG `MAX_CHO_DEPLOY`; quá trần riêng thì phần dư lại tính vào trần
# chính — tổng thợ sống không bao giờ vượt MAX_WORKERS + MAX_CHO_DEPLOY.
MAX_CHO_DEPLOY = int(os.environ.get("UNIV3_WORKER_MAX_CHO_DEPLOY", "5"))
DQ_ROOT = os.environ.get("UNIV3_DEPLOY_QUEUE_ROOT") or os.path.join(
    os.environ.get("CLAUDE_HOME") or os.path.expanduser("~/.claude"), "deploy-queue")
WLOCK_ROOT = os.environ.get("WLOCK_ROOT") or os.path.join(
    os.environ.get("CLAUDE_HOME") or os.path.expanduser("~/.claude"), "worker-locks")
# Hai dấu vết của lượt đăng ký vé: dòng LỆNH (owner viết chữ) và dòng KẾT QUẢ mà
# `cmd_register` in ra (deploy-batch.sh:160) — kết quả bắt được cả khi lệnh dùng biến
# `--owner=$ME` mà không đọc được chữ.
RX_LENH_DANG_KY = re.compile(
    r"deploy-batch(?:\.sh)?\s+(?:register|reg)\b[^\n]*?--owner=[\"']?([A-Za-z0-9_.\-]+)")
RX_KQ_DANG_KY = re.compile(r"Đã đăng ký hàng chờ deploy:\s*([^\s@]+)\s*@\s*([0-9a-f]{7,40})")
# Sau khi đăng ký vé, thợ vẫn được soạn đồ NHẸ chờ lô (kịch bản chụp ảnh, ghi chú):
# docs/, thư mục tạm, tệp nháp bắt đầu bằng dấu chấm. GHI vào chỗ khác = đang code tiếp
# -> tính là đang làm (ca thật W120 11:21 viết `docs/anh-w120/w120-chup.mjs` lúc chờ).
RX_GHI_NHE = re.compile(r"(?:^|/)(?:docs|tmp|private/tmp|scratchpad)/|(?:^|/)\.[^/]+$")


def _jl_cua(cwd: str, aid: str):
    root = project_dir(cwd)
    if not root:
        return None
    ds = sorted(glob.glob(os.path.join(root, "*", "subagents", "agent-%s.jsonl" % aid)),
                key=lambda p: os.path.islink(p))
    return ds[0] if ds else None


def _ve_deploy_dang_cho():
    """{owner thường hoá: sha} của MỌI vé còn nằm trong `deploy-queue/*/pending` —
    vé đã lên web thì `deploy-batch.sh` dời sang `done/`, thợ hết diện chờ."""
    ra = {}
    for f in glob.glob(os.path.join(DQ_ROOT, "*", "pending", "*.json")):
        try:
            with open(f, encoding="utf-8") as fh:
                d = json.load(fh)
        except Exception:
            continue
        o = str(d.get("owner") or "").strip().lower()
        if o:
            ra[o] = str(d.get("sha") or "")
    return ra


def _chu_khoa():
    """Tên chủ của MỌI khoá wlock đang cầm (trừ `deploy-batch` — nó cầm hộ cả lô)."""
    ra = set()
    for f in glob.glob(os.path.join(WLOCK_ROOT, "*.lock", "owner")):
        try:
            o = open(f, encoding="utf-8").read().strip().lower()
        except Exception:
            continue
        if o and o != "deploy-batch":
            ra.add(o)
    return ra


def cho_deploy(w, cwd: str, _ve=None, _khoa=None) -> bool:
    """True = thợ CHỈ đang ngồi chờ lô deploy: (1) transcript có lượt đăng ký vé
    `deploy-batch.sh register` · (2) vé đó còn nằm trong `pending/` (chưa lên web) ·
    (3) không cầm khoá wlock nào (build/browser/devserver/dbdev/deploy) · (4) từ lúc đăng
    ký không GHI vào tệp mã (chỉ docs/ · tạm · nháp chấm). Thiếu một điều -> False (tính
    trần như cũ). Không đọc được transcript -> False: đếm dư rẻ hơn thả quá tải."""
    try:
        if w[5]:                      # khong_ro: đã nằm ngoài trần sẵn
            return False
        jl = _jl_cua(cwd, w[1])
        if not jl:
            return False
        ve = _ve_deploy_dang_cho() if _ve is None else _ve
        if not ve:
            return False
        size = os.path.getsize(jl)
        with open(jl, "rb") as fh:
            fh.seek(max(0, size - VUNG_TAIL))
            raw = fh.read().decode("utf-8", "replace")
    except Exception:
        return False
    owners, shas = set(), set()
    ghi_sau = False                    # có GHI tệp mã SAU lượt đăng ký cuối không
    dong_ds = raw.split("\n")
    for dong in (dong_ds[1:] if size > VUNG_TAIL else dong_ds):
        if "deploy-batch" not in dong and "đăng ký hàng chờ deploy" not in dong \
                and '"file_path"' not in dong:
            continue
        try:
            o = json.loads(dong)
        except Exception:
            continue
        for c in ((o.get("message") or {}).get("content") or []):
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_use":
                inp = c.get("input") if isinstance(c.get("input"), dict) else {}
                ten = str(c.get("name") or "")
                if ten in ("Bash", "BashOutput"):
                    m = RX_LENH_DANG_KY.search(str(inp.get("command") or ""))
                    if m and "$" not in m.group(1):
                        owners.add(m.group(1).lower())
                        ghi_sau = False
                elif ten in GHI_TOOL:
                    p = str(inp.get("file_path") or "")
                    if owners and p and not RX_GHI_NHE.search(p):
                        ghi_sau = True
            elif c.get("type") == "tool_result":
                nd = c.get("content")
                if isinstance(nd, list):
                    nd = " ".join(str(x.get("text") or "") for x in nd if isinstance(x, dict))
                for m in RX_KQ_DANG_KY.finditer(str(nd or "")):
                    owners.add(m.group(1).lower())
                    shas.add(m.group(2).lower())
                    ghi_sau = False
    if not owners or ghi_sau:
        return False
    con_ve = any(o in ve for o in owners) or any(
        s and any(v.startswith(s) or s.startswith(v[:7]) for v in ve.values() if v)
        for s in shas)
    if not con_ve:
        return False
    khoa = _chu_khoa() if _khoa is None else _khoa
    so = (_so_chuan_w(w[2]) or "").lower()
    if owners & khoa or (so and so in khoa):
        return False
    return True


def _so_chuan_w(desc: str) -> str:
    m = re.match(r"^\s*W0*(\d+)\b", str(desc or ""), re.I)
    return "w%d" % int(m.group(1)) if m else ""


def tach_cho_deploy(ws, cwd: str):
    """(đang_làm, chờ_deploy) — tách danh sách `song` của `running_workers`."""
    ve, khoa = _ve_deploy_dang_cho(), _chu_khoa()
    lam, cho = [], []
    for w in ws:
        (cho if (ve and cho_deploy(w, cwd, ve, khoa)) else lam).append(w)
    return lam, cho


# ── W140 09/10/2026 — NGƯỜI SOÁT CÓ TRẦN RIÊNG (Task-09102026-39, anh chọn 1A/3A) ────────
# Vai `nguoi-soat` (.claude/agents/nguoi-soat.md của dự án) soát lại việc ĐỤNG TIỀN / DỮ
# LIỆU THẬT / XƯỞNG trước khi tin báo xong bay đi. Nó chỉ đọc + chạy lệnh kiểm, không ghi
# tệp mã, nên không làm nặng máy như thợ dựng. Nếu đếm vào trần 5 thì mỗi việc tiền/xưởng
# chiếm 2 chỗ (thợ + soát) -> hàng chờ ứ đúng kiểu ca W127 18:00–18:37. Trần riêng
# `MAX_NGUOI_SOAT` (mặc định 2, giống cách W127 tách thợ chờ deploy); quá trần riêng thì
# phần dư tính vào trần chính — tổng sống ≤ MAX_WORKERS + MAX_CHO_DEPLOY + MAX_NGUOI_SOAT.
MAX_NGUOI_SOAT = int(os.environ.get("UNIV3_WORKER_MAX_NGUOI_SOAT", "2"))
VAI_SOAT = "nguoi-soat"


def la_nguoi_soat(w, cwd: str) -> bool:
    """True = worker này chạy vai `nguoi-soat` (đọc `agentType` trong .meta.json harness ghi)."""
    try:
        jl = _jl_cua(cwd, w[1])
        if not jl:
            return False
        with open(jl[:-len(".jsonl")] + ".meta.json", encoding="utf-8") as fh:
            return str(json.load(fh).get("agentType") or "") == VAI_SOAT
    except Exception:
        return False


def tach_tran(ws, cwd: str):
    """(đang_làm, chờ_deploy, người_soát) — ba nhóm rời nhau của danh sách `song`."""
    lam, cho = tach_cho_deploy(ws, cwd)
    soat = [w for w in lam if la_nguoi_soat(w, cwd)]
    lam = [w for w in lam if w not in soat]
    return lam, cho, soat


def so_tinh_tran(ws, cwd: str) -> int:
    """Số thợ CHIẾM TRẦN: thợ đang làm + phần thợ chờ deploy / người soát vượt trần riêng."""
    try:
        lam, cho, soat = tach_tran(ws, cwd)
    except Exception:
        return len(ws)
    return (len(lam) + max(0, len(cho) - MAX_CHO_DEPLOY)
            + max(0, len(soat) - MAX_NGUOI_SOAT))


_SO_DEM = {}


def _ngay_phien(goc_map: str, du_an: str):
    """(ngày làm việc, phiên) — bản Python của `wseq.sh ngay_lam_viec()/phien_hien()`.

    Đọc tệp chứ không gọi `wseq.sh`: `so_worker` chạy trong vòng lặp của bảng và của cổng,
    đẻ một tiến trình bash mỗi lượt là tự làm chậm khung gõ của founder.
    """
    ngay, phien = "", 1
    try:
        with open(os.path.join(goc_map, "%s.dau-ngay" % du_an), encoding="utf-8") as fh:
            dong = fh.read().split("\n")
        ngay = (dong[0].split() or [""])[0]
        if len(dong) > 1 and dong[1].strip().isdigit():
            phien = max(1, int(dong[1].strip()))
    except Exception:
        pass
    if not ngay:
        try:
            with open(os.path.join(goc_map, "%s.seq" % du_an), encoding="utf-8") as fh:
                ngay = (fh.readline().split() or [""])[0]
        except Exception:
            pass
    return ngay, phien


def _so_trong_so(cwd: str, desc: str) -> str:
    """Số W## mà SỔ đang ghi cho việc này, "" nếu sổ chưa có.

    Khoá tra = (slug, ngày làm việc, phiên) và LẤY DÒNG CUỐI khớp — y hệt
    `wseq.sh line_of_slug`, để MỌI nơi tra cùng một sổ không bao giờ ra hai số.

    ĐÂY LÀ LUẬT DUY NHẤT (W104, 15/09/2026). Trước đây `so_worker()` mở thêm một
    đường THỨ BA tự đọc `.map` bằng luật riêng — chỉ khớp slug, KHÔNG lọc ngày/phiên
    — nên khi khoá đầy đủ (slug, ngày, phiên) trượt, đường đó vẫn vồ bừa dòng CUỐI
    khớp slug của NGÀY/PHIÊN KHÁC, cấp nhầm số cũ cho việc hôm nay. Đo thật trên hộp
    cát: khoá chính trượt -> hàm này trả "" đúng luật, đường ba cũ trả "W07" của một
    dòng 5 ngày trước — LỆCH. Sổ số thật đang chạy (`~/.claude/worker-counter/*.map`)
    không có dòng nào lệch ngày/phiên với đầu-ngày hiện tại (đã quét toàn bộ 40 dòng),
    nên KHÔNG có ca thật nào cần "đỡ" bằng cách nới luật. `so_worker()` chỉ dùng số
    này làm NHÃN HIỂN THỊ trên bảng — trượt thì đã có lưới an toàn "trả TÊN VIỆC"
    ngay sau, không mất task nào. Quyết định: SIẾT — mọi nơi gọi lại ĐÚNG hàm này,
    không mở luật lỏng hơn ở bất kỳ đâu.
    """
    slug = _slug_cua(desc)
    if not slug:
        return ""
    goc_map = os.path.expanduser(os.environ.get("WSEQ_ROOT", "~/.claude/worker-counter"))
    du_an = _du_an_cua(cwd)
    duong = os.path.join(goc_map, "%s.map" % du_an)
    try:
        moc = os.path.getmtime(duong)
    except OSError:
        return ""
    hit = _SO_DEM.get(duong)
    if not hit or hit[0] != moc:
        ngay, phien = _ngay_phien(goc_map, du_an)
        bang_so = {}
        try:
            with open(duong, encoding="utf-8") as fh:
                for d in fh:
                    c = d.rstrip("\n").split("\037")
                    if len(c) < 2:
                        continue
                    if ngay and len(c) >= 6 and c[5] and c[5] != ngay:
                        continue
                    p = int(c[6]) if len(c) >= 7 and c[6].strip().isdigit() else 1
                    if p != phien:
                        continue
                    bang_so[c[1]] = c[0]
        except Exception:
            return ""
        hit = (moc, bang_so)
        _SO_DEM[duong] = hit
    return hit[1].get(slug, "")


def so_worker(w, cwd: str) -> str:
    """Worker đang giữ vùng -> SỐ W## founder đọc được, không phải id agent.

    WHY: vé xếp hàng ghi "chờ ab8f76152c371c1da nhả src/lib" thì founder nhìn bảng không
    biết đó là con nào — đúng thứ dãy số W## sinh ra để dẹp. Lấy số theo hai đường: số gõ
    sẵn đầu `description`, hoặc tra sổ `wseq` theo slug. Cả hai trượt thì trả TÊN VIỆC,
    id agent chỉ là nước cuối.
    """
    desc = w[2] or ""
    m = re.match(r"\s*(W\d+)\b", desc, re.I)
    # SỔ THẮNG SỐ GÕ TAY khi hai bên lệch (W15, 09/09/2026 — chốt C4 của P085).
    # WHY: cổng `chuan_hoa_so_day` đã kéo số về đúng dãy và GHI VÀO SỔ trước khi agent
    # chạy. Nếu vẫn để số gõ trong `description` thắng tuyệt đối như bản cũ
    # (`:1099-1102`) thì bản sửa chỉ có tác dụng khi harness áp được `updatedInput` —
    # nửa mắt xích đó KHÔNG đo được nếu không thả agent thật, nên cấm dựa vào nó.
    # Sổ không có dòng nào cho việc này -> giữ nguyên đường cũ, không đoán.
    so_so = _so_trong_so(cwd, desc)
    if so_so:
        return so_so
    if m:
        return m.group(1).upper()
    # ĐƯỜNG DỰ PHÒNG (W104, 15/09/2026): TRƯỚC đây tự đọc `.map` LẦN HAI bằng luật RIÊNG
    # (chỉ khớp slug, KHÔNG lọc ngày/phiên) — lệch luật với `wseq.sh line_of_slug` và với
    # `_so_trong_so` phía trên. Đo thật trên hộp cát: khoá chính (slug, ngày, phiên) trượt
    # -> hàm chính trả "" đúng luật, còn đường ba CŨ vồ bừa dòng cuối khớp slug của NGÀY
    # KHÁC (`W07` của 5 ngày trước) — LỆCH. Quét sổ số THẬT (`~/.claude/worker-counter/
    # *.map`, 40 dòng, 15/09/2026) không có ca nào lệch ngày/phiên đang "running" cần
    # "đỡ" — quyết định SIẾT: gọi lại ĐÚNG hàm chính, không mở khoá lỏng hơn. Vẫn giữ
    # một lượt gọi tường minh (không gộp chung dòng `so_so` phía trên) để: (1) mọi ca
    # thử "che đường thứ ba" bắt được ĐÚNG nhánh này đang chạy (dòng vết debug dưới),
    # (2) tự chữa lành nếu `.map` vừa được ghi thêm GIỮA hai lượt gọi (cache theo mtime
    # trong `_so_trong_so` tự phát hiện tệp đổi). Trượt cả hai -> lưới an toàn cuối
    # "trả TÊN VIỆC" (không phải id agent) — CHỈ đổi NHÃN HIỂN THỊ, không mất task.
    if os.environ.get("W104_VET_DUONG_DU_PHONG"):
        print("VET: so_worker() da chay vao duong du phong cho slug=%r"
              % _slug_cua(desc), file=sys.stderr)
    so_du_phong = _so_trong_so(cwd, desc)
    if so_du_phong:
        return so_du_phong
    return (desc.strip()[:28] or w[1])


# =============== CHUẨN HOÁ SỐ W## SAI DÃY (P085 §7B.7, chốt C4) =================
# LUẬT CỨNG — ĐỌC TRƯỚC KHI SỬA CỤM NÀY:
#   Cơ chế này CHỈ ĐƯỢC sửa số rồi CHO LỆNH CHẠY TIẾP. CẤM mọi nhánh làm mất việc vì lý
#   do số sai dãy: cấm `deny`, cấm `permissionDecision: "ask"`, cấm `sys.exit(2)`.
#   Nguyên văn founder 09/09/2026: *"nếu thấy sai thì chặn lại và đổi lại số chuẩn rồi làm
#   việc thôi… mày chặn xong mất mẹ task của tao thì đúng số có được tác dụng lồn gì đâu???
#   quan trọng là task. definition of done là task đúng số."*
#   Không suy được số chuẩn -> KHÔNG ĐỤNG GÌ, chỉ ghi nhật ký. Im lặng còn hơn mất việc.
def _duong_nhat_ky_so() -> str:
    """Nhật ký chuẩn hoá số. Hộp cát (`WSEQ_ROOT` bị đổi) ghi vào CHÍNH hộp cát đó —
    không thì ca thử nhả dòng «SUA SO W131 -> W06» vào nhật ký thật, người đọc sau tưởng
    có worker thật bị đổi số."""
    goc = os.environ.get("WSEQ_ROOT")
    if goc and os.path.abspath(os.path.expanduser(goc)) != \
            os.path.abspath(os.path.expanduser("~/.claude/worker-counter")):
        return os.path.join(os.path.expanduser(goc), "so-worker-chuan-hoa.log")
    return os.path.expanduser("~/.claude/logs/so-worker-chuan-hoa.log")


def _wseq_chay(du_an, *dt):
    """Chạy `wseq.sh` và trả (mã thoát, stdout đã strip). Hỏng -> (99, "")."""
    try:
        r = subprocess.run(["bash", os.path.expanduser("~/.claude/universal-hooks/wseq.sh")]
                           + [str(x) for x in dt],
                           capture_output=True, text=True, timeout=15,
                           env=dict(os.environ, WSEQ_PROJECT=du_an))
        out = (r.stdout or "").strip()
        return r.returncode, (out.splitlines()[-1].strip() if out else "")
    except Exception:
        return 99, ""


def _ghi_so(dong: str):
    try:
        duong = _duong_nhat_ky_so()
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        with open(duong, "a", encoding="utf-8") as fh:
            fh.write("%s\t%s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), dong))
    except Exception:
        pass


def _du_an_cua(cwd: str) -> str:
    """Khoá sổ số — PHẢI ra cùng chuỗi mà `worker_queue.cap_so` và `worker_board` dùng."""
    try:
        import worker_queue as WQ
        return os.path.basename(WQ.goc_du_an(cwd).rstrip("/"))
    except Exception:
        return os.path.basename(os.path.abspath(cwd or ".").rstrip("/"))


def _slug_cua(desc: str) -> str:
    """Slug việc — PHẢI ra cùng chuỗi mà `worker_board.slug_hoa` dùng, nếu không sổ đẻ
    hai dòng cho một việc (bệnh "một việc hai số" đã ghi ở `worker_board.dong_bo_so`)."""
    try:
        import worker_board as WB
        return WB.slug_hoa(desc)
    except Exception:
        t = re.sub(r"^\s*W\d+\b", "", desc or "", flags=re.I).replace("worker-cap-ok", " ")
        return re.sub(r"[^a-z0-9]+", "-", khong_dau(t)).strip("-")


def _bo_dem_hien(du_an: str) -> int:
    """Giá trị bộ đếm của NGÀY LÀM VIỆC hiện tại; -1 nếu không đọc được.

    Đọc qua `wseq.sh bo-dem` chứ không tự parse `.seq`, để KHÔNG đẻ bản đo thứ hai về
    "hôm nay là ngày nào" (luật một cửa của `ngay_lam_viec()`)."""
    ma, ra = _wseq_chay(du_an, "bo-dem")
    try:
        return int(ra) if ma == 0 else -1
    except Exception:
        return -1


def chuan_hoa_so_day(desc: str, cwd: str):
    """Số W## gõ trong `description` -> (desc đã sửa, dòng báo). Không sửa -> (desc, "").

    Ba ca của §7B.7 — không có ca thứ tư nào từ chối việc:
      (a) số đang có chủ là worker KHÁC còn sống  -> lấy số kế tiếp của sổ
      (b) số vượt dãy (lớn hơn bộ đếm + 1)        -> lấy số kế tiếp của sổ
      (c) số hợp lệ                               -> giữ nguyên, chỉ ghi vào sổ

    Ca 09/09/2026 phải chữa được: bộ đếm nằm ở 134 (mốc ngày chưa mở lại) trong khi dãy
    trên màn hình là W11…W15. Số nhỏ hơn bộ đếm KHÔNG phải "sai dãy" — nó là dãy mới do
    điều phối mở; `wseq adopt` kéo bộ đếm về đúng chỗ đó (xem `wseq.sh cmd_adopt`).
    """
    d = desc or ""
    m = re.match(r"\s*W(\d+)\b", d, re.I)
    du_an = _du_an_cua(cwd)
    slug = _slug_cua(d)
    if not slug:
        return desc, ""
    if not m:
        # Không gõ số -> `worker_board.dong_bo_so` sẽ tự `next`. Không chen vào.
        return desc, ""
    n = int(m.group(1))
    # ĐO "VƯỢT DÃY" TRƯỚC KHI `adopt` — nếu adopt trước thì số W131 tự nhận được vào sổ
    # (nó chưa có chủ) rồi kéo luôn bộ đếm lên 131, tức cổng vừa hợp thức hoá đúng cái
    # số nó sinh ra để dẹp (đo được ở ca thử ① lượt đầu, 09/09/2026).
    bo_dem = _bo_dem_hien(du_an)
    # W01 14/09/2026 — NGƯỠNG "VƯỢT DÃY" PHẢI CHO ĐỦ MỘT LƯỢT THẢ, KHÔNG PHẢI +1.
    # Bản cũ coi mọi số > bộ đếm + 1 là "vượt dãy" rồi ép về `next`. Điều phối thả BỐN
    # việc trong CÙNG MỘT LƯỢT (bốn tool_use trong một message → bốn tiến trình hook), mỗi
    # con đọc `_bo_dem_hien()` NGOÀI khoá sổ nên cả bốn đều thấy dãy đang ở W00: W01/W02
    # qua được, còn W03 và W04 bị phán "vượt dãy" rồi ép về ĐÚNG MỘT số nhỏ nhất còn trống.
    # Nhật ký thật sáng 14/09 in liền hai dòng: `số đã đổi: W03 -> W01 — vượt dãy (dãy hôm
    # nay đang ở W00)` và `W04 -> W01 — vượt dãy` → ba việc khác nhau dán chung số W01,
    # bảng worker mất khả năng phân biệt (founder: *"VẪN TRÙNG???? CẢ TRÊN CẢ DƯỚI"*).
    # Nay nới ngưỡng đúng bằng TRẦN WORKER ĐỒNG THỜI: một lượt nhiều nhất thả `MAX_WORKERS` con
    # nên số cách bộ đếm tối đa `MAX_WORKERS` bậc vẫn là dãy hợp lệ của lượt này → cả bốn con đi
    # nhánh `adopt` và giữ ĐÚNG số mình gõ. Tính duy nhất KHÔNG dựa vào phép đo ngoài khoá
    # này nữa mà dựa vào `wseq adopt` → `number_taken()` chạy TRONG khoá sổ: số đã có chủ
    # thì adopt trả lỗi và luồng rơi xuống `next`. Số lạc dãy thật (vd W131 lúc dãy ở W00)
    # vẫn bị chặn vì 131 > 0 + 5.
    if bo_dem >= 0 and n > bo_dem + max(1, MAX_WORKERS):
        ma2, ra2 = _wseq_chay(du_an, "next", slug, d[:120])
        if ma2 != 0 or not re.match(r"^W\d+$", ra2 or ""):
            _ghi_so("KHONG SUY DUOC SO CHUAN (go W%d vuot day, slug=%s) -> GIU NGUYEN" % (n, slug))
            return desc, ""
        if int(ra2[1:]) == n:
            return desc, ""
        moi = re.sub(r"^\s*W\d+\b", "W%02d" % int(ra2[1:]), d, flags=re.I)
        _ghi_so("SUA SO W%d -> %s (vuot day, bo dem dang o %d) slug=%s" % (n, ra2, bo_dem, slug))
        return moi, ("số đã đổi: W%02d -> %s — vượt dãy (dãy hôm nay đang ở W%02d). "
                     "Việc vẫn chạy bình thường." % (n, ra2, bo_dem))
    # `W%02d` chứ không `W%d` — sổ ghi `W1` lẫn với `W01` thì cột SỐ của `wseq list` so le,
    # founder trỏ "W1" mà bảng hiện "W01" là mất đúng cái dãy số dùng để trỏ (P089).
    ma, ra = _wseq_chay(du_an, "adopt", slug, "W%02d" % n, d[:120])
    if ma == 0 and re.match(r"^W\d+$", ra or ""):
        cu = int(ra[1:])
        if cu == n:
            return desc, ""                      # ca (c) — sổ nhận đúng số đã gõ
        # slug này đã có số từ trước (vé xếp hàng / thả lại) -> số cũ THẮNG, giữ một dãy.
        moi = re.sub(r"^\s*W\d+\b", "W%02d" % cu, d, flags=re.I)
        _ghi_so("GIU SO CU %s (go W%d) slug=%s" % (ra, n, slug))
        return moi, ("số đã đổi: W%02d -> %s (việc này đã mang số đó trong sổ)" % (n, ra))
    ma2, ra2 = _wseq_chay(du_an, "next", slug, d[:120])
    if ma2 != 0 or not re.match(r"^W\d+$", ra2 or ""):
        _ghi_so("KHONG SUY DUOC SO CHUAN (go W%d, slug=%s) -> GIU NGUYEN, cho chay tiep" % (n, slug))
        return desc, ""                          # không đoán, và TUYỆT ĐỐI không chặn
    moi = re.sub(r"^\s*W\d+\b", "W%02d" % int(ra2[1:]), d, flags=re.I)
    ly = "trùng số worker đang sống"
    _ghi_so("SUA SO W%d -> %s (%s) slug=%s" % (n, ra2, ly, slug))
    return moi, "số đã đổi: W%02d -> %s — %s. Việc vẫn chạy bình thường." % (n, ra2, ly)


# ── DỌN SỐ MA — lượt thả bị cổng chặn không được giữ số (P089 O1.2) ─────────────────
# 7 hook khớp matcher `Agent` chạy ĐỘC LẬP. Hook này `allow` + `chuan_hoa_so_day` ghi số
# vào sổ, rồi `nhai_lai_gate` (tiến trình khác) `deny` — KHÔNG có worker nào ra đời nhưng
# dòng `running` nằm lại giữ số. Lượt thả lại bị `wseq number_taken()` coi là "số đang có
# chủ" nên bị đẩy sang số kế. Đo thật 10/09/2026, `~/.claude/logs/so-worker-chuan-hoa.log`:
#   11:56:11  SUA SO W1  -> W03 (trùng số worker đang sống) slug=trinh-sat-chi-doc-doi-sup
#   12:22:15  SUA SO W13 -> W14 (trùng số worker đang sống) slug=phan-bien-phieu-p089-...
# — trong khi phiên đó KHÔNG có `agent-*.meta.json` nào cho W1 lẫn W13 (8 tệp = đúng 8
# lượt thả THÀNH CÔNG, 7 lượt bị chặn đẻ 0 tệp).
#
# ORACLE dùng ở đây là TẤT ĐỊNH, không phải cửa sổ ân hạn phỏng đoán: trong transcript của
# phiên cha, mọi `tool_use` Task/Agent bị hook chặn đều có `tool_result` mang
# `is_error: true`. Lượt đó KHÔNG thành -> nhả số.
#
# HAI CHỐT AN TOÀN (thiếu một trong hai là nhả nhầm số của việc đang sống):
#   ① slug đang có AGENT SỐNG  -> KHÔNG nhả (lượt sau đã thả lại thành công cùng slug).
#   ② slug đang có VÉ HÀNG CHỜ -> KHÔNG nhả (vé giữ số từ lúc xếp hàng là ĐÚNG thiết kế).
# Hỏng bất cứ chỗ nào -> nuốt lỗi, giữ nguyên hành vi cũ (fail-open, ràng buộc §7.4).
_TAIL_TRANSCRIPT = int(os.environ.get("UNIV3_SO_MA_TAIL") or 3_000_000)


def _slug_luot_bi_chan(transcript_path: str):
    """{slug} của những lượt Task/Agent trong transcript cha đã bị hook `deny`.

    LƯỢT CUỐI CỦA SLUG THẮNG (W21, 10/09/2026). Bản cũ gom vào tập ngay khi thấy MỘT lượt
    lỗi và không bao giờ rút ra, nên slug bị chặn rồi THẢ LẠI THÀNH CÔNG vẫn nằm trong
    danh sách "đáng nhả". Hai chốt an toàn của `_don_so_ma` (đang có agent sống / đang có
    vé) chỉ che được sau khi transcript của agent mới đã hiện — trong khe đó số của một
    worker ĐANG SỐNG bị thu hồi. Đo được ở phép thử 2 của W21: sau lượt chặn `W01`, hai
    lượt sạch tiếp theo nhận `W01` và `W02` thay vì `W02`/`W03` — tức con thứ hai cướp
    đúng số của con thứ nhất.
    """
    ra, cho = set(), {}
    try:
        with open(transcript_path, "rb") as fh:
            try:
                fh.seek(-_TAIL_TRANSCRIPT, os.SEEK_END)
                fh.readline()          # bỏ dòng bị cắt dở
            except OSError:
                fh.seek(0)
            for raw in fh:
                if b'"tool_use"' not in raw and b'"tool_result"' not in raw:
                    continue
                try:
                    d = json.loads(raw.decode("utf-8", "replace"))
                except Exception:
                    continue
                c = (d.get("message") or {}).get("content")
                if not isinstance(c, list):
                    continue
                for b in c:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "tool_use" and b.get("name") in AGENT_TOOLS:
                        cho[b.get("id")] = str((b.get("input") or {}).get("description") or "")
                    elif b.get("type") == "tool_result" and b.get("tool_use_id") in cho:
                        mo_ta = cho.pop(b.get("tool_use_id"))
                        sl = _slug_cua(mo_ta)
                        if not sl:
                            continue
                        # Transcript đọc theo thứ tự thời gian -> gán/rút theo lượt CUỐI.
                        if b.get("is_error"):
                            ra.add(sl)
                        else:
                            ra.discard(sl)
    except Exception:
        return set()
    return ra


def _don_so_ma(cwd: str, transcript_path: str) -> None:
    if not transcript_path or os.environ.get("UNIV3_DON_SO_MA") == "0":
        return
    try:
        chan = _slug_luot_bi_chan(transcript_path)
        if not chan:
            return
        song = set()
        try:
            import worker_board as WB
            for w in running_workers(cwd)[0]:
                sl = WB.slug_hoa(str(w[2] or ""))
                if sl:
                    song.add(sl)
        except Exception:
            return          # không đo được "ai đang sống" -> KHÔNG dám nhả
        ve = set()
        try:
            if WQ is not None:
                ve = {v.get("slug") for v in WQ.doc(cwd) if v.get("slug")}
        except Exception:
            return          # không đọc được hàng chờ -> KHÔNG dám nhả
        du_an = _du_an_cua(cwd)
        for sl in sorted(chan - song - ve):
            ma, ra = _wseq_chay(du_an, "get", sl)
            if ma != 0 or not re.match(r"^W\d+$", ra or ""):
                continue
            ma2, ra2 = _wseq_chay(du_an, "nha", sl, "lượt thả bị cổng chặn (tool_result is_error)")
            if ma2 == 0:      # mã 3 = dòng đã `done`/đã nhả, không có gì để thu hồi -> im
                _ghi_so("NHA SO %s slug=%s (luot tha bi cong chan, khong co agent)" % (ra2 or ra, sl))
    except Exception:
        pass


def _ra_cho_qua(ti, desc, cwd, phu: str) -> int:
    """Lối ra CHO QUA của nhánh Agent — chuẩn hoá số W## rồi in output, KHÔNG chặn.

    Gom về một chỗ vì nhánh Agent có ba lối ra "cho qua" giống hệt nhau; ba bản sao là ba
    cơ hội quên đính `updatedInput`, mà quên thì số trên màn hình vẫn sai âm thầm.
    """
    try:
        moi, bao = chuan_hoa_so_day(desc, cwd)
    except Exception:
        moi, bao = desc, ""
    ctx = "\n\n".join(x for x in [(phu or "").strip(), bao] if x)
    ra = {"hookEventName": "PreToolUse"}
    if ctx:
        ra["additionalContext"] = ctx
    if moi != desc and isinstance(ti, dict):
        # A21 đo được 09/09/2026 (probe sống trên tool Bash): harness CÓ áp `updatedInput`
        # của PreToolUse. Nửa còn lại — `agent-*.meta.json` ghi bản đã sửa hay bản gốc —
        # KHÔNG đo được nếu không thả agent thật, nên số hiển thị KHÔNG được phép phụ
        # thuộc vào nó: `so_worker()` lấy số từ SỔ khi sổ đã ghi số khác (xem hàm đó).
        ra["permissionDecision"] = "allow"
        ra["permissionDecisionReason"] = ctx or "chuẩn hoá số worker"
        ra["updatedInput"] = dict(ti, description=moi)
    if len(ra) == 1:
        return 0
    json.dump({"hookSpecificOutput": ra}, sys.stdout, ensure_ascii=False)
    return 0


def khong_ro(w) -> bool:
    """Worker này ở trạng thái KHÔNG RÕ (mất nguồn tất định + transcript nguội)?

    Tuple cũ chỉ có 5 phần tử -> False, giữ tương thích với chỗ gọi chưa đổi.
    """
    return bool(w[5]) if len(w) > 5 else False


def _im_lenh(w):
    """Phút từ lệnh cuối của worker `w`. None = không đo được (tuple cũ 4 phần tử)."""
    return w[4] if len(w) > 4 else None


def bang(ws) -> str:
    return "\n".join("    - %-17s %-38s (im %.0f phút)" % (w[1], w[2] or "(không rõ)", w[0])
                     for w in ws)


HOW_TO = """LUẬT ĐIỀU PHỐI (rules/AGENTS-ORCH.md §Trần-worker):
  1. **Trần {cap} worker đồng thời / dự án.** Vượt trần thì XẾP HÀNG CHỜ — xong một mới
     thả một. Không có "thả trước rồi tính sau".
  2. **Việc mới trùng mảng với worker đang chạy -> `SendMessage` vào chính worker đó**,
     CẤM đẻ worker mới. Nó đã có sẵn ngữ cảnh, lại không tranh tệp với chính mình.
  3. **Một tệp/vùng chỉ MỘT worker được ghi tại một thời điểm** (nhất là CSS/JS/template
     dùng chung). Muốn sửa vùng người khác đang giữ -> chờ, hoặc nhờ chính worker đó làm.
  4. Worker phải **tự dọn tài nguyên nền** của mình khi xong (`http.server`, iOS Simulator,
     tiến trình nền). Lưới an toàn: `stale-server-reaper.sh`.
  5. **Worker đã trả báo cáo cuối VÀ im quá 5 phút không gọi lệnh nào = XONG, kill NGAY**
     (`TaskStop`), dù khung điều phối vẫn hiện `running`. Trạng thái đó là RÁC — để đấy thì
     mỗi thông báo nền lại đánh thức nó gửi lại đúng bản báo cáo cũ (25/8: 4 lần một con).
     **CẤM tắt con vừa gọi lệnh trong 5 phút gần đây**, dù nó có trả ra thứ trông như báo
     cáo: worker vừa nói vừa làm (29/8: W11 bị tắt lúc cách lệnh cuối 18 giây, đang gửi ảnh
     cho founder). Hook tự tách hai nhóm và chỉ khuyên tắt nhóm đã im — cứ đọc lời hook.
     Thợ mà harness ĐÃ báo kết thúc thì CLI đã tự đóng — KHÔNG cần `TaskStop` (P143 1A).
  6. **Cấm mỗi worker tự dựng một vòng `until ... sleep` canh cùng một tài nguyên, và CẤM
     dò chữ trong output khoá** — chờ khoá bằng ĐÚNG MỘT DÒNG:
     `bash ~/.claude/universal-hooks/wlock.sh wait deploy --owner=<slug> --pid=$$ || exit 75`
     (lệnh tự nằm chờ tới lượt; chỉ xét MÃ THOÁT 0/75, không đọc chữ. Khoá theo TÀI NGUYÊN
     nên script tên gì cũng bị chặn, không như `grep` theo tên script).

ĐI TIẾP NGAY BÂY GIỜ (chọn 1):
  a. Gửi việc vào một worker ở bảng trên: `SendMessage` kèm id/tên của nó.
  b. Xếp hàng: chờ một worker xong (notification sẽ báo) rồi mới thả con này.
  c. Việc thật sự độc lập và founder ĐÃ đồng ý chạy thêm -> thêm chuỗi `worker-cap-ok`
     vào `description`/`prompt`, hoặc chạy với `UNIV3_WORKER_MAX=<n>`."""


# 04/09/2026 (W55) — brief bắt worker LIỆT KÊ mà không bắt LƯU RA TỆP.
# Ca thật: W52 rà ra 11 đơn đã gửi xưởng bị nuốt chữ (nguy cơ xưởng in sai), chỉ ghi con số
# vào commit; W53 đi lấy thì không còn chỗ nào giữ. NHẮC thôi, KHÔNG chặn — brief nào cũng
# nhắc tới việc liệt kê, chặn là oan hàng loạt.
_RX_LIET_KE = re.compile(
    r"liet\s*ke|danh\s*sach|ra\s+(toan\s+bo|het|lai\s+toan)|quet\s+(toan\s+bo|het)|"
    r"dem\s+(toan\s+bo|het)|soi\s+toan\s+bo", re.I)
_RX_CO_LUU = re.compile(
    r"docs/handoff|ghi\s+ra\s+tep|luu\s+ra\s+tep|xuat\s+ra\s+tep|ghi\s+vao\s+tep|"
    r"\.txt\b|\.csv\b|\.json\b|\.md\b", re.I)


def nhac_luu_ds(desc: str, prompt: str) -> str:
    """Trả câu nhắc ('' = không cần nhắc). So trên bản BỎ DẤU để bắt cả brief viết có dấu."""
    try:
        van = khong_dau("%s\n%s" % (desc or "", prompt or ""))
    except Exception:
        return ""
    if not _RX_LIET_KE.search(van):
        return ""
    if _RX_CO_LUU.search(van):
        return ""
    return ("\n\n📌 NHẮC (không chặn): brief này bắt worker LIỆT KÊ / RÀ TOÀN BỘ nhưng KHÔNG "
            "có chỗ nào bắt GHI RA TỆP. Ca 04/09: W52 rà ra 11 đơn đã gửi xưởng bị nuốt chữ, "
            "chỉ ghi con số vào commit — lô sau đi tìm thì không còn chỗ nào giữ. Thêm một "
            "dòng vào brief: «ghi đầy đủ ra `docs/handoff/<tên-việc>-<ngày>.txt` và nêu "
            "đường dẫn đó trong báo cáo cuối».")


# Ba ô TRẠNG THÁI của vé — KHÔNG gồm description/prompt (xem WHY ở `worker_queue`).
# Giữ ở đây vì còn dùng để IN nội dung ba ô đó trong khối ⛔, không phải để đo.
_O_TRANG_THAI = ("nhan_cuoi", "ban_giao", "dau_vet")


def _cho_founder_gat(v) -> bool:
    """Vé có trạng thái dở dang tự khai đang chờ founder gật? (fail-open: lỗi -> False)

    W08 13/09/2026 — MỘT NGUỒN ĐẾM: phép đo (`_RX_CHO_GAT` + ba ô trạng thái) đã DỜI sang
    `worker_queue._cho_founder_gat` và nằm TRONG `WQ.cho_founder()`, nên `WQ.ve_tha_duoc()`
    — đường mà cổng `Stop` (`ve_de_sau_gate`) dùng — tự loại vé này. Ở đây chỉ HỎI LẠI để
    in khối ⛔, KHÔNG tính lại: bản cũ đo riêng một chỗ chính là lý do bảng nói "⏸ chờ
    founder gật" mà cổng `Stop` vẫn in "không chờ founder" cho cùng một vé.
    """
    try:
        return bool(WQ._cho_founder_gat(v))      # WQ=None -> AttributeError -> False
    except Exception:
        return False


# ══════ SỐ HIỆU VIỆC LÚC THẢ THỢ (P114 hướng A, W39 01/10/2026) ══════════════════════════
# VÌ SAO: một việc mang sáu tên ở sáu sổ, không sổ nào trỏ sang sổ nào (phiếu P114 §5.3) —
# `W##` cấp lại trong ngày (`.map` 30/09: W27 ba lần), vé chỉ có mã băm, sổ lệnh chỉ có L##.
# Trường `VIEC:` là sợi chỉ nối: brief khai `VIEC: 20261001-L05.1` (hoặc gọn `VIEC: L05.1`
# = hôm nay), cổng DoR đo ĐÚNG mục đó (`dod.cong_dor`), commit mang trailer `Viec=…`, báo
# cáo thợ chép lại, `viec_state.py --mat-xich` gộp thành bảng.
# CỐ Ý HẸP để không thành cửa phải lách:
#   · cháu (lượt gọi có `agent_id`) và thợ CHỈ ĐỌC (`GHI: -`) -> miễn;
#   · dự án CHƯA TỪNG có sổ lệnh -> không có số để khai -> miễn;
#   · vé cũ trong hàng chờ chưa có dòng `VIEC:` -> cho qua kèm nhắc (tương thích ngược);
#   · việc không sinh từ lệnh Dev -> `VIEC: ngoai-so — <lý do ≥15 ký tự>` (đếm riêng trên bảng).
# Tắt khẩn: UNIV3_VIEC_BAT_BUOC=0.
def _cong_viec(cwd, desc, prompt, ti, nguon_vung, agent_id):
    """(lời chặn, lời nhắc) — cả hai rỗng = cho qua im lặng. Fail-open mọi lỗi."""
    try:
        if os.environ.get("UNIV3_VIEC_BAT_BUOC", "1") == "0":
            return "", ""
        if agent_id or nguon_vung == "khai-rong":
            return "", ""
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import so_lenh as SL
        goc_du_an = os.path.join(SL.goc_so(), SL.ten_du_an(cwd))
        if not os.path.isdir(goc_du_an):
            return "", ""
        loai, gt = SL.boc_viec("%s\n%s" % (desc or "", prompt or ""))
        if loai == "ngoai":
            return "", ""
        if loai == "so":
            ok, ly = SL.kiem_viec(cwd, gt)
            if ok is not False:
                return "", ""
            loi = "số hiệu «%s»: %s" % (gt, ly)
        elif loai == "sai":
            loi = "dòng `VIEC:` viết sai khuôn: «%s»" % gt[:80]
        else:
            _ve = None
            try:
                _ve = WQ.tim(cwd, ti) if WQ is not None else None
            except Exception:
                _ve = None
            if _ve:
                return "", ("\n\n⚠️  VÉ CŨ %s CHƯA CÓ DÒNG `VIEC:` — cho qua (tương thích ngược). "
                            "Thả lại lần sau thì thêm `VIEC: <số hiệu>` để bảng mắt xích nối "
                            "được việc này." % (_ve.get("so") or "W??"))
            loi = "brief THIẾU dòng `VIEC:`"
        ds = SL.ds_muc_viec(cwd)
        bang_muc = "\n".join("    %s  %-4s %s" % (m, l, t) for m, l, t in ds[-15:]) \
            or "    (sổ lệnh hôm nay chưa có mục nào)"
        return (
            "⛔ THIẾU SỐ HIỆU VIỆC — %s.\n\n"
            "Mỗi lượt thả thợ phải nói việc này sinh từ MỤC NÀO của sổ lệnh, để máy trả lời "
            "được câu «việc Dev giao đang ở mắt xích nào» (phiếu P114 hướng A).\n\n"
            "SỬA: thêm MỘT dòng vào đầu brief (cạnh dòng `GHI:`), chép đúng số ở bảng dưới:\n"
            "    VIEC: %s          (mục con thì thêm .N, ví dụ %s.1)\n"
            "Việc không sinh từ lệnh Dev (dọn kho, vá cổng tự phát hiện…):\n"
            "    VIEC: ngoai-so — <lý do ít nhất 15 ký tự>\n\n"
            "Mục trong sổ lệnh hôm nay:\n%s" % (
                loi, ds[-1][0] if ds else "20261001-L05", ds[-1][0] if ds else "20261001-L05",
                bang_muc)), ""
    except Exception:
        return "", ""


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    ev = str(data.get("hook_event_name") or "")
    cwd0 = str(data.get("cwd") or os.getcwd())

    # Một worker vừa trả báo cáo -> có thể đã nhả vùng/nhả chỗ. Đây là thời điểm DUY NHẤT
    # chắc chắn có việc rời hàng, nên ép điều phối đọc hàng chờ ngay tại đây.
    if ev in ("SubagentStop", "UserPromptSubmit"):
        try:
            if WQ is None:
                return 0
            # W05 13/09/2026 (Đ8) — LỜI GIỤC ĐIỀU PHỐI KHÔNG ĐƯỢC RƠI VÀO NGỮ CẢNH THỢ.
            # Nhánh này vốn không kiểm `agent_id`, nên khi một WORKER đóng (payload có
            # `agent_id` = lời gọi phát ra từ worker, đo thật 27/08 — xem
            # founder_lenh_gate.py:29-30) thì khối "➜ THẢ NGAY LƯỢT NÀY" được đóng gói
            # `hookEventName: SubagentStop` và rơi vào con thợ vừa nộp bài. Ca thật
            # 13/09: W01 mang brief "THUẦN ĐO, không sửa gì" nhận đúng lời giục đòi nó tự
            # gọi `Agent` thả vé `git push` 47 commit — đòi việc ở người không có quyền làm.
            # VẪN CHẠY hết phần quét (hồi sinh vé `WR.quet` + đẻ vé việc-để-lại `WD.quet`)
            # vì đó là tác dụng phụ giữ việc khỏi rơi; CHỈ bỏ phần in ngữ cảnh.
            # ĐO TRƯỚC KHI SỬA (không bỏ nhắc mù): kênh `SubagentStop` chưa bao giờ giao
            # được chữ cho ai — quét 25 transcript phiên + 1000 transcript con của dự án
            # Fulfill: 5156 `hook_additional_context` được ghi, trong đó
            # UserPromptSubmit 4623 · PreToolUse 481 · SessionStart 52 · **SubagentStop 0**;
            # khối hàng chờ xuất hiện 470 lần, 470/470 qua `UserPromptSubmit`. 53 lần chuỗi
            # "THẢ NGAY LƯỢT NÀY" có trong transcript con đều là `tool_result` (thợ tự
            # grep mã), không một lần nào do hook chèn. Nên bỏ in ở đây KHÔNG làm điều
            # phối mất lời nhắc: nó vẫn nhận ở `UserPromptSubmit` (146 lần khối THẢ NGAY)
            # và ở `PreToolUse`.
            vao_tho = (ev == "SubagentStop" and bool(data.get("agent_id")))
            # BƯỚC 0 (thêm 27/8): worker bị `TaskStop`/kill/chết giữa chừng TỰ QUAY LẠI
            # hàng chờ. Trước đó hàng chờ chỉ nhận việc ở CỔNG VÀO (bị chặn lúc thả), nên
            # worker đã chạy rồi bị giết là rơi mất sạch — điều phối phải tự nhớ, và đã
            # quên 2 lần trong một buổi sáng (ca HGT nằm chết 2 tiếng).
            hoi_sinh = []
            if WR is not None:
                try:
                    hoi_sinh = WR.quet(cwd0)
                except Exception:
                    hoi_sinh = []
            # BƯỚC 0b (thêm 29/8): worker XONG VIỆC nhưng trong báo cáo cuối tự khai
            # "để lại / ngoài vùng ghi" -> đẻ vé. Đo 28/8: 31/56 worker có việc để lại mà
            # sổ hàng chờ nhận ĐÚNG 0 vé loại này (vé chỉ sinh lúc THẢ bị chặn) — ca P070
            # mục S5 nằm chết trong một tệp 52 KB tới sáng hôm sau founder mới thấy.
            de_lai = []
            if WD is not None:
                try:
                    de_lai = WD.quet(cwd0)
                except Exception:
                    de_lai = []
            # BƯỚC 0c (W25 09/09/2026): WORKER CHÁU (worker do worker khác đẻ) ĐÓNG mà
            # thông báo hoàn tất KHÔNG được giao về phiên điều phối. Đo trên phiên
            # 2eebc882 hôm đó: harness `enqueue` thông báo của cháu vào hàng đợi phiên rồi
            # `remove` 43 giây sau, không bao giờ giao — 22/22 con depth-1 được giao,
            # 0/2 cháu depth-2 được giao. Kết quả của cháu chỉ nằm trong nhật ký của mẹ:
            # `a4df81d5cbcd41ad3` truy xong ba đơn A35-4135133183 · E10-4159743430 ·
            # A67-4159944221, viết báo cáo 6419 ký tự, rồi biến mất không một dòng báo.
            # Khối này VỚT báo cáo đó ra và đẩy thẳng vào ngữ cảnh điều phối.
            # ĐẶT TRƯỚC phép `if not ves: return 0` — hàng chờ rỗng là ca THƯỜNG GẶP nhất,
            # nhét sau đó thì cảnh báo không bao giờ bắn.
            # W66 14/09/2026 — ĐẾM LƯỢT HÔ Ở MỌI KÊNH, KỂ CẢ `SubagentStop`.
            # Bản cũ miễn đếm cho `SubagentStop` (đo 09/09 thấy kênh đó để lại 0 dấu vết
            # trong transcript điều phối). Nhưng miễn đếm = `so_lan_bao` đứng yên =
            # `da_bao_dieu_phoi` KHÔNG BAO GIỜ đóng, nên khi kênh ấy THẬT SỰ tới mắt thì nó
            # hô lại y nguyên mỗi lượt, mãi mãi. Đo tối 14/09 trên chính hai cháu của W66:
            # hô 4 lượt liên tiếp cùng một bản, mà meta ghi `so_lan_bao` = 1 và `None` —
            # cổng không có lối ra, đúng thứ luật ca S12 09/09 cấm. `TOI_DA_LAN` = 3 vẫn là
            # lưới an toàn cho trường hợp một lượt không tới mắt.
            chau = ""
            try:
                import worker_chau as WC
                chau = WC.canh_bao(cwd0)
            except Exception:
                chau = ""
            ves = WQ.doc(cwd0)
            if not ves:
                if chau.strip():
                    json.dump({"hookSpecificOutput": {
                        "hookEventName": ("SubagentStop" if ev == "SubagentStop"
                                          else "UserPromptSubmit"),
                        "additionalContext": chau.strip()}}, sys.stdout, ensure_ascii=False)
                return 0
            ws, _ = running_workers(cwd0)
            n_tran = so_tinh_tran(ws, cwd0)     # W127: thợ chỉ chờ lô deploy không tính
            dang = set()
            for w in ws:
                dang |= vung_hep(w[3])
            # Vé chờ founder quyết KHÔNG bao giờ nằm trong tập "thả được ngay": nó
            # không vướng vùng nên bản cũ luôn cho lọt (ca W156·W160·W161 đêm 29/08).
            # WHY (W192, 29/08): vé còn ghi ĐIỀU KIỆN CHỜ MỘT WORKER cụ thể (`cho_worker`)
            # mà worker đó CÒN SỐNG thì KHÔNG phải "thả được ngay" — dù vùng tệp trống.
            # Ca thật: vé W200 «chạy sync-uni.sh pull KHI MỌI WORKER ĐÃ DỪNG» ghi chờ W197;
            # W197 còn chạy ở mốc 68% mà cổng vẫn giục thả 4 lượt liền. Pull cài đè lại
            # toàn bộ hook vào ~/.claude giữa lúc worker khác đang thi công = gãy cổng.
            try:
                so_song = {a["so"] for a in (WQ.agent_song(cwd0) or []) if a.get("so")}
            except Exception:
                so_song = set()

            def _cho_nguoi_khac(v):
                ai = WQ._so_chuan(str(v.get("cho_worker") or ""))
                return bool(ai) and ai in so_song

            # W18 09/09/2026 — MỘT NGUỒN DUY NHẤT: phép lọc này đã dời sang
            # `WQ.ve_tha_duoc()` để cổng `Stop` (`ve_de_sau_gate` — chỗ ÉP main thả) và
            # khối nhắc ở đây không bao giờ ra hai đáp án khác nhau. Bốn điều kiện y
            # nguyên (vùng trống · dưới trần · không chờ founder · không chờ worker khác);
            # `_cho_nguoi_khac` giữ lại vì hàm dùng chung tính bằng `agent_song` y hệt.
            try:
                san = WQ.ve_tha_duoc(cwd0, ves)
            except Exception:
                san = [v for v in ves if not (vung_tu_text(v.get("vung") or "") & dang)
                       and not ((v.get("vung") or "") in dang)
                       and not WQ.cho_founder(v)
                       and not _cho_nguoi_khac(v)]
                if n_tran >= MAX_WORKERS:
                    san = []
            # W05 13/09/2026 (Đ9) — VÉ ĐANG CHỜ FOUNDER GẬT KHÔNG BAO GIỜ LÀ "THẢ ĐƯỢC".
            # Ca thật 13/09, vé W02 `729ab85235`: *"BỊ DỪNG GIỮA CHỪNG ở 65% · đang dở: Đã
            # soạn script gỡ, chờ founder gật mới chạy"* vẫn mang nhãn ✅ THẢ ĐƯỢC NGAY và
            # bị giục mỗi lượt — hệ dùng áp lực lặp đẩy một vé `git push` 47 commit đi VÒNG
            # QUA cửa founder duyệt.
            # W08 13/09/2026 — BỎ PHÉP TRỪ Ở ĐÂY: phép lọc đã nằm trong `WQ.cho_founder()`
            # nên `WQ.ve_tha_duoc()` (cả nhánh dự phòng ngay trên) ĐÃ loại sẵn. Trừ lần nữa
            # = nguồn đếm thứ hai. Danh sách dưới chỉ để IN khối ⛔, lấy từ `ves` (không lấy
            # từ `san` — `san` đã sạch vé chờ gật thì lọc lại ra rỗng, mất hẳn khối ⛔).
            cho_gat = [v for v in ves if _cho_founder_gat(v)]
            ma_san = {v.get("ma") for v in san}
            # W18 10/09/2026 (P089 O1.6) — HỎI `nhai_lai_gate` TRƯỚC KHI GIỤC. Lượt đang
            # nợ khối NHẠI LẠI thì cổng kia CẤM thả worker thi công; giục "THẢ NGAY LƯỢT
            # NÀY" ở đây là đẩy điều phối vào một cửa đã khoá. Cổng bảo vệ tính đúng đắn
            # thắng cổng thúc tốc độ -> đổi giọng sang nhắc mềm, và KHÔNG tính quãng chờ
            # founder gật là "bỏ rơi" (`WQ.cho_phut` trừ đồng hồ treo).
            try:
                no_nhai, treo = WQ.treo_vi_nhai_lai(
                    cwd0, str(data.get("session_id") or ""),
                    str(data.get("transcript_path") or ""))
            except Exception:
                no_nhai, treo = "", 0.0
            lau = max(WQ.cho_phut(v, cwd0, treo) for v in ves)
            # Thời gian chờ của vé THẢ ĐƯỢC — mức gắt phải đo trên chính nó, không đo trên
            # vé đang bị chặn thật (vé kia chờ lâu là đúng, vé này chờ lâu là BỎ RƠI).
            lau_san = max([WQ.cho_phut(v, cwd0, treo) for v in san] or [0])
            dau = "⏳ HÀNG CHỜ WORKER"
            if san and no_nhai:
                dau = ("⏸ HÀNG CHỜ WORKER — %d vé ĐÃ SẴN nhưng CHƯA ĐƯỢC THẢ: lượt này "
                       "đang nợ khối NHẠI LẠI (%s). Viết khối nhại -> founder gật -> "
                       "rồi mới thả. KHÔNG phải việc bị bỏ rơi."
                       % (len(san), no_nhai))
            elif san and lau_san >= 30:
                dau = ("🛑 LỖI ĐIỀU PHỐI — vé THẢ ĐƯỢC nằm chờ %.0f PHÚT (%d/%d worker, "
                       "vùng trống). Đây là việc bị BỎ RƠI, không phải việc bị chặn."
                       % (lau_san, n_tran, MAX_WORKERS))
            elif san and lau_san >= 10:
                dau = ("⛔ ĐANG BỎ RƠI VIỆC — vé nằm chờ %.0f phút mà VÙNG ĐÃ TRỐNG, "
                       "THẢ NGAY LƯỢT NÀY" % lau_san)
            elif san:
                dau = "⏳ HÀNG CHỜ WORKER — CÓ VÉ THẢ ĐƯỢC NGAY, thả trong lượt này"
            txt = ("%s — %d việc đang nằm chờ (đã lưu đủ brief, KHÔNG mất):\n%s"
                   % (dau, len(ves), WQ.bang(ves, chi_tiet=True, san=ma_san)))
            # W05 13/09/2026 (Đ9) — nhãn ⛔ cho vé chờ founder gật, và CHỈ IN MỘT LẦN cho
            # mỗi tập vé (không lặp mỗi lượt): lặp chính là thứ biến lời nhắc thành áp lực
            # đẩy vé đi vòng qua cửa founder. In lại khi tập mã đổi (có vé chờ-gật MỚI)
            # hoặc sau 6 giờ, để vé không im lặng nằm chết cả ngày.
            if cho_gat:
                moc_p = os.path.join(WQ.thu_muc(cwd0), ".w05-nhac-cho-gat.json")
                da_nhac, gio = set(), 0.0
                try:
                    cu = json.load(open(moc_p, encoding="utf-8"))
                    da_nhac = set(cu.get("ma") or [])
                    gio = float(cu.get("luc") or 0)
                except Exception:
                    pass
                moi = {v.get("ma") for v in cho_gat}
                if (moi - da_nhac) or (time.time() - gio) > 6 * 3600:
                    txt += ("\n\n⛔ CHỜ FOUNDER GẬT — KHÔNG THẢ (%d vé, đã loại khỏi khối "
                            "THẢ NGAY):\n%s\n"
                            "   Trạng thái dở dang của chính vé tự khai đang chờ founder "
                            "đồng ý. Thả worker lúc này = đẩy việc đi vòng qua cửa founder "
                            "duyệt. Founder gật rồi thì ghi lại trạng thái vé (bỏ chữ "
                            "«chờ founder/chờ gật» trong mốc `.progress`/sổ bàn giao) — "
                            "KHÔNG thả worker để lách."
                            % (len(cho_gat),
                               "\n".join("   • %s «%s» — VÉ: %s · %s"
                                         % (v.get("so") or "W??", WQ.ten_ve(v)[:40],
                                            v.get("ma"),
                                            " / ".join(str(v.get(k))[:60]
                                                       for k in _O_TRANG_THAI if v.get(k)))
                                         for v in cho_gat)))
                    try:
                        json.dump({"ma": sorted(m for m in moi if m),
                                   "luc": time.time()},
                                  open(moc_p, "w", encoding="utf-8"),
                                  ensure_ascii=False)
                    except Exception:
                        pass
            if hoi_sinh:
                txt += ("\n\n🔁 VỪA TỰ DỰNG LẠI %d vé từ worker BỊ DỪNG GIỮA CHỪNG: %s\n"
                        "   (brief nguyên văn + mốc %% + việc đang dở đã nằm trong vé — "
                        "thả lại là chạy tiếp được, không phải làm lại từ đầu.)"
                        % (len(hoi_sinh),
                           ", ".join("%s «%s» dừng ở %s%%" % (r[0], r[1][:32], r[2])
                                     for r in hoi_sinh)))
            # W71 30/08/2026 — TÁCH tầng A (đã đẻ vé thật) khỏi tầng B (chỉ cảnh báo, xem
            # WHY tại worker_de_lai.py chỗ `if tang == "B"`): worker TỪ CHỐI việc rồi viết
            # kiểu "nằm ngoài phạm vi của tôi" từng bị tầng B hiểu nhầm là bàn giao, đẻ vé
            # rác đêm 29-30/08. Từ nay tầng B không tạo vé nữa, chỉ in cảnh báo cho main đọc.
            ve_that = [r for r in de_lai if r[3] != "B"]
            canh_bao = [r for r in de_lai if r[3] == "B"]
            if ve_that:
                txt += ("\n\n\U0001F4CC VỪA ĐẺ %d vé từ VIỆC WORKER TỰ ĐỂ LẠI (báo cáo cuối "
                        "khai «để lại / ngoài vùng ghi»): %s\n"
                        "   Vé nào có vùng thì tự lật sang ✅ THẢ ĐƯỢC NGAY khi vùng trống; "
                        "vé không vùng là việc CHỜ FOUNDER quyết — gom lúc chốt ngày."
                        % (len(ve_that),
                           ", ".join("%s «%s»%s" % (r[0], str(r[1])[:32],
                                                    (" [vùng %s]" % r[2]) if r[2] else "")
                                     for r in ve_that)))
            if canh_bao:
                txt += ("\n\n⚠️ NGHI CÓ %d VIỆC ĐỂ LẠI (lưới vớt văn xuôi tầng B, "
                        "CHƯA đẻ vé — main tự đọc và quyết có mở vé hay không): %s"
                        % (len(canh_bao),
                           ", ".join("«%s»%s" % (str(r[1])[:40],
                                                 (" [vùng %s]" % r[2]) if r[2] else "")
                                     for r in canh_bao)))
            if san and no_nhai:
                # Nhường `nhai_lai_gate`: chỉ NHẮC MỀM, không dựng khối mệnh lệnh "THẢ
                # NGAY" (gọi `Agent` lúc này chắc chắn ăn `deny` của cổng kia).
                txt = ("⏸ CHƯA THẢ ĐƯỢC — %d vé sẵn sàng nhưng cổng NHẠI LẠI đang giữ "
                       "lượt (%s).\n   Thứ tự đúng: viết khối NHẠI LẠI -> founder gật "
                       "-> thả vé. Vé nằm nguyên trong sổ, KHÔNG mất.\n\n%s"
                       % (len(san), no_nhai, txt))
            elif san:
                # MỆNH LỆNH ĐẶT LÊN ĐẦU. Bản cũ để khối này DƯỚI bảng + dưới mấy đoạn kể
                # lể -> điều phối đọc lướt tới đó là hết hơi, vé W01 nằm 8 giờ 52, W62
                # nằm 8 giờ 37, W64 nằm 66 phút trong khi chỉ có 0-2/5 worker chạy.
                menh = []
                for v in san[:3]:
                    cho = WQ.cho_phut(v, cwd0, treo)
                    menh.append(
                        "   • %s «%s» — chờ %.0f phút. Gọi `Agent`, brief NGUYÊN VĂN ở: %s\n"
                        "     `description` PHẢI bắt đầu bằng \"%s \" VÀ chứa mã vé \"%s\" "
                        "(dù có gộp/rút gọn/đổi cách gọi việc thế nào cũng KHÔNG bỏ mã này —"
                        " đây là khoá gỡ vé duy nhất không phụ thuộc chữ, xem AC-C2)."
                        % (v.get("so") or "W??", WQ.ten_ve(v), cho, v.get("_path"),
                           v.get("so") or "W??", v.get("ma") or "??????????"))
                    # GỘP ĐƯỢC: có worker SỐNG đang làm đúng loại việc này -> nêu đích danh
                    # kèm lệnh dựng sẵn, khỏi đẻ con thứ hai cùng loại (luật gộp việc).
                    try:
                        import ve_cho_founder as VCF
                        ten_v = WQ.ten_ve(v)
                        for w in ws:
                            if VCF.cung_loai_viec(ten_v, str(w[2] or "")):
                                menh.append(
                                    "     🔗 GỘP ĐƯỢC vào %s (đang làm ĐÚNG loại việc này, "
                                    "chạy %.0f phút) — chuyển thẳng, khỏi thả con mới:\n"
                                    "        SendMessage -> to: \"%s\" · message: «%s»"
                                    % (so_worker(w, cwd0) or w[1], w[0],
                                       so_worker(w, cwd0) or w[1], ten_v[:120]))
                                break
                    except Exception:
                        pass
                txt = ("➜ THẢ NGAY LƯỢT NÀY (%d/%d worker đang chạy, vùng đã trống — "
                       "KHÔNG có lý do gì để vé nằm thêm):\n%s\n\n%s"
                       % (n_tran, MAX_WORKERS, "\n".join(menh), txt))
            else:
                # W05 13/09/2026 (Đ9) — nêu ĐÚNG lý do. Bản cũ chỉ biết hai lý do (đủ trần
                # / vùng bị giữ) nên vé bị loại vì chờ founder gật lại bị giải thích là
                # "vùng vẫn bị worker giữ" — điều phối đi tìm worker không tồn tại.
                txt += "\n\n(chưa thả được: %s)" % (
                    "đủ trần %d worker" % MAX_WORKERS if n_tran >= MAX_WORKERS
                    else "%d vé đang CHỜ FOUNDER GẬT" % len(cho_gat) if cho_gat
                    else "vùng vẫn bị worker đang chạy giữ")
            key = "SubagentStop" if ev == "SubagentStop" else "UserPromptSubmit"
            # W05 13/09/2026 (Đ8) — lượt của THỢ: bỏ khối hàng chờ/"THẢ NGAY" (việc của
            # điều phối, thợ không có quyền thả), nhưng GIỮ khối `chau`: worker cháu là
            # con của chính con thợ này, nó mới là người cần đọc lại báo cáo cháu.
            if vao_tho:
                if chau.strip():
                    json.dump({"hookSpecificOutput": {
                        "hookEventName": key,
                        "additionalContext": chau.strip()}}, sys.stdout,
                        ensure_ascii=False)
                return 0
            # W140 09/10/2026: khi KHÔNG có vé thả được ngay (chỉ là bảng hàng chờ + lý do
            # chưa thả), bảng đủ in khi hàng chờ ĐỔI (chữ ký = mã vé + lý do, không tính số
            # phút chờ) / đầu phiên / sau nén / mỗi 40 lượt; các lượt khác một dòng. Có vé
            # «THẢ NGAY» thì LUÔN in đủ — đó là mệnh lệnh, bỏ là vé nằm im (ca 8 giờ 52).
            if not san and not chau.strip():
                try:
                    import nhac_gon as NG
                    _dau = "|".join(sorted("%s:%s" % (v.get("ma") or v.get("so") or "", v.get("ly_do") or "")
                                           for v in ves)) + "|" + txt.rsplit("(chưa thả được:", 1)[-1]
                    txt = NG.gon(data, "hang-cho", txt,
                                 "⏳ Hàng chờ KHÔNG ĐỔI từ lần in đủ trước: %d vé (chưa thả được:%s"
                                 % (len(ves), txt.rsplit("(chưa thả được:", 1)[-1]), dau=_dau)
                except Exception:
                    pass
            if chau.strip():
                txt = chau.strip() + "\n\n" + txt
            if san and WQ is not None:
                # P143 1C: main SẮP đọc «➜ THẢ NGAY» cho các vé này -> canh hàng chờ khỏi
                # đánh thức thêm một lần cho đúng chúng (xem `worker_queue.ghi_main_thay_tha`).
                WQ.ghi_main_thay_tha(cwd0, [v.get("ma") for v in san])
            json.dump({"hookSpecificOutput": {"hookEventName": key,
                                              "additionalContext": txt}},
                      sys.stdout, ensure_ascii=False)
        except Exception:
            return 0
        return 0

    if ev != "PreToolUse":
        return 0
    tool = str(data.get("tool_name") or "")

    if tool == "Bash":
        try:
            cmd = str((data.get("tool_input") or {}).get("command") or "")
            if ESCAPE in cmd:
                return 0
            la_wlock = all(rx.search(cmd) for rx in VONG_WLOCK)
            la_do_chu = ("wlock" in cmd) and bool(RX_DO_CHU.search(cmd))
            if la_wlock or la_do_chu:
                reason = (
                    "SAI CÁCH DÙNG KHOÁ — lệnh này tự bọc vòng lặp quanh `wlock` "
                    "và/hoặc DÒ CHỮ trong output của nó.\n\n"
                    "Ngày 2026-08-26 đúng kiểu này: worker được cấp khoá NGAY lần đầu "
                    "(wlock in `ĐÃ CẤP khoá 'deploy'…`) nhưng vòng lặp dò chữ tiếng Anh "
                    "`acquired|ok|granted` -> không khớp -> tưởng trượt -> `sleep 60` -> xin lại "
                    "-> **xếp hàng sau chính mình**, kẹt 15 phút và chặn 2 worker phía sau.\n\n"
                    "CÁCH ĐÚNG — MỘT DÒNG, tự nằm chờ tới lượt, KHÔNG dò chữ:\n"
                    "    W=~/.claude/universal-hooks/wlock.sh; ME=<slug worker>\n"
                    "    bash $W wait deploy --owner=$ME --pid=$$ --timeout=900 || exit 75\n"
                    "    trap 'bash '\"$W\"' release deploy --owner='\"$ME\"' >/dev/null' EXIT INT TERM\n"
                    "  hoặc gọn hơn, tự nhả kể cả khi lệnh lỗi:\n"
                    "    bash $W run deploy --owner=$ME -- ./day_len_prod.sh\n\n"
                    "MÃ THOÁT là thứ duy nhất được xét: 0 = đã cầm khoá · 75 = hết giờ chờ · "
                    "2 = sai cú pháp. Xin/chờ khoá mà CHÍNH MÌNH đang giữ -> wlock trả 0 ngay, "
                    "không xếp hàng sau chính mình.")
                json.dump({"hookSpecificOutput": {
                    "hookEventName": "PreToolUse", "permissionDecision": "allow",
                    "permissionDecisionReason": reason,
                    "additionalContext": reason}}, sys.stdout, ensure_ascii=False)
                return 0
            if not all(rx.search(cmd) for rx in VONG_CANH):
                return 0
            reason = (
                "HỎI TRƯỚC — lệnh này là một VÒNG CANH tài nguyên tự chế "
                "(`while/until` + `ps/pgrep` + `sleep`).\n\n"
                "Ngày 2026-08-25 mỗi worker tự dựng một vòng như vậy -> **6 shell nền cùng canh "
                "một thứ**; lại canh theo TÊN SCRIPT nên một worker dùng script tên khác vẫn lọt "
                "-> hai worker đẩy FTP cùng lúc, 9 tệp lệch.\n\n"
                "CÁCH ĐÚNG — xin khoá dùng chung theo TÀI NGUYÊN (rules/AGENTS-ORCH.md §Trần worker):\n"
                "    W=~/.claude/universal-hooks/wlock.sh; ME=<slug worker>\n"
                "    bash $W wait deploy --timeout=900 --owner=$ME --pid=$$ || exit 75\n"
                "    trap 'bash '\"$W\"' release deploy --owner='\"$ME\"' >/dev/null' EXIT INT TERM\n"
                "  hoặc gọn 1 dòng, tự nhả kể cả khi lệnh lỗi:\n"
                "    bash $W run deploy --owner=$ME -- ./day_len_prod.sh\n\n"
                "Duyệt CHỈ khi vòng lặp này canh thứ KHÁC hẳn (không phải deploy/tài nguyên dùng "
                "chung). Thật sự cần -> thêm `worker-cap-ok` vào lệnh."
            )
        except Exception:
            return 0
        # 2026-08-26: allow thay vi ask — hook hoi = ket ca phien khi founder di vang.
        # Nhac van toi agent qua additionalContext, khong chan.
        json.dump({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "allow",
            "permissionDecisionReason": reason,
            "additionalContext": reason}}, sys.stdout, ensure_ascii=False)
        return 0

    if tool not in AGENT_TOOLS:
        return 0
    try:
        ti = data.get("tool_input") or {}
        if not isinstance(ti, dict):
            return 0
        desc = str(ti.get("description") or "")
        prompt = str(ti.get("prompt") or "")
        cwd = str(data.get("cwd") or "")
        globals()["_GOC_KHO"] = cwd
        # P089: nhả số của những lượt thả TRƯỚC ĐÓ đã bị cổng chặn, TRƯỚC khi lượt này
        # xin số — có thế thì sửa brief rồi thả lại mới ra ĐÚNG số cũ.
        _don_so_ma(cwd, str(data.get("transcript_path") or ""))
        co_ok = (ESCAPE in desc) or (ESCAPE in prompt)

        ws, xac = running_workers(cwd)
        cap = MAX_WORKERS
        # W127: trần đếm thợ ĐANG LÀM; thợ chỉ ngồi chờ lô deploy có trần riêng.
        # W140: người soát cũng có trần riêng; thả MỘT người soát mới khi trần riêng còn
        # chỗ thì không xét trần chính (cổng trùng vùng phía dưới vẫn chạy như cũ).
        try:
            _lam, _cho_dep, _soat = tach_tran(ws, cwd)
        except Exception:
            _lam, _cho_dep, _soat = list(ws), [], []
        n_tran = (len(_lam) + max(0, len(_cho_dep) - MAX_CHO_DEPLOY)
                  + max(0, len(_soat) - MAX_NGUOI_SOAT))
        if str(ti.get("subagent_type") or "") == VAI_SOAT and len(_soat) < MAX_NGUOI_SOAT:
            n_tran = 0

        # ---- CỔNG 1: TRÙNG VÙNG TỆP — chặn KỂ CẢ khi có `worker-cap-ok` ----
        # Vượt trần chỉ làm nặng máy; trùng vùng làm GÃY BUILD (26/8: deeddc1). Nên cửa
        # thoát `worker-cap-ok` (founder cho phép chạy thêm) KHÔNG được mở cổng này.
        # CỔNG 0 — BRIEF DẠY WORKER LÁCH CỔNG (bệnh 3 tầng 2, 04/09/2026).
        try:
            import nghi_truoc_gate as NTG
            _pham, _ly = NTG.kiem_brief(desc, prompt)
            if _pham:
                NTG._ghi("CHẶN BRIEF DẠY LÁCH | %s" % (desc or "")[:120])
                json.dump({"hookSpecificOutput": {
                    "hookEventName": "PreToolUse", "permissionDecision": "deny",
                    "permissionDecisionReason": _ly}}, sys.stdout, ensure_ascii=False)
                return 0
        except Exception:
            pass
        vung_raw, nguon_vung = vung_viec_moi(desc + "\n" + prompt)
        vung_moi = vung_hep(vung_raw)

        # ---- CỔNG H4 (P103, 15/09/2026) — CẤM WORKER ĐẺ CHÁU THI CÔNG (AC13, "ba cái
        # gật" §11 phiếu P103 đã duyệt) ----
        # `data.get("agent_id")` non-empty = LƯỢT GỌI NÀY do một WORKER phát ra (main
        # không có agent_id — chính tín hiệu CỔNG 1 dùng ở dưới, `_minh`). Worker do main
        # thả có spawnDepth 1 (neo A13: đo thật trên meta W94); nó thả tiếp thì con mới
        # LUÔN spawnDepth >= 2 = CHÁU. Cháu THI CÔNG (brief khai đường dẫn sẽ ghi, tức
        # `nguon_vung != "khai-rong"`) bị cấm — kết quả của nó chỉ chắc chắn về tới MẸ
        # (worker vừa gọi), không có đường tin cậy báo lại điều phối chính (P098
        # §Ngoài-tầm: harness `enqueue`→`remove` không sửa được). Cháu CHỈ-ĐỌC
        # (`GHI: -` -> `nguon_vung == "khai-rong"`) vẫn cho — trinh sát không rủi ro như
        # thi công. KHÔNG có cửa thoát cờ (giống CỔNG 1 trùng vùng — founder không thể
        # "cho phép" một kênh báo cáo không tin được trở nên tin được).
        try:
            _goi_boi_worker = str(data.get("agent_id") or "")
            if _goi_boi_worker and nguon_vung != "khai-rong":
                json.dump({"hookSpecificOutput": {
                    "hookEventName": "PreToolUse", "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        "⛔ CẤM WORKER ĐẺ CHÁU THI CÔNG (P103 H4) — bạn đang là worker "
                        "(agent_id=%s) gọi `%s` để tạo THÊM một con (cháu, spawnDepth ≥ 2 "
                        "so với điều phối chính).\n\n"
                        "Cháu THI CÔNG (brief khai sẽ ghi file — `GHI:` khác `-`) bị cấm: "
                        "kết quả của nó chỉ chắc chắn về được tới BẠN (mẹ), không có "
                        "đường tin cậy nào báo lại điều phối chính — dễ mất việc âm "
                        "thầm. Hai lối ra:\n"
                        "  1. Trả việc về ĐIỀU PHỐI CHÍNH (main) — xin thả worker cấp 1 "
                        "làm việc này.\n"
                        "  2. Tự làm TRONG VAI MẸ (đừng đẻ con nữa).\n\n"
                        "Cháu CHỈ-ĐỌC (trinh sát, không sửa file) vẫn được — brief bắt "
                        "đầu dòng `GHI: -` (đúng khuôn CỔNG 0b ngay dưới). BẮT BUỘC: báo "
                        "cáo cuối của bạn phải chép kết luận từng cháu — bạn là nơi DUY "
                        "NHẤT chắc chắn nhận được thông báo của nó."
                        % (_goi_boi_worker[:16], tool)
                    )}}, sys.stdout, ensure_ascii=False)
                return 0
        except Exception:
            pass

        # ---- CỔNG 0b: BRIEF PHẢI KHAI VÙNG GHI THEO KHUÔN (07/09/2026, W07) ----
        # Founder chốt qua AskUserQuestion: *"Bắt brief khai vùng theo khuôn cố định, cấm
        # đoán hẳn."* Cổng không còn đường suy vùng từ văn xuôi -> không khai = không đo
        # được = CHẶN. Ngoại lệ DUY NHẤT: vé đã nằm trong hàng chờ từ trước khuôn mới
        # (brief cũ không có dòng `GHI:`) — thả lại phải chạy được, không thì việc chết kẹt.
        nhac_thieu_khai = ""
        if nguon_vung == "thieu-khai":
            _ve_cu = None
            try:
                _ve_cu = WQ.tim(cwd, ti) if WQ is not None else None
            except Exception:
                _ve_cu = None
            if _ve_cu:
                nhac_thieu_khai = (
                    "\n\n⚠️  VÉ CŨ %s KHÔNG CÓ DÒNG `GHI:` — cho qua theo diện tương thích "
                    "ngược, nhưng cổng trùng vùng ĐANG TẮT cho lần thả này. Thêm dòng "
                    "`GHI: <đường dẫn sẽ ghi>` vào đầu brief trước khi thả lại lần sau."
                    % (_ve_cu.get("so") or "W??"))
            else:
                _ghi_chan_do(desc, set(), "-", "", "brief thiếu dòng `GHI:` (không đo được vùng)",
                             loai="thieu-khai-GHI")
                json.dump({"hookSpecificOutput": {
                    "hookEventName": "PreToolUse", "permissionDecision": "deny",
                    "permissionDecisionReason": THIEU_KHAI_GHI}},
                    sys.stdout, ensure_ascii=False)
                return 0
        # ---- CỔNG 0e: `GHI:` PHẢI PHỦ VÙNG PHIẾU BẮT GHI (P138, 11/10/2026) ----
        # Ca P137: dòng `GHI:` do điều phối đoán, hẹp hơn 6 dòng `GHI:` theo đợt của phiếu ->
        # thợ viết mã 30+ phút ngoài vùng rồi mới bị cổng commit chặn, đứng 35% sau 44 phút.
        # Chặn ở đây là chặn sớm nhất có thể; `tien_kiem_brief.py` chạy đúng hook này nên tiền
        # kiểm cũng bắt. Không đẻ vé hàng chờ: lỗi brief, không phải tranh vùng.
        try:
            import ghi_khop_phieu as GKP
            _muc_p, _loi_p = GKP.kiem(desc + "\n" + prompt, cwd)
            if _muc_p == "thieu":
                _ly_thoat = (CT.lay(GKP.TEN_CUA_THOAT, cwd=cwd) if CT is not None else None)
                if not _ly_thoat:
                    _ghi_chan_do(desc, set(), "-", "", "GHI thiếu vùng phiếu bắt ghi",
                                 loai="ghi-khop-phieu")
                    json.dump({"hookSpecificOutput": {
                        "hookEventName": "PreToolUse", "permissionDecision": "deny",
                        "permissionDecisionReason": _loi_p}}, sys.stdout, ensure_ascii=False)
                    return 0
            elif _muc_p == "nhac":
                nhac_thieu_khai += "\n\n" + _loi_p
        except Exception:
            pass
        # ---- CỔNG 0d: SỐ HIỆU VIỆC `VIEC:` (P114 hướng A, W39 01/10/2026) ----
        # Chỗ bắt buộc điền THỨ NHẤT trong đúng hai chỗ (chỗ thứ hai: báo cáo cuối của thợ,
        # `worker_khai_xong_gate`). Không cắm chỗ thứ ba. Xem WHY ở `_cong_viec`.
        _ly_viec, _nhac_viec = _cong_viec(cwd, desc, prompt, ti, nguon_vung,
                                          str(data.get("agent_id") or ""))
        if _ly_viec:
            json.dump({"hookSpecificOutput": {
                "hookEventName": "PreToolUse", "permissionDecision": "deny",
                "permissionDecisionReason": _ly_viec}}, sys.stdout, ensure_ascii=False)
            return 0
        nhac_thieu_khai += _nhac_viec
        # ---- CỔNG 0c: ĐỦ ĐIỀU KIỆN GIAO VIỆC (DoR) CHƯA (P085 §7C.3, chốt F2a) ----
        # Founder 09/09/2026: *"trước đấy phải clear clarify cái problem của tao để biết
        # được đích đến chuẩn theo ý tao là gì. như thế thì cứ theo mà làm."* Ca hỏng đắt
        # nhất của hệ này không nằm ở lúc xong mà ở LÚC GIAO: thợ làm đúng một thứ không
        # phải thứ founder muốn, mọi cổng xanh, tới lúc founder nhìn mới lộ.
        # Toàn bộ luật miễn trừ / fail-open nằm trong `dod.cong_dor` — ở đây chỉ gọi và
        # nuốt mọi lỗi, để hook trần không bao giờ vỡ vì một cổng đọc sổ.
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import dod as _DOD
            _chan_dor, _ly_dor = _DOD.cong_dor(cwd, desc, prompt,
                                               str(data.get("transcript_path") or ""),
                                               float(data.get("ts") or 0) or 0.0)
        except Exception:
            _chan_dor, _ly_dor = False, ""
        if _chan_dor:
            json.dump({"hookSpecificOutput": {
                "hookEventName": "PreToolUse", "permissionDecision": "deny",
                "permissionDecisionReason": _ly_dor}}, sys.stdout, ensure_ascii=False)
            return 0

        # CHÍNH MÌNH KHÔNG PHẢI "WORKER KHÁC". Payload `PreToolUse` mang `agent_id` của
        # con ĐANG GỌI; `running_workers` thì liệt kê MỌI agent sống, kể cả nó. Không lọc
        # ra thì worker nào tự giữ một vùng rồi cần thả thợ phụ vào đúng vùng đó sẽ TỰ
        # CHẶN CHÍNH MÌNH (ca thật 07/09: W154 giữ `tools/univ3` rồi bị chặn vì
        # `tools/univ3` — `cong-trung-vung.log` 10:45:21 và 10:49:36, "worker đang giữ W154").
        _minh = str(data.get("agent_id") or "")
        if _minh:
            ws = [w for w in ws if str(w[1]) != _minh]
        if vung_moi:
            for w in ws:
                chung = doi_chieu_vung(vung_moi, vung_hep(w[3]))
                if not chung:
                    continue
                cv = ", ".join(sorted(chung))
                # Cửa thoát đọc ĐÚNG LÚC sắp chặn (tệp cờ dùng-một-lần), không đốt cờ oan.
                _ly_thoat = CT.lay(TEN_CONG_VUNG, cwd=cwd) if CT is not None else None
                if _ly_thoat:
                    # Điều phối khai ĐÍCH DANH là máy đo sai vùng -> cho qua, nhưng ghi sổ.
                    _ghi_cua_thoat(desc, prompt, vung_moi, cv, so_worker(w, cwd) or w[1], _ly_thoat)
                    json.dump({"hookSpecificOutput": {
                        "hookEventName": "PreToolUse", "permissionDecision": "allow",
                        "permissionDecisionReason": "cửa thoát tệp cờ `trung-vung`",
                        "additionalContext":
                            ("🔓 QUA CỔNG TRÙNG VÙNG BẰNG CỜ CỬA THOÁT `trung-vung` — "
                             "vùng %s (worker %s đang giữ theo máy đo). Lý do đã khai: «%s». "
                             "Đã ghi nhật ký %s và ĐỐT CỜ (lần sau phải mở lại). "
                             "Nếu hai con thật sự ghi chung vùng này thì chính mày chịu "
                             "trách nhiệm gãy build."
                             % (cv, so_worker(w, cwd) or w[1], _ly_thoat[:120],
                                NHAT_KY_CUA_THOAT))}},
                        sys.stdout, ensure_ascii=False)
                    return 0
                ve = ""
                if WQ is not None:
                    # `them` trả rỗng = việc này ĐANG có agent sống làm -> không đẻ vé
                    # thứ hai (nếu không bảng lại vẽ nó hai lần, đúng bệnh đang trị).
                    # `me_agent` (W01 14/09/2026): vé do một WORKER thả thì bảng phải
                    # in `W03.1` thay vì `W03` — xem `worker_queue.so_hien()`. Điều phối
                    # thả thì payload không có `agent_id` nên trường này rỗng.
                    p = WQ.them(cwd, ti, "trùng vùng %s" % cv, cho_ai=so_worker(w, cwd), vung=cv,
                                them_truong={"me_agent": str(data.get("agent_id") or "")}
                                if data.get("agent_id") else None)
                    _v = (WQ.tim(cwd, ti) or {}) if p else {}
                    ve = "" if not p else ("\n\n✅ ĐÃ CHO VÀO HÀNG CHỜ với số **%s** — việc này KHÔNG mất, và "
                          "ĐÃ CÓ TÊN + SỐ ngay từ lúc xếp hàng (hiện trên bảng worker). Vé lưu "
                          "đủ brief để chạy lại y nguyên:\n    %s\n%s"
                          % (_v.get("so") or "W??", p, WQ.bang(WQ.doc(cwd))))
                # W188 29/08/2026 — CHẶN XONG PHẢI TỰ PHÂN TÍCH CÓ GỘP ĐƯỢC KHÔNG.
                # Nguyên văn founder: «toàn đẩy chờ nhưng khi có task liên quan đéo tự động
                # phân tích để gộp. ngu vãi lồn. tốn nguồn lực và thời gian vãi lồn.»
                # Cổng BIẾT THỪA worker nào đang giữ vùng (nó in tên ngay dưới) mà chỉ nhét
                # việc vào hàng chờ rồi thôi. Nay: cùng vùng + CÙNG LOẠI VIỆC -> in thẳng
                # lệnh chuyển việc kèm mã worker đích, main dán một phát là xong; khác loại
                # -> nói rõ chờ AI và con đó đã chạy bao lâu.
                gop = ""
                try:
                    import ve_cho_founder as VCF
                    if VCF.cung_loai_viec(desc + " " + prompt[:600], str(w[2] or "")):
                        gop = ("\n\n🔗 GỘP ĐƯỢC — %s đang làm ĐÚNG loại việc này trong cùng "
                               "vùng %s. Đừng xếp hàng, chuyển thẳng:\n"
                               "    SendMessage -> to: \"%s\" · message: «%s»\n"
                               "   (đo bằng cùng thước gộp vé của `ve_cho_founder.cung_viec`)"
                               % (so_worker(w, cwd) or w[1], cv,
                                  so_worker(w, cwd) or w[1], (desc or "")[:120]))
                    else:
                        gop = ("\n\n⏳ KHÔNG gộp được (khác loại việc). Chờ %s — con đó đã "
                               "chạy %.0f phút: «%s»."
                               % (so_worker(w, cwd) or w[1], w[0], str(w[2] or "")[:70]))
                except Exception:
                    gop = ""
                nguon_cau = {
                    "khai": "brief TỰ KHAI dòng `GHI:` (cổng tin theo khai báo, KHÔNG suy thêm)",
                    "khai-rong": "brief có dòng `GHI:` nhưng không bóc ra đường dẫn nào",
                    "thieu-khai": "brief THIẾU dòng `GHI:` (vé cũ, cho qua tương thích ngược)",
                }.get(nguon_vung, nguon_vung)
                chan_do = (
                    "\n\n📍 AI NÓI THẾ (dán nguyên khối này khi báo lỗi cổng):\n"
                    "   · vùng bị giữ   : %s\n"
                    "   · worker đang giữ: %s  (id %s)\n"
                    "   · NGUỒN         : transcript worker ĐANG SỐNG — "
                    "`worker_cap_enforce.running_workers()` -> `vung_worker()`, tức tệp "
                    "worker đã Edit/Write/`git add` thật. Bảng worker và hàng chờ hỏi "
                    "CÙNG nguồn này qua `worker_queue.vung_dang_giu()`.\n"
                    "   · vùng việc mới : %s  (nguồn: %s)\n"
                    "   · CHỈ ĐỌC KHÔNG CÒN BỊ TÍNH (từ 07/09/2026): cổng CHỈ đọc dòng "
                    "`GHI:` của brief, không suy vùng từ văn xuôi nữa. Vùng trên là do "
                    "chính brief khai ra — sai thì sửa dòng `GHI:` rồi thả lại. Dòng "
                    "`ĐỌC:` cố ý KHÔNG bao giờ tính là tranh chấp.\n"
                    "   · TÀI NGUYÊN: cổng còn một kênh khai CỨNG riêng cho thứ KHÔNG "
                    "phải tệp mã (kho dữ liệu thử, máy chủ thử…) — dòng `TÀI NGUYÊN: "
                    "db-dev dev-3000` (hoặc `TÀI NGUYÊN: -` nếu không giành gì). CÓ dòng "
                    "này thì cổng TIN TUYỆT ĐỐI, KHÔNG suy thêm từ văn xuôi mô tả bệnh — "
                    "khỏi phải mở cửa thoát chỉ vì brief lỡ nhắc chữ 'kho dữ liệu thử'."
                ) % (cv, so_worker(w, cwd) or "(không rõ số)", w[1],
                     ", ".join(sorted(vung_moi)) or "(rỗng)", nguon_cau)
                reason = (
                    "CHẶN — việc mới «%s» ghi vào VÙNG mà worker khác ĐANG GIỮ: %s\n%s%s\n\n"
                    "Ngày 26/08/2026 đúng tình huống này: hai worker cùng ghi "
                    "`src/lib/fulfill/` -> `git add` của con này cuốn phần đang viết dở của "
                    "con kia vào commit deeddc1 (gọi `probeSupplierOrderWithRetry` khi hàm đó "
                    "chưa được export) -> nhánh main không biên dịch được, lô deploy gãy.\n\n"
                    "LÀM NGAY (chọn 1):\n"
                    "  a. `SendMessage` việc này vào chính worker %s — nó đang giữ vùng đó.\n"
                    "  b. Để nguyên trong hàng chờ; khi %s xong, hook sẽ nhắc thả.\n"
                    "  c. MÁY ĐO SAI VÙNG (việc mới chỉ ĐỌC chỗ đó, hoặc con kia không hề "
                    "ghi vào đấy) -> CHẠY LỆNH mở cờ cửa thoát rồi thả lại; TUYỆT ĐỐI KHÔNG "
                    "viết ký hiệu nào vào câu trả lời gửi founder:\n"
                    "     python3 ~/.claude/universal-hooks/cua_thoat.py mo trung-vung "
                    "\"<lý do >= 15 ký tự>\"\n"
                    "     (cờ dùng MỘT LẦN, hết hạn 15 phút, ghi nhật ký "
                    "~/.claude/logs/cua-thoat.log)\n\n"
                    "Lưu ý: `worker-cap-ok` KHÔNG mở được cổng này — vượt trần chỉ nặng máy, "
                    "còn trùng vùng thì gãy build.%s%s%s"
                ) % (desc or "(không tên)", cv, bang([w]), chan_do, w[1], w[1],
                     ("\n\n(`dung-chung` = tệp dùng chung nằm thẳng trong hộp chứa — "
                      "src/lib/*.ts, src/types/*, src/app/globals.css, layout gốc. "
                      "Đây là chỗ hai worker chắc chắn ghi đè nhau.)" if CHUNG in chung else ""),
                     ("\n\n(Vùng việc mới được SUY từ đường dẫn nêu trong brief. Suy sai thì "
                      "khai thẳng một dòng `VÙNG: <đường dẫn sẽ ghi>` trong brief — cổng tin "
                      "theo khai báo, không đoán nữa.)" if nguon_vung == "suy" else ""),
                     gop + ve)
                _ghi_chan_do(desc, vung_moi, cv, so_worker(w, cwd) or w[1], nguon_vung)
                json.dump({"hookSpecificOutput": {
                    "hookEventName": "PreToolUse", "permissionDecision": "deny",
                    "permissionDecisionReason": reason}}, sys.stdout, ensure_ascii=False)
                return 0

        # ---- CỔNG BỘ NHỚ (P147 E, 28/10/2026) — đặt SAU cổng trùng vùng ----
        # Máy 16 GB đơ 4 giờ vì cổng chỉ đếm SỐ thợ: wired 12 GB, RAM trống TB 410 MB mà vẫn thả đủ
        # 5 thợ (báo cáo W12 §3). Vàng: chặn thợ mới, `worker-cap-ok` vẫn qua kèm cảnh báo. Đỏ: chặn
        # cả `worker-cap-ok` — máy đang sát đơ, ép thêm là anh phải tắt cứng; lối ra duy nhất là cờ
        # ~/.claude/ram-guard.OFF. Thợ đang chạy để yên. Vé vào hàng chờ như ca vượt trần.
        _ram_canh = ""
        if RG is not None:
            try:
                _m, _so, _ly = RG.muc()
            except Exception:
                _m, _so, _ly = "xanh", "", []
            if _m == "do" or (_m == "vang" and not co_ok):
                _ve = ""
                if WQ is not None:
                    try:
                        _p = WQ.them(cwd, ti, "bộ nhớ máy %s" % ("ĐỎ" if _m == "do" else "VÀNG"),
                                     them_truong={"me_agent": str(data.get("agent_id") or "")}
                                     if data.get("agent_id") else None)
                        _v = (WQ.tim(cwd, ti) or {}) if _p else {}
                        if _p:
                            _ve = ("\n\n✅ Đã cho vào HÀNG CHỜ với số **%s** — việc không mất; "
                                   "`tu_tha_ve` tự thả lại khi bộ nhớ về xanh." % (_v.get("so") or "W??"))
                    except Exception:
                        pass
                json.dump({"hookSpecificOutput": {
                    "hookEventName": "PreToolUse", "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        "CHẶN THỢ MỚI — bộ nhớ máy đang %s: %s (%s). Chờ thợ đang chạy xong rồi "
                        "thả lại; thợ đang chạy để yên.\n%s%s"
                        % ("ĐỎ" if _m == "do" else "VÀNG", _so, "; ".join(_ly),
                           "Lối ra duy nhất ở mức ĐỎ: tạo cờ ~/.claude/ram-guard.OFF (anh quyết)."
                           if _m == "do" else
                           "Cần chạy gấp: thêm `worker-cap-ok` vào mô tả (máy sẽ nặng thêm).",
                           _ve))}}, sys.stdout, ensure_ascii=False)
                return 0
            if _m == "vang":
                _ram_canh = ("⚠️  ĐANG ÉP THẢ THỢ khi bộ nhớ máy VÀNG bằng `worker-cap-ok`: %s (%s)."
                             % (_so, "; ".join(_ly)))

        if co_ok:
            # GỠ VÉ TRƯỚC, rồi mới thoát. Bản cũ `return 0` NGAY ở đây nên không bao giờ
            # chạm tới `WQ.tha()` bên dưới — mà vé bị chặn vì VƯỢT TRẦN chỉ thả được khi
            # điều phối thêm `worker-cap-ok`, tức ĐÚNG những vé được thả thì không bao giờ
            # được gỡ. Hậu quả đo được 27/8: W130 đang chạy 84% vẫn hiện "đang xếp hàng",
            # bảng vẽ việc đó hai lần; trước đó W114 và W125 y hệt, lần nào main cũng phải
            # xoá vé bằng tay. (Lưới thứ hai: `worker_queue.doc()` tự đối soát mỗi lần đọc.)
            # W39 01/10/2026 (P114 D) — KHÔNG GỠ VÉ Ở ĐÂY NỮA. Hook này chạy SONG SONG với các
            # cổng `PreToolUse:Agent` khác; cổng khác từ chối cùng lượt thì vé đã mất mà không
            # thợ nào chạy (ca thật 00:55–00:56: vé f1298cafdd · 34dd090b07 · 9f43583956 bị đổi
            # đuôi `.da-go`, main phải đổi tên lại tay). Vé sẽ được `worker_queue.doi_soat()`
            # gỡ khi agent SỐNG thật sự làm đúng việc (khớp mã vé `VÉ: <mã>` tuyệt đối).
            nhac_ve = ""
            if WQ is not None:
                _t = WQ.tim(cwd, ti)
                if _t:
                    nhac_ve = ("\n✅ Vé %s sẽ tự rời hàng chờ ngay khi thợ chạy thật (đối soát "
                               "theo mã vé) — bị cổng khác chặn thì vé vẫn còn nguyên."
                               % (_t.get("so") or "W??"))
            # Founder cho phép vượt trần -> cho qua NHƯNG phải nhìn thấy là đang ép chạy.
            canh = ((_ram_canh + "\n") if _ram_canh else "") + nhac_ve
            if n_tran >= cap:
                canh = ("⚠️  ĐANG ÉP CHẠY VƯỢT TRẦN bằng `worker-cap-ok`: %d worker đang "
                        "chạy / trần %d.\n%s\n(Đã qua cổng trùng vùng nên không gãy build, "
                        "nhưng máy founder sẽ nặng thêm.)%s"
                        % (len(ws), cap, bang(ws), nhac_ve))
            if canh.strip():
                json.dump({"hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": canh.strip()}}, sys.stdout, ensure_ascii=False)
            return 0

        # Điều phối đang thả đúng việc nằm trong hàng chờ -> gỡ vé.
        nhac_q = nhac_thieu_khai
        if nguon_vung == "khai-rong":
            # CÓ dòng `GHI:` nhưng bóc ra RỖNG -> cổng cho qua mà không ai biết là khai
            # hỏng. Im lặng ở đây là mở toang cổng trùng vùng bằng một dòng viết sai.
            # `GHI: -` (việc thuần đọc) rơi vào đây và ĐÚNG là phải cho qua — cảnh báo chỉ
            # để người viết brief nhìn thấy mình vừa tắt cổng, không phải lỗi.
            nhac_q = ("\n\n⚠️  DÒNG `GHI:` TRONG BRIEF KHÔNG BÓC RA ĐƯỜNG DẪN NÀO -> cổng "
                      "trùng vùng ĐÃ BỊ TẮT cho lần thả này. Đúng ý (việc thuần đọc, "
                      "`GHI: -`) thì bỏ qua; còn không thì viết lại đúng dạng: "
                      "`GHI: src/app/pipeline src/components/card` (đường dẫn thật, cách "
                      "nhau bằng khoảng trắng; chữ mô tả và ngoặc đơn bị bỏ qua).")
        if WQ is not None:
            # W39: chỉ TRA vé, không gỡ — xem WHY ở nhánh `co_ok` phía trên.
            _tha = WQ.tim(cwd, ti)
            if _tha:
                # NỐI, không ĐÈ: cảnh báo "vé cũ thiếu dòng GHI:" phải sống sót qua đây,
                # nếu không thì vé cũ cứ thả lại êm ru và không ai đi thêm dòng khai.
                nhac_q += ("\n\n(việc này đang có vé trong hàng chờ, mang số %s từ lúc xếp hàng; "
                           "giữ nguyên số đó trên bảng, đừng cấp số mới — vé tự rời hàng khi "
                           "thợ chạy thật)" % (_tha.get("so") or "W??"))
            con = [v for v in (WQ.doc(cwd) or [])
                   if not (_tha and v.get("ma") == _tha.get("ma"))]
            if con:
                nhac_q += ("\n\n⏳ Hàng chờ còn %d việc:\n%s" % (len(con), WQ.bang(con)))
        # CẤM KHUYÊN TẮT CON CÒN ĐANG GỌI LỆNH (ca W11, 29/08 — xem NGUONG_NHUC_NHICH_PHUT).
        # "Trông như đã trả báo cáo" KHÔNG đủ để kết luận đã xong: worker vừa nói vừa làm.
        # P143 1A (W195 13/10/2026): `pl == -1.0` = harness ĐÃ báo kết thúc -> CLI đã tự đóng
        # thợ, `TaskStop` trả «No task found» (đo 24 giờ: 94% lần bấm là thừa; nhắc này in 145
        # lần). Chỉ còn khuyên tắt con mà harness CHƯA báo kết thúc. Lùi: `UNIV3_P143_1A_TAT=1`.
        xac_xet = xac if os.environ.get("UNIV3_P143_1A_TAT") == "1" else [
            w for w in xac if _im_lenh(w) != -1.0]
        xac_tat = [w for w in xac_xet
                   if _im_lenh(w) is None or _im_lenh(w) < 0
                   or _im_lenh(w) >= NGUONG_NHUC_NHICH_PHUT]
        xac_dong = [w for w in xac_xet if w not in xac_tat]
        nhac_xac = ""
        if xac_tat:
            nhac_xac = (
                "\n\nDỌN NGAY — {m} worker ĐÃ TRẢ BÁO CÁO CUỐI và im quá {ng:.0f} phút không gọi "
                "lệnh nào (khung điều phối vẫn hiện `running`, KHÔNG tính vào trần, nhưng phải "
                "kill):\n{tx}\n"
                "    -> `TaskStop` từng con ngay bây giờ. Để đấy thì mỗi thông báo nền lại đánh "
                "thức nó gửi lại đúng bản báo cáo cũ (25/8: 4 lần liên tiếp một con)."
            ).format(m=len(xac_tat), ng=NGUONG_NHUC_NHICH_PHUT, tx=bang(xac_tat))
        if xac_dong:
            nhac_xac += (
                "\n\n⛔ CẤM `TaskStop` {m} con dưới đây — trông như đã trả báo cáo NHƯNG VỪA GỌI "
                "LỆNH, nó đang làm dở:\n{tx}\n"
                "    -> để yên. Tắt bây giờ là cắt giữa chừng (ca W11 29/08: tắt lúc nó cách lệnh "
                "cuối 18 GIÂY, đang gửi ảnh cho founder). Im quá {ng:.0f} phút mới được khuyên tắt."
            ).format(m=len(xac_dong), ng=NGUONG_NHUC_NHICH_PHUT,
                     tx="\n".join("    - %-17s %-38s (lệnh cuối cách %.1f phút)"
                                  % (w[1], w[2] or "(không rõ)", _im_lenh(w)) for w in xac_dong))

        if n_tran >= cap:
            ve = ""
            if WQ is not None:
                p = WQ.them(cwd, ti, "vượt trần %d worker" % cap,
                            them_truong={"me_agent": str(data.get("agent_id") or "")}
                            if data.get("agent_id") else None)
                _v = (WQ.tim(cwd, ti) or {}) if p else {}
                ve = "" if not p else ("\n\n✅ ĐÃ CHO VÀO HÀNG CHỜ với số **%s** — việc này KHÔNG mất, đã có "
                      "TÊN + SỐ ngay từ lúc xếp hàng, vé lưu đủ brief:\n"
                      "    %s\n%s\nKhi một worker xong, hook `SubagentStop` sẽ nhắc thả "
                      "đúng việc này." % (_v.get("so") or "W??", p, WQ.bang(WQ.doc(cwd))))
            # W23 05/09/2026 (lỗi A, AC-A6) — lời chặn phải in CẢ BA con số (đang chạy /
            # xác treo / không rõ), không chỉ `len(ws)` như trước. Thiếu hai số kia thì
            # khi cổng "đủ trần", còi báo "ĐANG BỎ RƠI VIỆC" bị tắt theo mà không ai thấy
            # (§4.1 phiếu P-DEM-DUNG-05092026) — in ra để founder/worker khác đối chiếu
            # ngay với `worker_board.py --dem` thay vì phải đoán.
            _khong_ro_n = sum(1 for w in xac if w[5])
            _xac_thuc_n = len(xac) - _khong_ro_n
            reason = (
                "CHẶN — dự án này đang có {n} worker THỰC SỰ ĐANG CHẠY, trần là {cap} "
                "(XAC={xt} KHONG_RO={kr}):\n{tb}\n\n"
                "Ngày 2026-08-25 thả 11 worker cùng lúc đã đẩy load average lên 566, "
                "còn ~63 MB RAM trống, 4 http.server mồ côi, worker ghi đè CSS của nhau."
                "{nx}\n\n{how}"
            ).format(n=n_tran, cap=cap, xt=_xac_thuc_n, kr=_khong_ro_n, tb=bang(_lam),
                     nx=nhac_xac, how=HOW_TO.format(cap=cap)) + ve
            if _soat:
                reason += ("\n\n(W140) %d người soát — trần riêng %d, không tính vào trần chính:\n%s"
                           % (len(_soat), MAX_NGUOI_SOAT, bang(_soat)))
            if _cho_dep:
                reason += ("\n\n(W127) %d thợ khác CHỈ ĐANG CHỜ LÔ DEPLOY — không tính vào trần "
                           "(trần riêng %d):\n%s" % (len(_cho_dep), MAX_CHO_DEPLOY, bang(_cho_dep)))
            decision = "deny"
        else:
            # Brief đã KHAI vùng và không đè vùng ai -> khỏi đoán tiếp bằng từ khoá
            # (đoán chữ chính là thứ đẻ ra cảnh báo oan: brief nhắc tên thư mục làm ví dụ).
            if nguon_vung == "khai" and vung_moi:
                return _ra_cho_qua(ti, desc, cwd, (nhac_xac or "") + (nhac_q or ""))
            # W140: Người soát chỉ đọc + chạy lệnh kiểm (vai không ghi mã) và mô tả của nó
            # CỐ Ý nhắc tên việc của thợ được soát -> đoán «trùng mảng» theo chữ luôn nổ oan.
            if str(ti.get("subagent_type") or "") == VAI_SOAT:
                return _ra_cho_qua(ti, desc, cwd, (nhac_xac or "") + (nhac_q or ""))
            moi = tokens(desc + " " + prompt[:400])
            trung = [(w, moi & tokens(w[2])) for w in ws if w[2]]
            trung = [(w, k) for w, k in trung if len(k) >= 2]
            if not trung:
                return _ra_cho_qua(ti, desc, cwd, (nhac_xac or "") + (nhac_q or ""))
            w, k = max(trung, key=lambda x: len(x[1]))
            reason = (
                "HỎI TRƯỚC — việc mới «{d}» TRÙNG MẢNG với worker đang chạy:\n{tb}\n"
                "    (từ khoá trùng: {k})\n\n"
                "Luật founder: *\"cái nào cùng worker đang xử lý thì mới add vào worker chứ\"* — "
                "trùng mảng thì `SendMessage` vào chính worker đó, đừng đẻ con mới: nó đã có "
                "ngữ cảnh, và hai con cùng sửa một vùng tệp sẽ ghi đè nhau (đã mất 1250 dòng CSS "
                "vì đúng lỗi này).{nx}\n\nDuyệt CHỈ khi việc này thật sự đụng tệp KHÁC hẳn.\n\n{how}"
            ).format(d=desc or "(không tên)", tb=bang([w]), k=", ".join(sorted(k)),
                     nx=nhac_xac, how=HOW_TO.format(cap=cap)) + (nhac_q or "")
            # 2026-08-26: "allow" thay "ask" — chi nhac, khong chan de hoi (ket phien).
            # Tran worker (nhanh tren) van DENY nhu cu: deny khong hoi user.
            decision = "allow"
    except Exception:
        return 0

    out = {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": reason,
    }
    try:
        _nhac_ke = nhac_luu_ds(desc, prompt)
    except Exception:
        _nhac_ke = ""
    if _nhac_ke:
        out["permissionDecisionReason"] = (out.get("permissionDecisionReason") or "") + _nhac_ke
    if decision == "allow":
        out["additionalContext"] = out["permissionDecisionReason"]  # allow -> agent van phai DOC loi nhac
        # CHỈ chuẩn hoá số ở nhánh CHO QUA. Nhánh chặn (vượt trần) thì agent không chạy,
        # số đã do `worker_queue.cap_so` cấp lúc xếp hàng — sửa nữa là tiêu thêm một số.
        try:
            _moi, _bao = chuan_hoa_so_day(desc, cwd)
        except Exception:
            _moi, _bao = desc, ""
        if _bao:
            out["permissionDecisionReason"] = (out["permissionDecisionReason"] or "") + "\n\n" + _bao
            out["additionalContext"] = out["permissionDecisionReason"]
        if _moi != desc and isinstance(ti, dict):
            out["updatedInput"] = dict(ti, description=_moi)
    json.dump({"hookSpecificOutput": out}, sys.stdout, ensure_ascii=False)
    return 0


def _ca_thu_chau() -> int:
    """P103 H4 (15/09/2026) — CỔNG "CẤM WORKER ĐẺ CHÁU THI CÔNG" (AC13).

    Gọi `main()` THẬT qua stdin (không mô phỏng lại logic) — đúng cách chống dối test
    (kiểu `w01_ca_thu.py`). `cwd` trỏ thư mục KHÔNG tồn tại nên `running_workers()`/
    `vung_dang_giu()` tự trả rỗng/None (fail-open có chủ đích của chính các hàm đó),
    cổng H4 vẫn chạy TRƯỚC những chỗ cần đọc đĩa đó.
    """
    import io
    import contextlib

    def goi(payload):
        buf = io.StringIO()
        old_in = sys.stdin
        sys.stdin = io.StringIO(json.dumps(payload))
        try:
            with contextlib.redirect_stdout(buf):
                main()
        finally:
            sys.stdin = old_in
        raw = buf.getvalue()
        try:
            return json.loads(raw) if raw.strip() else {}
        except Exception:
            return {"_raw": raw}

    base = {"hook_event_name": "PreToolUse", "tool_name": "Agent",
            "cwd": "/tmp/khong-ton-tai-p103-h4-ca-thu"}
    AID = "a" + "1" * 16
    KEY = "CẤM WORKER ĐẺ CHÁU THI CÔNG"

    def ly_do(r):
        return ((r.get("hookSpecificOutput") or {}).get("permissionDecisionReason") or "")

    ca = [
        ("1. worker (agent_id) + GHI đường dẫn thật -> DENY H4",
         KEY in ly_do(goi(dict(base, agent_id=AID, tool_input={
             "description": "W99 sửa file X",
             "prompt": "GHI: src/lib/abc.ts\nĐỌC: -\nTÀI NGUYÊN: -\nsửa file abc.ts"})))),
        ("2. worker (agent_id) + GHI: - (chỉ đọc) -> KHÔNG bị H4 chặn",
         KEY not in ly_do(goi(dict(base, agent_id=AID, tool_input={
             "description": "W99 trinh sát file X",
             "prompt": "GHI: -\nĐỌC: src/lib/abc.ts\nTÀI NGUYÊN: -\nđọc file abc.ts"})))),
        ("3. main (không agent_id) + GHI thật -> KHÔNG bị H4 chặn",
         KEY not in ly_do(goi(dict(base, tool_input={
             "description": "W99 sửa file X",
             "prompt": "GHI: src/lib/abc.ts\nĐỌC: -\nTÀI NGUYÊN: -\nsửa file abc.ts"})))),
        ("4. worker (agent_id) + THIẾU dòng GHI: -> DENY H4 (coi như khác '-')",
         KEY in ly_do(goi(dict(base, agent_id=AID, tool_input={
             "description": "W99 sửa file X (brief cũ)",
             "prompt": "sửa file abc.ts, không khai gì cả"})))),
    ]
    n_dat = sum(1 for _, dat in ca if dat)
    for ten, dat in ca:
        print("  %s %s" % ("✅" if dat else "❌", ten))
    print("worker_cap_enforce --ca-thu-chau: %d/%d %s"
          % (n_dat, len(ca), "PASS" if n_dat == len(ca) else "FAIL"))
    return 0 if n_dat == len(ca) else 1


if __name__ == "__main__":
    if "--ca-thu-chau" in sys.argv:
        sys.exit(_ca_thu_chau())
    sys.exit(main())
