#!/usr/bin/env python3
"""univ3 — MỘT installer duy nhất (thay 5 bề mặt cài của v2).

  python3 install.py --harness claude   # hook + skill Claude + git pre-commit
  python3 install.py --harness codex    # AGENTS.md + skill Codex + git pre-commit
  python3 install.py --harness all       # cả hai (mặc định)
  python3 install.py --project /path     # chỉ định repo để cài git pre-commit (mặc định: cwd)
  python3 install.py --khong-lich        # không cắm lịch máy dọn rác (LaunchAgent / crontab)

Luôn làm: sinh AGENTS.md (từ SPINE.md) + gen MANIFEST + cài git pre-commit (nếu là git repo).
An toàn: backup settings.json trước khi ghi; sync skill có xoá file mồ côi.
"""
import json
import os
import shutil
import stat
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))               # univ3/
HOOKS_SRC = os.path.join(ROOT, "enforce", "claude", "hooks")
SKILLS_SRC = os.path.join(ROOT, "skills")
AGENTS_SRC = os.path.join(ROOT, "agents")
SPINE = os.path.join(ROOT, "SPINE.md")
COMMANDS_SRC = os.path.join(ROOT, "commands")

CLAUDE_HOOKS_DEST = os.path.expanduser("~/.claude/universal-hooks")
CLAUDE_SKILLS_DEST = os.path.expanduser("~/.claude/skills")
CLAUDE_AGENTS_DEST = os.path.expanduser("~/.claude/agents")
CLAUDE_COMMANDS_DEST = os.path.expanduser("~/.claude/commands")
CODEX_HOOKS_DEST = os.path.expanduser("~/.agents/univ3-hooks")
CODEX_SKILLS_DEST = os.path.expanduser("~/.agents/skills")
SETTINGS = os.path.expanduser("~/.claude/settings.json")

HOOK_FILES = ["session_context.py", "askback_enforce.py", "quality_gate_enforce.py",
              "goal_tracking_enforce.py", "viet_diacritics_check.py",
              "code_index_commit_gate.py", "claude_notify.sh",
              "prebuild_gate_enforce.py", "report_context_enforce.py",
              "design_gate_enforce.py", "seo_meta_gate_enforce.py",
              "pnpm_enforce.py",
              "univ3_freshness_check.py", "univ3_fresh_gate.py",
              "delegate_subagent_reminder.sh", "subagent_background_enforce.py",
              # 19/09 (W08): TIỀN KIỂM BRIEF trước khi thả thợ. `tien_kiem_brief.py` là
              # LỆNH chạy tay (không đăng ký hook) kiêm thư viện tính vân tay/dấu cho cổng;
              # `tien_kiem_gate.py` là cổng PreToolUse(Agent) bắt buộc chạy nó;
              # `tien_kiem_ca_thu.py` là bộ ca thử, không đăng ký hook.
              "tien_kiem_brief.py", "tien_kiem_gate.py", "tien_kiem_ca_thu.py",
              "mobile_sim_verify_enforce.py", "platform_ambiguity_enforce.py",
              "progress_format_enforce.py", "bg-progress.sh",
              "docs_bootstrap_gate.py", "no_password_reset_enforce.py",
              "no_steal_focus_enforce.py", "sim-headless.sh",
              "no_chrome_phone_verify_enforce.py",
              "sim_one_device_enforce.py", "no_secret_in_file_enforce.py",
              "worker-watchdog.sh", "worker_cap_enforce.py", "shared_file_deploy_enforce.py",
              "no_guess_enforce.py",
              # 26/8: chống hai worker cùng ghi một vùng làm gãy build (xem rules/AGENTS-ORCH.md §Trần-worker điều 3)
              "git_add_scope_enforce.py", "worker_queue.py",
              # 29/10 (Task-28102026-02): cổng chặn bí mật + chữ khách thật trước khi lưu/đẩy
              # (`pii_commit_gate.py`, gọi từ pre-commit của dự án, KHÔNG đăng ký hook Claude)
              # + công cụ viết lại đoạn lịch sử chưa đẩy không chặn thợ (`viet_lai_lich_su.sh`,
              # lệnh chạy tay). Luật: rules/GIT.md §Tự-đẩy-khi-cổng-PII-sạch + §Viết-lại-lịch-sử.
              "pii_commit_gate.py", "viet_lai_lich_su.sh",
              # 27/8: worker bị TaskStop/kill giữa chừng TỰ quay lại hàng chờ (module dùng
              # chung cho worker_cap_enforce + worker_board; không đăng ký hook riêng).
              "worker_relapse.py",
              # 29/8 (W173): cổng chặn worker KHAI XONG mà mốc .progress chưa tới 100.
              # Ca W144 dừng ở 92% («Smoke demo + prod, chụp ảnh») nhưng khai "xong,
              # ĐỂ LẠI: không có" -> main tin lời khai, 4 màn giao diện vỡ lọt tới tay
              # founder. Đăng ký ở CẢ SubagentStop (rót cảnh báo ĐÚNG lượt worker kết
              # thúc) lẫn Stop (chặn main viết "xong" khi mốc còn < 100).
              "worker_khai_xong_gate.py",
              # 29/8 (W187): TÁCH CHẶNG ĐẨY khỏi worker thi công. Hai cuốn sổ —
              # sổ thi công `.progress` đóng ở 100 ngay khi đăng ký được vé đẩy;
              # sổ đẩy `deploy-queue/<proj>/pending` đóng khi lô chạy xong. Cổng
              # này bịt khe duy nhất còn lại: commit rồi CHẾT TRƯỚC khi đăng ký vé
              # (đúng ca W165 dừng 84% «Đăng ký lô deploy, chuẩn bị đẩy»).
              "deploy_ban_giao_gate.py",
              # 29/8: worker XONG VIỆC mà báo cáo cuối tự khai "ĐỂ LẠI / CHỜ VÙNG" thì tự
              # đẻ vé hàng chờ. Đo 28/8: 31/56 worker có việc để lại -> 0 vé (vé chỉ sinh
              # lúc THẢ bị chặn). Module dùng chung cho worker_cap_enforce, KHÔNG đăng ký
              # hook riêng.
              "worker_de_lai.py",
              # 28/10 (P147 E, ChicHub): mức bộ nhớ máy xanh/vàng/đỏ — máy 16 GB đơ 4 giờ vì
              # cổng chỉ đếm SỐ thợ. Module dùng chung cho worker_cap_enforce + worker_queue,
              # KHÔNG đăng ký hook riêng. Ca thử: `ram_guard.py --ca-thu` · `--ca-thu-cong`.
              "ram_guard.py",
              # 29/8 (W188): vé "chờ founder quyết" tự GỘP vé trùng, tự ĐÓNG vé lỗi thời
              # (founder đã chốt việc đó ở worker khác), tự sinh CÂU HỎI quyết được và giục
              # main gom hỏi khi đủ ngưỡng. Đo thật: 12 vé nằm tới gần 2 tiếng, founder
              # không biết chúng tồn tại. Module dùng chung (ve_de_sau_gate + worker_cap_
              # enforce import), KHÔNG đăng ký hook riêng.
              "ve_cho_founder.py",
              # 29/8: MỘT nguồn cho khối chỉ dẫn "viết lại cho gọn" mà MỌI cổng `Stop`
              # đính vào thông điệp chặn. Cổng Stop chặn SAU khi chữ đã hiện lên màn
              # founder (không giấu được bản 1) -> thứ sửa được là ĐỘ DÀI bản viết lại.
              # Đo 28-29/8: 41 cặp tin lặp = 40.992 ký tự founder đọc hai lần, riêng
              # bảng worker in lại lần hai chiếm 17.920. Module dùng chung, KHÔNG đăng
              # ký hook riêng.
              "stop_viet_lai.py",
              # 29/8 (W192): TỰ kiểm ĐĨA MÁY ĐANG DÙNG mỗi lượt gõ và trước khi thả
              # worker. Sáng 29/8 máy local đầy 98% (còn 12 GB) mà không ai biết —
              # founder phải tự hỏi mới có người đi đo. Ba mức để không kêu oan:
              # <85% im tuyệt đối · 85-92% nhắc MỘT LẦN mỗi 12 tiếng · >=93% nhắc
              # mỗi lượt kèm danh sách kho tạm dọn được. Đọc ổ DỮ LIỆU, không đọc
              # ổ hệ thống chỉ-đọc (macOS: `df /` báo 57% lúc ổ thật đã 98%).
              "disk_guard_enforce.py",
              # 27/8: deploy không còn cần GitHub (bare repo nội bộ trên VPS) ->
              # push GitHub trở lại đúng vai "xuất bản", phải có người gật.
              "git_push_gate_enforce.py",
              # 27/8: cổng "founder HỎI ≠ founder RA LỆNH" — main tự sinh việc từ
              # câu hỏi/góp ý của founder (xem rules/ASK-BACK.md §cùng tên).
              "founder_lenh_gate.py",
              # 27/8: cổng chặn PHÁN BỪA — khẳng định trạng thái hệ thống mà lượt đó
              # chưa chạy lệnh nào chạm tới đối tượng (ca `ListingCSV`, SPINE project §7).
              "phan_bua_gate.py",
              # 27/8: cổng chặn gọi worker theo VỊ TRÍ ("ba con đầu") thay vì mã W###
              # — bảng đổi mỗi lượt nên vị trí không trỏ về đâu (SPINE project §8).
              "worker_vi_tri_gate.py",
              # 4 script CÔNG CỤ (chỉ copy, không đăng ký hook) — trước đây có trên
              # SSOT nhưng thiếu ở đây nên máy/project mới KHÔNG nhận được.
              "wlock.sh", "stale-server-reaper.sh", "wseq.sh", "worker_board.py",
              # 30/10/2026 (Task-30102026-07): máy dọn RỘNG cho macOS (wseq mồ côi, tiến trình
              # mồ côi trong /tmp, thư mục tạm cũ, kho gói khi đĩa chật). Trước đó chỉ nằm ở
              # ~/.claude/don-may/ của một máy — máy khác không có lưới dọn. Thứ riêng máy
              # (gốc dự án, nhật ký app) để ở ~/.claude/don-may/cau-hinh.sh theo mẫu .example.
              # Lịch chạy do install_lich_don() cắm, KHÔNG đăng ký hook.
              "don-may.sh", "don-may.cau-hinh.example",
              # 27/8: MỘT nguồn trạng thái tất định cho cả hệ canh (khoá + hàng chờ +
              # sổ lô deploy chain.log + tệp tiến độ + tiến trình build thật). Thiếu nó
              # thì watchdog/bảng worker quay về phán bằng dữ liệu nhớ sẵn — đúng ca
              # W166·W167·W169 chờ hơn một tiếng sau khi lô đã xong (AGENTS-ORCH
              # §Đọc-nguồn-lúc-in). Chỉ copy, KHÔNG đăng ký hook.
              "worker_state.py",
              # deploy-shared.sh: script BỌC 5 bước mà shared_file_deploy_enforce.py viết
              # lại lệnh trỏ tới. Thiếu nó -> hook quay về CHẶN thẳng, worker kẹt giữa
              # chừng. Phải đi kèm hook đó, không được rải riêng.
              "deploy-shared.sh",
              # 27/8: /tmp/sync-uni-state/ dùng chung cả máy -> worker tìm clone bằng
              # `*/clone.txt | head -1` trúng clone project KHÁC rồi chép đè lên việc
              # dở của nó. Cổng chặn ghi chéo project (xem rules/WORKFLOWS.md §sync-uni).
              "sync_state_owner_enforce.py",
              "sync-uni.sh", "agents-prune.sh",
              # 27/8: 2 hook thêm từ máy local (founder quyết đẩy lên SSOT).
              "nhai_lai_gate.py", "ve_de_sau_gate.py",
              # 07/09 (W09): cổng "fix tận gốc" — founder nói tận gốc/root cause/triệt để
              # thì BẮT BUỘC hỏi lại có cần ki-su+tho-xay challenge và RRI-T không, và
              # CẤM main nhả thiết kế/kết luận ngay lượt đó (ca "đéo tin lắm" 07/09).
              "fix_tan_goc_gate.py",
              # 28/8: cổng chặn Ý ĐỊNH NÓI RA đẻ worker mới vào vùng worker khác
              # đang giữ. Cổng cũ worker_cap_enforce chỉ bắt ở PreToolUse:Agent,
              # tức SAU khi đã quyết — founder ngắt giữa chừng là lọt (SPINE project §10).
              "worker_de_trung_vung_gate.py", "db_that_gate.py",
              # 15/10 (W08): thợ không chạy `task-dev.mjs phuong-an|ap-phuong-an|duyet-luot-huy` thật.
              "phuong_an_tho_gate.py",
              "nghi_truoc_gate.py",
              # 04/09 (W68): cổng chặn `SendMessage` gửi vào TÊN LOẠI THỢ (`tho-fulfill`,
              # `general-purpose`) thay vì MÃ ĐỊNH DANH `a…`. Chuỗi trong
              # `<task-notification from="…">` là LOẠI thợ, không phải địa chỉ — gửi
              # vào là harness trả `No agent named ... is reachable`, tin RƠI MẤT mà
              # không ai biết (ca W64 phải gửi lại lần hai). Danh sách loại thợ đọc
              # từ `agents/*.md` + `agentType` trong `*.meta.json`, KHÔNG viết cứng.
              "worker_dia_chi_gate.py",
              # 04/09: THƯ VIỆN cửa thoát dùng-một-lần (tệp cờ). Trước đây mọi cổng Stop bắt
              # main gõ chuỗi ký hiệu ( …) vào CHÍNH câu trả lời gửi founder —
              # founder không đọc code, ba lượt liên tiếp phải đọc hai dòng ký hiệu vô nghĩa,
              # và nó trông như đang công khai lách luật. Nay khai bằng lệnh, cổng đọc tệp cờ
              # rồi tự xoá. Chỉ COPY, KHÔNG đăng ký hook (các cổng tự import).
              "cua_thoat.py",
              # 29/8: kênh báo tiến độ/kết quả cho founder qua Telegram, gọi tay
              # `tg-notify.sh "nội dung"` (đọc BOT_TOKEN/CHAT_ID từ telegram_config.env
              # cùng thư mục — file KHÔNG lên SSOT, xem .gitignore). Script CÔNG CỤ,
              # chỉ copy, KHÔNG đăng ký hook (xem rules/WORKFLOWS.md §Buổi-sáng).
              "tg-notify.sh",
              # 24/09 (W05): lệnh gom CHẠY HẾT bộ ca thử  trong một câu. Trước đó
              # 16 bộ nằm cạnh hook mà KHÔNG lượt chạy nào gọi (máy không có crontab, không
              # LaunchAgent nào của univ3, chỉ 3 bộ được hook gọi lồng) → sửa 1 hook là gãy âm
              # thầm hook khác. Script CÔNG CỤ, chỉ copy, KHÔNG đăng ký hook.
              "chay-het-ca-thu.sh",
              # W24 30/09/2026 — ba bài tự kiểm cho `wlock build` + chặng đưa bản lên.
              # Chạy tay, KHÔNG đăng ký vào settings.json (giống chay-het-ca-thu.sh).
              "wlock_gop_luot_ca_thu.sh", "wlock_hang_cho_ca_thu.sh",
              "w24_lech_nhip_ca_thu.sh",
              # W301 15/10/2026 — ca thử vé ce749c224c (lô deploy chỉ đoạt khoá của chủ có vé trong lô)
              # + vé e7c1eac966 (5 lỗi cổng báo khách khớp P137). Chạy tay, KHÔNG đăng ký hook.
              "wlock_doat_ca_thu.sh", "p137_bao_khach_ca_thu.py",
              # 03/09: cổng chốt ngày — chặn gửi báo cáo ngày khi việc của ngày còn nợ
              # (worker sống / vé chờ / dòng `ĐỂ LẠI:` chưa có vé). Ca thật: báo cáo 03/09
              # gửi NON hai lần vì định nghĩa "xong" cũ chỉ là ảnh chụp một thời điểm.
              "chot_ngay_gate.py",
              # 04/09 (W55): cổng "chưa tra nhật ký worker". Worker đóng rồi nhật ký
              # `subagents/agent-*.jsonl` vẫn còn nguyên — nói "không tìm thấy dữ liệu của
              # worker kia" mà chưa grep tệp đó là CHẶN. Không đăng ký hook riêng: được
              # `worker_de_trung_vung_gate` gọi hộ ở Stop (settings.json là cấu hình founder).
              "tra_nhat_ky_worker_gate.py",
              # 07/09 (W01): chế độ AFK — founder báo "không ngồi máy" bằng câu nói tự do
              # (không gõ slash command) thì vẫn phải nạp giao thức AFK sáu giai đoạn.
              # 07/09 (W154): MỞ PHIÊN HAI LỚP. Lớp 1 `SessionStart` TỰ CHẠY chuỗi mở phiên
              # (mở ngày làm việc mới + con canh + bảng worker + hàng chờ + git + cầu DB +
              # GOAL/TODO còn treo) rồi rót kết quả vào context — main hết khâu để quên.
              # Lớp 2 `PreToolUse` chỉ nổ khi lớp 1 KHÔNG để lại dấu. Kiêm cổng ép
              # `Skill(chot-ngay)` (chốt ngày có bước gửi Telegram nên hook không tự làm thay).
              "mo_phien_gate.py",
              "afk_mode.py",
              # 11/10/2026: founder đang AFK → CẤM AskUserQuestion, câu hỏi gửi danh sách vào inbox.
              # afk_trang_thai.py = module cờ AFK dùng chung (afk_mode ghi, cổng + claude_notify đọc),
              # không đăng ký hook riêng.
              "afk_trang_thai.py",
              "afk_hoi_inbox_gate.py",
              # 16/10 (Task-12102026-21): ca thử «anh vắng khỏi CLI» (cờ /afk · lời cuối từ Telegram), không đăng ký hook.
              "afk_vang_ca_thu.py", "afk_vang_tan_goc_ca_thu.py",
              # 07/09 (W01): module DÙNG CHUNG nhận diện "SendMessage này có phải GIAO VIỆC
              # THI CÔNG MỚI không" — nhai_lai_gate + founder_lenh_gate cùng gọi, một định
              # nghĩa duy nhất. Không đăng ký hook riêng.
              # 07/09 (W21): cổng chặn tin gửi NHÓM NGƯỜI VẬN HÀNH mà còn dính chữ kỹ
              # thuật (đường dẫn tệp mã nguồn, mã commit, tên nhánh, tên hàm, tên cột DB).
              # Ca thật: tin báo đơn nuốt món gửi nhóm "Hệ thống Fulfill TheChic" kết bằng
              # "chi tiết nằm ở tệp trong kho mã nguồn: docs/handoff/...md" — Phương/My/Hạnh
              # không ai mở được kho. Nhóm KỸ THUẬT và chat riêng founder KHÔNG bị chặn.
              "tin_van_hanh_gate.py",
              # 29/09 (W05): MỨC KIỂM — thợ phải khai tự thử được tới đâu; chưa
              # có người dùng thật xác nhận thì việc mang trạng thái CHỜ NGƯỜI
              # DÙNG XÁC NHẬN, không được gọi là xong, tin gửi nhóm phải nói thẳng.
              "tin_nhom_trung_thuc_gate.py",
              # 05/10 (P118): KHUÔN tin nhóm Hệ thống + cổng chặn đường gửi lậu — thư viện dùng
              # chung cho tin_nhom_trung_thuc_gate + bao_khach_gui, không đăng ký hook riêng.
              "tin_nhom_khuon.py",
              "muc_kiem_ca_thu.py",
              # 29/09 (W15): XƯNG HÔ — chặn tin gửi nhóm người vận hành mà gọi sai giới
              # tính người trong công ty (sếp Quỳnh là NAM, bị gọi "chị" hai lần: 28/09 và
              # tin 3717 ngày 29/09). Bảng người đọc từ `docs/TU-DIEN-TEN.md` mục 6 của
              # DỰ ÁN, mã cổng không chứa tên ai. Fail-closed, không cờ tắt, không cửa
              # thoát. Cắm lồng trong tin_nhom_trung_thuc_gate.py (lệnh Bash) và
              # bao_khach_gui.py (lượt tự bắn tin lúc thợ dừng) -> không thêm dòng hook.
              "xung_ho_gate.py",
              # 07/10 (L20): MỘT chỗ trả lời "lệnh này có thuộc dự án Chichub không" — 4 cổng tin
              # nhóm (tin_van_hanh, tin_nhom_trung_thuc, xung_ho, chot_ngay) gọi nó TRƯỚC khi soi;
              # dự án khác thì cổng im lặng (ca 07/10: dự án khác bị chặn nhầm vì tên loại tin
              # trùng). Thiếu tệp này → cổng rơi về soi như cũ (fail-closed). Không đăng ký hook.
              "pham_vi_chichub.py",
              # 29/09 (W10): CẤM HỎI DEV VIỆC MÀ LUẬT ĐÃ BẮT TỰ LÀM. Hai lần trong cùng một
              # buổi sáng, điều phối xin phép Dev đúng việc `AGENTS.md:45` đã bắt tự làm
              # («soạn sẵn tin, để main duyệt» rồi «anh muốn em nhắn nhờ Phương, hay anh tự
              # nói trong nhóm»). Cổng gác nhánh `Stop` — chỗ DUY NHẤT mọi câu trả lời của
              # điều phối phải đi qua. Lớp 1 soi TRẠNG THÁI sổ VIỆC CHO NGƯỜI (không soi
              # chữ, không có trần chặn); lớp 2 là lưới vớt kiểu câu xin phép/đùn việc, đối
              # chiếu với danh sách máy đọc `viec_cam_hoi.tsv`. FAIL-CLOSED: cổng hỏng là
              # CHẶN. KHÔNG có cờ tắt bằng biến môi trường, KHÔNG dùng `cua_thoat.py` (điều
              # phối tự mở được = tự chấm bài mình) — cửa duy nhất là chuỗi do Dev tự gõ.
              "tu_lam_viec_da_co_luat_gate.py", "viec_cam_hoi.tsv", "tu_lam_viec_ca_thu.py",
              "giao_viec_moi.py",
              # 08/09 (W79): SỔ NGHIỆM THU — nguồn dữ kiện THỨ HAI cho cổng khai-xong.
              # Cổng cũ chỉ so MỘT con số (mốc `.progress` đã 100 chưa) nên worker ghi
              # `100|xong` là qua, dù trang trắng trơn. `nghiem_thu_gate.py` giữ sổ tiêu
              # chí bóc từ brief; `worker_queue.py` chép tiêu chí sang sổ lúc thả vé và
              # `worker_khai_xong_gate.py` đọc sổ lúc worker kết thúc — CẢ HAI `import
              # nghiem_thu_gate`, thiếu tệp này thì cổng W79 tự tắt lặng (try/except) trên
              # mọi máy khác. Module + bộ kiểm, KHÔNG đăng ký hook riêng.
              #   · nghiem_thu_mo_trang.cjs — bộ mở trang THẬT (demo rồi prod), gate gọi qua
              #     hằng MO_TRANG; · nghiem_thu_ca_thu.py — ca thử của gate (`from
              #     nghiem_thu_ca_thu import chay`), thiếu thì `--ca-thu` gãy.
              "nghiem_thu_gate.py", "nghiem_thu_mo_trang.cjs", "nghiem_thu_ca_thu.py",
              # 23/09 (W09): BÁO NHÓM KHI VIỆC XONG — founder chốt qua AskUserQuestion: việc
              # đã nghiệm thu ĐẠT trên trang thật (đọc `trang_thai == "dat"` của sổ trên,
              # KHÔNG đo lại) + thợ tự khai là việc người dùng nhìn thấy (dòng `BAO-KHACH:`
              # bóc ở `nghiem_thu_gate.boc_bao_khach`, gọi từ `khai`) -> tự gửi 3 dòng vào
              # nhóm "Hệ thống Fulfill TheChic" qua `tg-notify.sh` sẵn có. `nghiem_thu_gate.
              # _thu_bao_khach()` (nhánh CLI `khai`/`kiem`) `import bao_khach_gui` — thiếu
              # tệp thì fail-safe im lặng (try/except), không gãy cổng nghiệm thu.
              # 23/09 (W20): NỐI VÀO CỔNG TỰ CHẠY — trước đó tệp chỉ chạy khi có người gõ
              # tay (`grep bao_khach ~/.claude/settings.json` ra RỖNG), nên founder hỏi
              # "thông báo khi xong task có chưa??". Nay đăng ký `SubagentStop` + `Stop`
              # (xem REGISTRATIONS): thợ dừng -> bóc dòng khai trong BÁO CÁO CUỐI -> tin tự
              # bay. Bộ kiểm `bao_khach_ca_thu.py` chạy tay: `bao_khach_gui.py ca-thu`.
              "bao_khach_gui.py", "bao_khach_ca_thu.py",
              # 08/09 (W82): SỔ LỆNH FOUNDER — mỗi ngày đúng hai tệp song song (goc.md nguyên
              # văn + dich.md bản dịch) ở ~/.claude/so-lenh/, NGOÀI kho mã vì có ảnh chụp màn
              # đơn hàng (PII). Chỉ SCRIPT lên SSOT, dữ liệu thì không. `so_lenh_gate.py` là
              # hook 3 nhánh (ghi ngay lúc UserPromptSubmit / bóc ảnh + cổng ở Stop / dọn ở
              # SessionStart), nó `import so_lenh` cùng thư mục nên THIẾU `so_lenh.py` là gãy
              # cả cổng. `so_lenh_ca_thu.py` + `khai_xong_ten_ca_thu.py` là bộ ca thử của
              # so_lenh_gate / worker_khai_xong_gate — gate chạy `--ca-thu` mà thiếu thì gãy,
              # đúng kiểu nghiem_thu_ca_thu.py ở trên.
              "so_lenh_gate.py", "so_lenh.py", "so_lenh_ca_thu.py", "khai_xong_ten_ca_thu.py",
              # 09/09 (W20): canh hàng chờ NGOÀI LƯỢT rồi tự đánh thức điều phối.
              "tu_tha_ve.py",
              # 09/09 (P085, W11): ĐỊNH NGHĨA XONG tất định — gom 5 nguồn dấu vết rời
              # (git · vé + log lô deploy · sổ nghiệm thu · sổ lệnh · harness) thành MỘT
              # phán quyết, và đổi cột `%` của bảng worker thành cột CHẶNG do MÁY đo.
              # `dod.py` là module DÙNG CHUNG (worker_board + worker_cap_enforce +
              # worker_khai_xong_gate import), KHÔNG đăng ký hook riêng.
              "dod.py", "dod_ca_thu.py", "dau_ngay_ca_thu.py",
              # 09/09 (P088/W36): SỔ CÁI VIỆC hợp nhất (khác tầng worker_state.py —
              # trả trạng thái VIỆC, kể cả việc chưa thành worker). worker_chau.py là
              # module cháu spawnDepth:2 do W25 dựng cùng ngày, dùng chung qua
              # worker_cap_enforce (không đăng ký hook riêng).
              "viec_state.py", "viec_state_ca_thu.py", "worker_chau.py",
              # 14/09 (P093/W01): bộ ca thử của cơ chế "cổng chặn phải ĐẺ VÉ và CHỈ LỐI
              # RA" + cấp số worker không trùng. `w01_ca_thu.py` KHÔNG đăng ký hook nào —
              # nó chạy các cổng THẬT (`nhai_lai_gate`, `dod.cong_dor`, `wseq.sh`,
              # `worker_khai_xong_gate`) trong hộp cát rồi đo vé/số sinh ra, đúng kiểu
              # `dod_ca_thu.py`. Thiếu tệp này thì máy mới clone không tái hiện được ca
              # founder mắng sáng 14/09 (thả 9 lượt, chặn 8, hàng chờ 0 vé; ba dòng W01).
              "w01_ca_thu.py",
              # 10/09 (lô W23): bộ ca thử "bảng worker chỉ MỘT nguồn đếm" — dựng lại
              # 5 ca lỗi hôm đó (thợ ghi 95 mà bảng in `chặng 5/9`; thợ CHỈ ĐỌC bị
              # chấm thang 9 chặng; thợ chạy lệnh dài bị con canh hô chết; đối chứng
              # thợ chết thật vẫn phải kêu; mốc 90 của thợ tầng hook rơi `chặng ?/?`).
              # KHÔNG đăng ký hook nào — chạy worker_board/dod/worker-watchdog THẬT
              # trong hộp cát, đúng kiểu `w01_ca_thu.py`. Thiếu tệp này thì máy mới
              # clone không tái hiện được ca 10/09.
              "w23_ca_thu.py",
              # 01/10 (W39, phiếu P114 hướng A + D): bộ ca thử số hiệu việc `VIEC:` (bắt
              # buộc lúc thả + lúc kết lượt, trailer commit), cổng DoR đọc đúng khối/bản
              # mới/mục khai, cờ cửa thoát không cháy oan, hàng chờ đo vùng cùng hàm cổng
              # thả, `wseq dau-ngay` ca đêm. KHÔNG đăng ký hook nào.
              "w39_ca_thu.py",
              # 14/09 (lô W08/P094): bộ ca thử 12 đề xuất cổng worker DoD/DoR — chạy được
              # trên CẢ bản cũ lẫn bản mới (`--hook-dir <bản cũ>`) để đối chứng từng ca
              # bệnh: cổng khai-xong bắt chính bảng do hook cấp · `dod` chấm ĐẠT nhờ lô
              # tuần trước · `FOUNDER CHOT:` xuống dòng · vé vừa gỡ bị coi là vé ma ·
              # D8 an toàn dữ liệu · khối ✋ VIỆC CHO NGƯỜI. KHÔNG đăng ký hook nào.
              "w08_ca_thu.py",
              # 14/09 (W88): bộ ca thử ĐƯỜNG TIÊU SỐ THỨ BA — `worker_board.dong_bo_so`
              # cấp số mới cho TỆP MỐC MỒ CÔI của thợ đã chết (17 số trong ba giây tối
              # 14/09: W66→W82), và cỗ máy bơm nuôi nó: `worker_state.dong_bo_moc` kéo
              # ngược bản bền về sau khi bảng đã đóng việc. Bốn ca: A mồ côi không tiêu
              # số · B thợ sống vẫn được cấp số · C chạy lại không nhảy · D không kéo
              # ngược việc đã đóng. KHÔNG đăng ký hook nào.
              "w88_ca_thu.py",
              # W127 (09/10/2026): dựng lại ca 18:00–18:37 — thợ chỉ chờ lô deploy không
              # chiếm trần 5, câu hứa «làm sau khi W### xong» không vé bị cổng Stop chặn.
              # Chạy `python3 w127_ca_thu.py [thư-mục-hook]`. KHÔNG đăng ký hook nào.
              "w127_ca_thu.py",
              # W140 (09/10/2026, Etsy Task-09102026-39): `nhac_gon.py` là THƯ VIỆN (không đăng
              # ký hook) — lời nhắc tĩnh in đủ một lần mỗi phiên, các lượt sau một dòng; được
              # delegate_subagent_reminder.sh, no_guess_enforce.py, prebuild_gate_enforce.py,
              # worker_cap_enforce.py gọi, session_context.py xoá sổ ở SessionStart. Thiếu tệp
              # này thì các hook đó tự về bản ĐỦ (fail-open phía an toàn).
              "nhac_gon.py",
              # W140: ca thử nhắn tiếp thợ cũ (26 lần thật trong nhật ký) + Người soát trần
              # riêng + giữ tin chờ soát + lượt + bảng hàng chờ gọn. KHÔNG đăng ký hook nào.
              # Chạy `python3 w140_ca_thu.py [thư-mục-hook] [thư-mục-hook-CŨ]`.
              "w140_ca_thu.py",
              # P103 (W96, 14/09/2026): corpus hồi quy AC1 — 28 câu thật bị chặn oan
              # ngày 14/09 bởi worker_khai_xong_gate.py, chạy `--gate <đường dẫn>` để
              # so bản cũ/mới. Đứng riêng (không import bởi gate) nhưng theo đúng nếp
              # các *_ca_thu.py khác ở trên — thiếu registration là lượt pull kế tiếp
              # gỡ mất tệp khỏi máy, mất luôn corpus hồi quy.
              "w96_p103_corpus_ca_thu.py",
              # P104 (W101, 15/09/2026): corpus ca thử AC1/AC2 (11 ca dương + corpus âm)
              # + trạng thái BẬT/TẮT từng nhánh — cùng nếp trên, thiếu registration là
              # lượt pull kế tiếp gỡ mất, mất luôn trạng thái đã chứng minh 0-oan.
              "w98_p104_corpus_ca_thu.py", "p104_trang_thai.json",
              # 18/09 (W13): bộ ca thử TẦNG VÙNG của `git_add_scope_enforce.py` — dựng lại
              # đúng ca W07 cuốn `card-dialog.tsx` của W09 (commit f13253dc -> main gãy
              # build). KHÔNG đăng ký hook nào, chạy tay trong hộp cát như các *_ca_thu.py
              # khác; thiếu tệp này thì máy mới clone không tái hiện được lỗ.
              "git_add_vung_ca_thu.py",
              # P138 (11/10/2026): cổng «GHI khớp phiếu» lúc giao việc — `worker_cap_enforce`
              # import nó, KHÔNG đăng ký hook riêng; thiếu tệp thì cổng im (fail-open) mà không
              # ai biết. Kèm bộ ca thử dựng lại đúng ca P137 (thợ đứng 35% sau 44 phút).
              "ghi_khop_phieu.py", "p138_ca_thu.py",
              # 16–20/10/2026: chống hộp xin quyền khi không ai trông (thợ nền / anh AFK / anh làm qua
              # Telegram). `rm_khong_hop_gate` chặn TRƯỚC các dạng `rm` sẽ bật hộp «kiểm an toàn xoá»;
              # `hop_quyen_vang_gate` là lưới cuối lúc hộp sắp bật. Task-20102026-02: tin báo chặn viết
              # lời thường + việc thật sự cần quyền thì hỏi anh qua bot RIÊNG (telegram_xin_quyen.env,
              # mẫu .example) — Reply 1A cho chạy, 1B / hết 10 phút thì chặn.
              "rm_khong_hop_gate.py", "hop_quyen_vang_gate.py", "telegram_xin_quyen.env.example"]

INTERP = {"claude_notify.sh": "bash", "delegate_subagent_reminder.sh": "bash",
          "sim-headless.sh": "bash", "worker-watchdog.sh": "bash"}  # còn lại python3

# (event, matcher, "basename [tham số]", timeout[, {trường thêm}]) — đã thêm
# MultiEdit/NotebookEdit cho diacritics. Trường thêm dùng cho hook nền/đánh thức.
REGISTRATIONS = [
    # Task-20102026-02: timeout 660 vì hai cổng này có thể GIỮ lệnh chờ anh trả lời 1A/1B tối đa 600 giây
    # (đo 20/10 trên Claude Code 2.1.304: hook PermissionRequest ngủ 610 giây rồi `allow` vẫn được nhận).
    # Lệnh thường đi qua trong vài phần mười giây — timeout chỉ là trần.
    ("PreToolUse",       "Bash",            "rm_khong_hop_gate.py",      660),
    ("PermissionRequest", "*",              "hop_quyen_vang_gate.py",    660),
    ("PermissionDenied", "*",               "hop_quyen_vang_gate.py",     10),
    ("UserPromptSubmit", "",                "claude_notify.sh",          5),
    ("PreToolUse",       "AskUserQuestion", "afk_hoi_inbox_gate.py",     5),
    ("PreToolUse",       "AskUserQuestion", "claude_notify.sh",          5),
    # P104 (W101, 15/09/2026) — C6 tra-trước-hỏi-sau: matcher AskUserQuestion trước
    # chỉ có notify, không có gate; +1 dòng đăng ký cho tệp sẵn có (O1.4), 0 hook mới.
    ("Notification",     "",                "claude_notify.sh",          5),
    ("Stop",             "",                "claude_notify.sh",         10),
    ("UserPromptSubmit", "",                "askback_enforce.py",        5),
    ("Stop",             "",                "askback_enforce.py",       10),
    ("UserPromptSubmit", "",                "prebuild_gate_enforce.py",  5),
    ("UserPromptSubmit", "",                "report_context_enforce.py", 5),
    ("UserPromptSubmit", "",                "afk_mode.py",               5),
    ("PreToolUse",       "Write",           "viet_diacritics_check.py",  5),
    ("PreToolUse",       "Edit",            "viet_diacritics_check.py",  5),
    ("PreToolUse",       "MultiEdit",       "viet_diacritics_check.py",  5),
    ("PreToolUse",       "NotebookEdit",    "viet_diacritics_check.py",  5),
    ("PreToolUse",       "Write",           "design_gate_enforce.py",    5),
    ("PreToolUse",       "Edit",            "design_gate_enforce.py",    5),
    ("PreToolUse",       "MultiEdit",       "design_gate_enforce.py",    5),
    ("PreToolUse",       "Write",           "seo_meta_gate_enforce.py",  5),
    ("SessionStart",     "",                "session_context.py",        5),
    # LỚP 1 chạy ở SessionStart — tự mở ngày làm việc, dựng con canh, đo bảng worker.
    ("SessionStart",     "",                "mo_phien_gate.py",         20),
    # LỚP 2 — lưới an toàn, IM khi lớp 1 để lại dấu. Kiêm ép Skill(chot-ngay).
    ("PreToolUse",       "",                "mo_phien_gate.py",          5),
    ("UserPromptSubmit", "",                "mo_phien_gate.py",          5),
    ("Stop",             "",                "quality_gate_enforce.py",  10),
    ("PreToolUse",       "Bash",            "goal_tracking_enforce.py",  5),
    ("PreToolUse",       "Bash",            "code_index_commit_gate.py", 5),
    ("PreToolUse",       "Bash",            "pnpm_enforce.py",           5),
    # 07/09 (W21): tin gửi nhóm người vận hành còn dính chữ kỹ thuật -> chặn cứng.
    ("PreToolUse",       "Bash",            "tin_van_hanh_gate.py",      5),
    # 29/09 (W05): chưa khai MỨC KIỂM / tin thiếu phần nhờ người dùng xác nhận -> chặn.
    ("PreToolUse",       "Bash",            "tin_nhom_trung_thuc_gate.py", 5),
    # 29/09 (W10): cấm hỏi Dev việc luật đã bắt tự làm. Gác `Stop` vì đó là chỗ DUY NHẤT
    # mọi câu trả lời của điều phối đi qua trước khi tới mắt Dev — không có đường vòng.
    ("Stop",             "",                "tu_lam_viec_da_co_luat_gate.py", 15),
    # cấm GHI vào vùng tạm/tiến độ của PROJECT KHÁC + cấm bung `*` trên /tmp/sync-uni-state
    ("PreToolUse",       "Bash",            "sync_state_owner_enforce.py", 5),
    ("PreToolUse",       "Agent",           "subagent_background_enforce.py", 5),
    # 19/09 (W08): brief CHƯA QUA TIỀN KIỂM thì không được thả. Ca thật hôm đó: bốn lượt
    # thả liên tiếp bị cổng chặn ngay lúc bấm, founder chỉ thấy bốn dòng «0 tool uses».
    ("PreToolUse",       "Agent",           "tien_kiem_gate.py",             10),
    # univ3 freshness check — SessionStart + gate trước Edit/Write/MultiEdit/Bash
    ("SessionStart",     "",                "univ3_freshness_check.py",  5),
    ("PreToolUse",       "Edit",            "univ3_fresh_gate.py",       5),
    ("PreToolUse",       "Write",           "univ3_fresh_gate.py",       5),
    ("PreToolUse",       "MultiEdit",       "univ3_fresh_gate.py",       5),
    ("PreToolUse",       "Bash",            "univ3_fresh_gate.py",       5),
    # delegate subagent reminder — UserPromptSubmit
    ("UserPromptSubmit", "",                "delegate_subagent_reminder.sh", 5),
    # verify UI mobile = iOS Simulator (cấm chrome-devtools phone view) — UserPromptSubmit
    ("UserPromptSubmit", "",                "mobile_sim_verify_enforce.py",  5),
    # project có CẢ app iOS lẫn web mà prompt nói "app/nút/giao diện" chung chung
    # -> ép AskUserQuestion hỏi nền tảng trước khi sửa code / thả worker
    ("UserPromptSubmit", "",                "platform_ambiguity_enforce.py", 5),
    # khuôn báo % tiến độ worker ngầm — chặn sai khuôn + đóng mốc phiên cho bg-progress.sh
    ("PreToolUse",       "Bash",            "progress_format_enforce.py",    5),
    ("SessionStart",     "",                "progress_format_enforce.py",    5),
    # project lớn mà thiếu docs/GOAL.md | PROJECT_SUMMARY.md -> hỏi 1 câu lúc git commit
    ("PreToolUse",       "Bash",            "docs_bootstrap_gate.py",        5),
    # cấm sửa mật khẩu / bảng người dùng trên DB production để vượt màn đăng nhập
    ("PreToolUse",       "Bash",            "no_password_reset_enforce.py",  5),
    # cấm cướp chuột / kéo cửa sổ lên trước khi test app (dùng simctl headless thay thế)
    ("PreToolUse",       "Bash",            "no_steal_focus_enforce.py",     5),
    # cấm boot >1 iOS Simulator cùng lúc (worker thi công không boot; 1 worker QA, 1 device)
    ("PreToolUse",       "Bash",            "sim_one_device_enforce.py",      5),
    # cấm xác nhận UI/UX điện thoại bằng chrome-devtools phone view (phải dùng iOS Simulator)
    ("PreToolUse",       "mcp__chrome-devtools__.*", "no_chrome_phone_verify_enforce.py", 5),
    # cấm ghi GIÁ TRỊ BÍ MẬT thật vào tệp không phải .env (máy local cũng áp dụng)
    ("PreToolUse",       "Write",           "no_secret_in_file_enforce.py",   5),
    ("PreToolUse",       "Edit",            "no_secret_in_file_enforce.py",   5),
    ("PreToolUse",       "MultiEdit",       "no_secret_in_file_enforce.py",   5),
    ("PreToolUse",       "NotebookEdit",    "no_secret_in_file_enforce.py",   5),
    ("PreToolUse",       "Bash",            "no_secret_in_file_enforce.py",   5),
    # trần số worker đồng thời + trùng mảng thì gửi vào worker đang chạy + cấm vòng canh tự chế
    ("PreToolUse",       "Agent",           "worker_cap_enforce.py",          5),
    ("PreToolUse",       "SendMessage",     "worker_dia_chi_gate.py",         5),
    # 26/8: một worker vừa xong / mỗi lượt founder gõ -> ép điều phối nhìn HÀNG CHỜ
    ("SubagentStop",     "",                "worker_cap_enforce.py",          8),
    ("UserPromptSubmit", "",                "worker_cap_enforce.py",          8),
    # 26/8: chặn  /  vơ vét phần dang dở của worker khác
    ("PreToolUse",       "Bash",            "git_add_scope_enforce.py",       8),
    # P138 11/10/2026: Edit/Write ra NGOÀI vùng `GHI:` bị chặn ngay lần sửa đầu, không đợi
    # tới lúc commit (ca P137: thợ viết mã ngoài vùng 30 phút rồi mới vấp cổng commit).
    ("PreToolUse",       "Edit",            "git_add_scope_enforce.py",       8),
    ("PreToolUse",       "Write",           "git_add_scope_enforce.py",       8),
    ("PreToolUse",       "MultiEdit",       "git_add_scope_enforce.py",       8),
    ("PreToolUse",       "NotebookEdit",    "git_add_scope_enforce.py",       8),
    # 27/8: chặn `git push` ra GitHub khi founder chưa duyệt trong lượt đó
    ("PreToolUse",       "Bash",            "git_push_gate_enforce.py",       8),
    ("PreToolUse",       "Bash",            "worker_cap_enforce.py",          5),
    # tệp dùng chung phải tải-về/sửa/đẩy + verify lại prod cuối phiên
    ("PreToolUse",       "Bash",            "shared_file_deploy_enforce.py", 10),
    ("Stop",             "",                "shared_file_deploy_enforce.py", 10),
    ("Stop",             "",                "phan_bua_gate.py",         15),
    # 27/8: gọi worker phải bằng mã W###, cấm "ba con đầu / con cuối"
    ("Stop",             "",                "worker_vi_tri_gate.py",         10),
    ("SubagentStop",     "",                "shared_file_deploy_enforce.py", 10),
    # 29/8 (W173): worker kết thúc mà mốc .progress < 100 -> cảnh báo NGAY lượt đó
    # (SubagentStop), và chặn main viết "xong" cho con đó (Stop). Ca W144: 92%.
    ("SubagentStop",     "",                "worker_khai_xong_gate.py",      10),
    ("Stop",             "",                "worker_khai_xong_gate.py",      10),
    # P138 11/10/2026: khối «WORKER KẾT THÚC…» không in vào THỢ nữa — cất tệp chờ, in ở
    # lượt kế của main (lượt do task-notification mở cũng chạy UPS, đo 11/10).
    ("UserPromptSubmit", "",                "worker_khai_xong_gate.py",      10),
    # 29/8 (W187): có mã đã commit mà KHÔNG vé nào chờ đẩy -> kêu ngay lượt worker
    # kết thúc (SubagentStop) và chặn main khai "đã lên web" (Stop).
    ("SubagentStop",     "",                "deploy_ban_giao_gate.py",       10),
    ("Stop",             "",                "deploy_ban_giao_gate.py",       10),
    # 23/09 (W20): việc đã nghiệm thu ĐẠT + thợ khai `BAO-KHACH: có` -> TỰ báo nhóm
    # "Hệ thống Fulfill TheChic". `SubagentStop` bóc dòng khai trong báo cáo cuối của thợ
    # rồi gửi; `Stop` chỉ quét lại sổ (lưới an toàn khi lượt trước gửi hụt). Timeout 30s
    # vì nhánh gửi thật gọi `tg-notify.sh` (tự cắt ở 25s); không có ứng viên thì ~0,1s.
    ("SubagentStop",     "",                "bao_khach_gui.py hook",         30),
    ("Stop",             "",                "bao_khach_gui.py hook",         30),
    # LUẬT SỐ 1 chống đoán: chèn luật vào mọi prompt + chặn ngay trước khi sửa code
    ("UserPromptSubmit", "",                "no_guess_enforce.py",            5),
    ("PreToolUse",       "Write",           "no_guess_enforce.py",            5),
    ("PreToolUse",       "Edit",            "no_guess_enforce.py",            5),
    ("PreToolUse",       "MultiEdit",       "no_guess_enforce.py",            5),
    # watchdog giám sát worker nền: tự bật mỗi phiên + chèn cảnh báo vào context CLI
    ("SessionStart",     "",                "worker-watchdog.sh ensure",     10),
    ("UserPromptSubmit", "",                "worker-watchdog.sh cli-alerts", 10),
    # 27/8: watchdog tự thoát khi rảnh 45 phút mà CHỈ SessionStart bật lại ->
    # phiên dài cả ngày thì không ai canh worker. Dựng lại ở mỗi lượt gõ và
    # mỗi lần thả worker; `ensure` idempotent, ~0,04 giây nên gọi dày vô hại.
    ("UserPromptSubmit", "",                "worker-watchdog.sh ensure",      5),
    ("PreToolUse",       "Agent",           "worker-watchdog.sh ensure",      5),
    # 27/8: cổng "founder HỎI ≠ founder RA LỆNH" — phân loại lượt founder ở
    # UserPromptSubmit, chặn thả worker / lệnh có hậu quả khi lượt đó chỉ là
    # câu hỏi, góp ý hay thông tin.
    ("UserPromptSubmit", "",                "founder_lenh_gate.py",           5),
    ("PreToolUse",       "Agent",           "founder_lenh_gate.py",           5),
    ("PreToolUse",       "Bash",            "founder_lenh_gate.py",           5),
    # 07/09 (W01): SendMessage là ĐƯỜNG VÒNG giao việc cho worker ĐANG CHẠY — hai cổng dưới
    # trước nay chỉ canh Agent nên việc lọt thẳng, không bị soi. Chỉ chặn tin GIAO VIỆC MỚI.
    ("PreToolUse",       "SendMessage",     "founder_lenh_gate.py",           5),
    # 07/09 (W09): cổng "fix tận gốc" đứng TRƯỚC nhai_lai_gate — ưu tiên 1 vì nó CẤM
    # ĐẦU RA (không được vẽ giải pháp), hai cổng kia chỉ định dạng/định tuyến đầu ra.
    # CHỈ UserPromptSubmit, KHÔNG deny tool nào -> không khoá chết main.
    ("UserPromptSubmit", "",                "fix_tan_goc_gate.py",            5),
    # 27/8: 2 hook thêm từ máy local (founder quyết đẩy lên SSOT).
    # 29/8: nhại lại là BƯỚC 3. Chặn khối NHẠI LẠI viết khi lượt đó CHƯA chạy lệnh đọc
    # nào (đo 28/8: 9/12 khối nhại viết lúc chưa tra gì; 4/5 câu hỏi vô ích nằm đúng đó).
    ("Stop",             "",                "ve_de_sau_gate.py",             12),
    # 28/8: trùng vùng tệp -> SendMessage vào chính worker đang giữ, cấm đẻ con mới
    ("Stop",             "",                "worker_de_trung_vung_gate.py",  12),
    # 28/8: cấm tra DB dev (.env trần) rồi kết luận như dữ liệu thật
    ("PreToolUse",       "Bash",            "db_that_gate.py",                5),
    # 15/10 (W08): skill bot-nhan-viec §7e — thợ chỉ dùng --thu với lệnh duyệt lượt.
    ("PreToolUse",       "Bash",            "phuong_an_tho_gate.py",          5),
    # 29/8 (W192): cổng tự kiểm đĩa máy đang dùng — im khi an toàn, kêu kèm
    # cách dọn khi sắp hết chỗ. Không chặn việc, chỉ rót cảnh báo vào ngữ cảnh.
    ("UserPromptSubmit", "",                "disk_guard_enforce.py",          15),
    ("PreToolUse",       "Agent",           "disk_guard_enforce.py",          15),
    # 03/09 (W63): "bảng worker trống" KHÔNG bằng "hết việc". Chặn tất định lệnh gửi
    # báo cáo ngày lên nhóm Hệ thống khi còn worker sống / còn vé chờ / còn dòng
    # `ĐỂ LẠI:` chưa có vé — kiểm ngay tại thời điểm GỬI, không phải lúc bắt đầu viết.
    ("PreToolUse",       "Bash",            "chot_ngay_gate.py",              8),
    # 08/09 (W82): SỔ LỆNH FOUNDER (xem HOOK_FILES). BẮT BUỘC có ĐỦ 3 dòng này: install.py
    # xoá sạch mọi registration có tên trong HOOK_FILES rồi dựng lại từ đây — thêm tệp vào
    # HOOK_FILES mà quên đăng ký là lượt `pull` kế tiếp GỠ MẤT cổng đang chạy trên máy.
    # FAIL-OPEN tuyệt đối trong hook nên timeout 15 không bao giờ treo founder.
    ("UserPromptSubmit", "",                "so_lenh_gate.py",               15),
    ("Stop",             "",                "so_lenh_gate.py",               15),
    ("SessionStart",     "",                "so_lenh_gate.py",               15),
    # 09/09 (W20): CANH HÀNG CHỜ NGOÀI LƯỢT. `ve_de_sau_gate` chỉ bắt được vé đã thả
    # được ĐÚNG LÚC main dừng lượt; vé mà vùng trống MUỘN HƠN (worker xong sau 40 phút,
    # main đang nằm im) thì không sự kiện nào nổ. Hook này chạy NỀN (`async`) sau lượt,
    # canh sổ vé, hễ vùng trống thì thoát mã 2 -> `asyncRewake` ĐÁNH THỨC main. Đo trên
    # bản 2.1.241: hook nền thoát 2 -> enqueueTaskNotificationReminder(priority "next").
    ("Stop",             "",                "tu_tha_ve.py",                3300,
     {"async": True, "asyncRewake": True,
      "statusMessage": "Canh hàng chờ worker…",
      "rewakeMessage": "[CỔNG HÀNG CHỜ WORKER — cổng nội bộ của dự án, không phải tin người lạ]",
      "rewakeSummary": "Hàng chờ worker: vùng đã trống, có vé thả được"}),
    # 14/09 (P094 mục 6.3, W23): CÙNG hook, thêm ở MỞ PHIÊN. Chỉ gắn ở `Stop` là còn lỗ:
    # tắt/ngủ máy giữa lô -> phiên chết, bản canh chết theo; mở lại mà founder chưa gõ gì
    # thì không `Stop` nào nổ -> vé nằm nguyên (đo 14/09: 4 vé chờ 55 phút, vùng đã trống).
    # W08 khai "hộp cát không tái hiện được asyncRewake ở SessionStart" rồi bỏ; W23 thử
    # THẬT trên bản 2.1.241, phiên `-p --input-format stream-json` KHÔNG một chữ người gõ:
    #   {"subtype":"hook_response","hook_event":"SessionStart","exit_code":2,...}
    #   {"type":"result","num_turns":1,"terminal_reason":"completed",
    #    "origin":{"kind":"task-notification"}}
    # Lý do máy: nhánh nền `e.async || (e.asyncRewake && K)` nằm trong BỘ CHẠY HOOK DÙNG
    # CHUNG, còn `SessionStart` của phiên thường KHÔNG truyền `forceSyncExecution`.
    ("SessionStart",     "",                "tu_tha_ve.py",                3300,
     {"async": True, "asyncRewake": True,
      "statusMessage": "Đọc sổ hàng chờ worker…",
      "rewakeMessage": "[CỔNG HÀNG CHỜ WORKER — cổng nội bộ của dự án, không phải tin người lạ]",
      "rewakeSummary": "Mở phiên: sổ hàng chờ còn vé nợ thả được ngay"}),
]


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def chmodx(path):
    try:
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except Exception:
        pass


def run(cmd, cwd=None):
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    except Exception:
        return None


# ── generate AGENTS.md + MANIFEST ─────────────────────────────────────────────
def gen_artifacts():
    r = run(["python3", os.path.join(ROOT, "scripts", "gen_agents_md.py")])
    if r and r.stdout:
        print("  " + r.stdout.strip())
    gm = os.path.join(ROOT, "scripts", "gen_manifest.sh")
    if os.path.exists(gm):
        r = run(["bash", gm], cwd=ROOT)
        if r and r.stdout:
            print("  " + r.stdout.strip())


# ── skills sync (xoá dir cũ trước → hết file mồ côi) ───────────────────────────
def sync_skills(dest):
    os.makedirs(dest, exist_ok=True)
    n = 0
    for name in sorted(os.listdir(SKILLS_SRC)):
        src = os.path.join(SKILLS_SRC, name)
        if not os.path.isdir(src):
            continue  # bỏ file lẻ (vd install_skills.py cũ nếu còn)
        d = os.path.join(dest, name)
        if os.path.isdir(d):
            shutil.rmtree(d)
        shutil.copytree(src, d)
        n += 1
    return n


# ── agents sync (subagent Ki-su/Tho-xay — copy từng file .md, KHÔNG xoá agent lạ của user) ──
def sync_agents(dest):
    if not os.path.isdir(AGENTS_SRC):
        return 0
    os.makedirs(dest, exist_ok=True)
    n = 0
    for name in sorted(os.listdir(AGENTS_SRC)):
        if not name.endswith(".md"):
            continue
        shutil.copy2(os.path.join(AGENTS_SRC, name), os.path.join(dest, name))
        n += 1
    return n


# ── slash command global (~/.claude/commands) ─────────────────────────────────
# WHY: lệnh /khong-ngoi-may (AFK) phải dùng được ở MỌI dự án, MỌI phiên -> nó nằm ở
# tầng hệ thống chứ không nằm trong .claude/commands của một kho mã. Chỉ chép file .md
# do univ3 sở hữu, KHÔNG xoá lệnh lạ founder tự viết.
def sync_commands(dest):
    if not os.path.isdir(COMMANDS_SRC):
        return 0
    os.makedirs(dest, exist_ok=True)
    n = 0
    for name in sorted(os.listdir(COMMANDS_SRC)):
        if not name.endswith(".md"):
            continue
        shutil.copy2(os.path.join(COMMANDS_SRC, name), os.path.join(dest, name))
        n += 1
    return n

# ── git pre-commit ────────────────────────────────────────────────────────────
def install_precommit(project):
    gitdir = os.path.join(project, ".git")
    if not os.path.isdir(gitdir):
        print(f"  (bỏ qua pre-commit: {project} không phải git repo)")
        return
    hooks = os.path.join(gitdir, "hooks")
    os.makedirs(hooks, exist_ok=True)
    dst = os.path.join(hooks, "pre-commit")
    if os.path.exists(dst) and "univ3" not in open(dst, encoding="utf-8", errors="ignore").read():
        shutil.copy2(dst, dst + ".bak")
        print(f"  ~ backup pre-commit cũ -> {dst}.bak")
    shutil.copy2(os.path.join(ROOT, "enforce", "pre-commit"), dst)
    chmodx(dst)
    print(f"  + git pre-commit -> {dst}")


# ── claude ────────────────────────────────────────────────────────────────────
def install_claude():
    os.makedirs(CLAUDE_HOOKS_DEST, exist_ok=True)
    copied = []
    for name in HOOK_FILES:
        src = os.path.join(HOOKS_SRC, name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(CLAUDE_HOOKS_DEST, name))
            chmodx(os.path.join(CLAUDE_HOOKS_DEST, name))
            copied.append(name)
    shutil.copy2(SPINE, os.path.join(CLAUDE_HOOKS_DEST, "SPINE.md"))  # global default spine
    tconf = os.path.join(HOOKS_SRC, "telegram_config.env.example")
    if os.path.exists(tconf):
        shutil.copy2(tconf, os.path.join(CLAUDE_HOOKS_DEST, "telegram_config.env.example"))

    settings = {}
    if os.path.exists(SETTINGS):
        shutil.copy2(SETTINGS, SETTINGS + ".bak")  # backup
        try:
            settings = json.load(open(SETTINGS, encoding="utf-8"))
        except Exception:
            settings = {}

    # purge entry univ3/universal cũ (self-migrate)
    hooks = settings.get("hooks", {})
    names = tuple(HOOK_FILES)
    for ev in list(hooks.keys()):
        kept = []
        for entry in hooks[ev]:
            hs = [h for h in entry.get("hooks", []) if not any(n in h.get("command", "") for n in names)]
            if hs:
                entry["hooks"] = hs
                kept.append(entry)
        if kept:
            hooks[ev] = kept
        else:
            del hooks[ev]

    added = 0
    for dong in REGISTRATIONS:
        # Phần tử thứ 5 (tuỳ chọn) = dict trường thêm cho hook, vd async/asyncRewake.
        ev, matcher, base, timeout = dong[:4]
        them = dict(dong[4]) if len(dong) > 4 and dong[4] else {}
        base, _, extra = base.partition(" ")   # hook có thể kèm tham số (vd "x.sh ensure")
        path = os.path.join(CLAUDE_HOOKS_DEST, base)
        if not os.path.exists(path):
            continue
        cmd = f'{INTERP.get(base, "python3")} "{path}"' + (f" {extra}" if extra else "")
        mot = {"type": "command", "command": cmd, "timeout": timeout}
        mot.update(them)
        settings.setdefault("hooks", {}).setdefault(ev, []).append(
            {"matcher": matcher, "hooks": [mot]})
        added += 1

    os.makedirs(os.path.dirname(SETTINGS), exist_ok=True)
    with open(SETTINGS, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
        f.write("\n")

    ns = sync_skills(CLAUDE_SKILLS_DEST)
    na = sync_agents(CLAUDE_AGENTS_DEST)
    nc = sync_commands(CLAUDE_COMMANDS_DEST)
    print(f"  Claude: {len(copied)} hook -> {CLAUDE_HOOKS_DEST}; {added} registration -> settings.json (đã .bak); {ns} skill -> {CLAUDE_SKILLS_DEST}; {na} agent -> {CLAUDE_AGENTS_DEST}; {nc} lệnh -> {CLAUDE_COMMANDS_DEST}")
    if not os.path.exists(os.path.join(CLAUDE_HOOKS_DEST, "telegram_config.env")):
        print("  NOTE: notify tự im tới khi tạo ~/.claude/universal-hooks/telegram_config.env (copy từ .example).")


# ── lịch máy dọn rác ──────────────────────────────────────────────────────────
# WHY: luật SPINE bắt agent tự tắt tiến trình nền, hai script dọn là lưới an toàn cuối —
# nhưng trước 30/10/2026 install.py chỉ CHÉP script, không cắm lịch: máy mới cài univ3 có
# lưới mà không ai kéo. Nay macOS tự cắm 2 LaunchAgent (1800 giây), Linux in dòng crontab.
LICH_DON_GIAY = 1800
LICH_DON_CU = ["local.don-may"]   # nhãn cũ cắm tay trước khi lên SSOT — gỡ để khỏi chạy đôi


def _lich_don_macos():
    import plistlib
    home = os.path.expanduser("~")
    la_dir = os.path.join(home, "Library", "LaunchAgents")
    logs = os.path.join(home, ".claude", "logs")
    dm_dir = os.path.join(home, ".claude", "don-may")
    os.makedirs(la_dir, exist_ok=True)
    os.makedirs(logs, exist_ok=True)
    os.makedirs(dm_dir, exist_ok=True)
    reaper = os.path.join(CLAUDE_HOOKS_DEST, "stale-server-reaper.sh")
    donmay = os.path.join(CLAUDE_HOOKS_DEST, "don-may.sh")
    reaper_log = os.path.join(logs, "stale-server-reaper.log")
    nk = os.path.join(dm_dir, "nhat-ky.log")
    viec = {
        "univ3.stale-server-reaper": {
            "Label": "univ3.stale-server-reaper",
            "ProgramArguments": ["/bin/bash", "-c",
                                 f'date "+== %Y-%m-%d %H:%M:%S"; exec /bin/bash "{reaper}" run 60'],
            "RunAtLoad": True,
            "StandardErrorPath": reaper_log,
            "StandardOutPath": reaper_log,
            "StartInterval": LICH_DON_GIAY,
        },
        "univ3.don-may": {
            "Label": "univ3.don-may",
            # Dòng XOÁ từng thư mục quá nhiều → bỏ khỏi nhật ký; nhật ký giữ 2000 dòng cuối.
            "ProgramArguments": ["/bin/bash", "-c",
                                 f'"{donmay}" chay 2>&1 | grep -v \'^XOÁ\' >> "{nk}"; '
                                 f'tail -n 2000 "{nk}" > "{nk}.tmp" && mv "{nk}.tmp" "{nk}"'],
            "RunAtLoad": True,
            "StartInterval": LICH_DON_GIAY,
            "ProcessType": "Background",
            "LowPriorityIO": True,
            "Nice": 10,
        },
    }
    dom = f"gui/{os.getuid()}"

    def dang_nap(label):
        return subprocess.run(["launchctl", "print", f"{dom}/{label}"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

    def go(label):
        subprocess.run(["launchctl", "bootout", f"{dom}/{label}"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def nap(path):
        r = subprocess.run(["launchctl", "bootstrap", dom, path], capture_output=True, text=True)
        return r.returncode == 0, (r.stderr or r.stdout).strip()

    for cu in LICH_DON_CU:
        pcu = os.path.join(la_dir, cu + ".plist")
        if os.path.exists(pcu) or dang_nap(cu):
            go(cu)
            if os.path.exists(pcu):
                bk = os.path.join(home, ".claude", "backups")
                os.makedirs(bk, exist_ok=True)
                shutil.move(pcu, os.path.join(bk, f"{cu}.plist.da-thay-boi-univ3"))
            print(f"  ~ gỡ lịch cũ {cu} (đã thay bằng univ3.don-may)")

    for label, muon in viec.items():
        path = os.path.join(la_dir, label + ".plist")
        dang = None
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    dang = plistlib.load(f)
            except Exception:
                dang = None
        if dang == muon and dang_nap(label):
            print(f"  = lịch {label}: đã cắm, giữ nguyên")
            continue
        if dang != muon:
            with open(path, "wb") as f:
                plistlib.dump(muon, f)
            go(label)   # nội dung đổi → nạp lại; chưa nạp thì lệnh này vô hại
        ok, loi = nap(path)
        if ok or dang_nap(label):
            print(f"  + lịch {label}: cắm, {LICH_DON_GIAY} giây/lần")
        else:
            print(f"  ! lịch {label}: launchctl bootstrap lỗi — {loi}")
    if not os.path.exists(os.path.join(dm_dir, "cau-hinh.sh")):
        print(f"  NOTE: don-may chưa có cấu hình riêng máy → chép {CLAUDE_HOOKS_DEST}/don-may.cau-hinh.example"
              f" thành {dm_dir}/cau-hinh.sh nếu muốn dọn thêm .next dự án / nhật ký app.")


def _lich_don_linux():
    reaper = os.path.join(CLAUDE_HOOKS_DEST, "stale-server-reaper.sh")
    try:
        hien = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
    except Exception:
        hien = ""
    if "stale-server-reaper.sh" in hien:
        print("  = lịch stale-server-reaper: crontab đã có, giữ nguyên")
        return
    # univ3 chưa có tiền lệ tự ghi crontab của người dùng → chỉ in dòng để người tự thêm.
    print("  NOTE: Linux — thêm lịch dọn rác bằng `crontab -e`, dán dòng:")
    print(f"    */30 * * * * /bin/bash {reaper} run 60 >> $HOME/.claude/logs/stale-server-reaper.log 2>&1")
    print("    (don-may.sh chỉ chạy macOS; Linux chỉ cần stale-server-reaper.sh.)")


def install_lich_don():
    if "--khong-lich" in sys.argv:
        print("  (bỏ qua lịch máy dọn: --khong-lich)")
        return
    if sys.platform == "darwin":
        _lich_don_macos()
    elif sys.platform.startswith("linux"):
        _lich_don_linux()


# ── codex ─────────────────────────────────────────────────────────────────────
def install_codex():
    ns = sync_skills(CODEX_SKILLS_DEST)
    os.makedirs(CODEX_HOOKS_DEST, exist_ok=True)
    for name in HOOK_FILES:
        src = os.path.join(HOOKS_SRC, name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(CODEX_HOOKS_DEST, name))
    print(f"  Codex: {ns} skill -> {CODEX_SKILLS_DEST}; hook (tuỳ chọn) -> {CODEX_HOOKS_DEST}")
    print(f"  → Copy AGENTS.md vào root project (Codex đọc natively). Wiring hook config.toml: xem enforce/codex/README.md.")


def main():
    harness = arg("--harness", "all")
    project = os.path.abspath(arg("--project", os.getcwd()))
    print(f"univ3 install — harness={harness}, project={project}")
    gen_artifacts()
    if harness in ("claude", "all"):
        install_claude()
        install_lich_don()
    if harness in ("codex", "all"):
        install_codex()
    install_precommit(project)
    print("Xong. (Claude: mở phiên mới để hook nạp. Codex: đảm bảo AGENTS.md ở root + < 32KiB.)")


if __name__ == "__main__":
    main()
