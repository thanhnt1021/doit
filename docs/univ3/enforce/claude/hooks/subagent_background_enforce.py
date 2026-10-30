#!/usr/bin/env python3
"""subagent_background_enforce.py — PreToolUse(Agent) soft-gate.

Rule "1 main, mọi subagent chạy NGẦM" (AGENTS-ORCH.md) chỉ là markdown = xác suất
-> agent hay quên set run_in_background. Chuyển thành CỔNG tất định:

  Agent call ĐẶT run_in_background:false  -> permissionDecision "allow" + lời nhắc.
  THIẾU field  -> CHO QUA (harness đã mặc định chạy NGẦM).

SỬA 2026-08-26 — trước đây hook đòi `run_in_background is True` mới cho qua. Đo thật
trên claude-code 2.1.241, `sdk-tools.d.ts` AgentInput ghi rõ: *"Agents run in the
background by default"*, và schema tool Agent phát cho model KHÔNG còn expose field
này -> model không thể truyền -> điều kiện KHÔNG BAO GIỜ thoả -> hook hỏi VĨNH VIỄN
dù subagent vốn đã chạy nền. Founder đi vắng, mỗi lần hỏi là kẹt cả phiên.
Nay chỉ hỏi khi có người CỐ TÌNH tắt nền (`run_in_background: false`) — đúng ý định
ban đầu, hết hỏi oan.

Fail-open: mọi lỗi -> exit 0 (cho qua), không bao giờ vỡ phiên.
"""
import json
import os
import re
import sys
import unicodedata

# Tên tool spawn subagent, phòng cả 2 đời harness (Agent mới / Task cũ).
AGENT_TOOLS = {"Agent", "Task"}

# ===== CỔNG 2: brief con PHẢI kèm câu ghi mốc (thêm 03/09/2026, W16) =====
# CA THẬT: 03/09/2026 W07 (subagent điều phối) đẻ 6 worker lô A-F lúc 08:05-08:07, brief
# của cả 6 KHÔNG có câu ghi mốc -> 5 con ghi 0 lần -> `worker_board.slug_td_cua_agent()`
# trả '' -> bảng vẽ chúng 0% suốt vòng đời rồi mất hút khi xong. Lô E (W10) do MAIN đẻ,
# brief CÓ câu ghi -> ghi 7 lần, bảng chạy đúng. Tương quan 18/18 agent trong phiên.
# WHY cổng nằm ở PreToolUse(Agent) chứ không thêm dòng markdown: luật "brief phải kèm câu
# ghi mốc" hiện CHỈ sống trong `delegate_subagent_reminder.sh` — hook UserPromptSubmit,
# chỉ bắn cho lượt chat của MAIN, KHÔNG bao giờ tới subagent. Subagent đi đẻ con thì
# không ai nhắc nó. PreToolUse thì bắn cả trong subagent (đo thật: hook
# progress_format_enforce.py deny được lệnh Bash của W16 — chính là một subagent).
RX_TEN_MOC = re.compile(r"^w\d{1,4}-[a-z0-9-]+\.progress$")
RX_DUONG_MOC = re.compile(r"/tmp/claude-bg-progress/[^/\s]+/([^/\s`]+?\.progress)")
# Chỉ bật cổng khi phiên CHA thật sự đang chạy bảng worker — tức transcript của nó đã có
# ít nhất một câu GHI mốc (`> …/*.progress`). Ngoài chế độ đó (project khác, phiên chat
# thường) cổng im lặng, không chặn oan Explore/code-review.
RX_CHA_CO_GHI = re.compile(r">\s*/tmp/claude-bg-progress/")


def _bo_dau(t):
    try:
        t = unicodedata.normalize("NFD", t)
        t = "".join(c for c in t if unicodedata.category(c) != "Mn")
        t = unicodedata.normalize("NFC", t).replace("đ", "d").replace("Đ", "D").lower()
        return re.sub(r"[^a-z0-9.-]+", "-", t).strip("-")
    except Exception:
        return ""


def _cha_dang_chay_bang(duong_dan):
    """Transcript phiên cha đã có câu ghi mốc nào chưa. Đọc theo khối, thoát sớm khi thấy."""
    try:
        with open(duong_dan, encoding="utf-8", errors="replace") as fh:
            while True:
                khoi = fh.read(1 << 20)
                if not khoi:
                    return False
                if RX_CHA_CO_GHI.search(khoi):
                    return True
    except OSError:
        return False


def _du_an(cwd):
    return os.path.basename(str(cwd or "").rstrip("/")) or "<project>"


def _mau_brief(desc, du_an):
    goi = _bo_dau(desc) or "viec"
    return ("Ghi tiến độ sau mỗi bước chính (lệnh Bash RIÊNG, KHÔNG gộp với rm/git commit/"
            "git push/build — hook deny sẽ giết cả lệnh, mốc không bao giờ được ghi):\n"
            "  echo 'NN|<nhãn tiếng Việt có dấu, <=60 ký tự>' > "
            "/tmp/claude-bg-progress/%s/w<số>-%s.progress\n"
            "  Mốc NN: số nguyên 0-100. Slug KHÔNG DẤU, chỉ [a-z0-9-]." % (du_an, goi[:40]))


def _soi_brief(ti, cwd):
    """None = cho qua. Chuỗi = lý do CHẶN."""
    prompt = str(ti.get("prompt") or "")
    desc = str(ti.get("description") or "").strip()
    ten = [m.group(1) for m in RX_DUONG_MOC.finditer(prompt)]
    if not ten:
        return ("⛔ CHẶN — brief của subagent «%s» THIẾU câu ghi mốc tiến độ.\n"
                "Thiếu nó thì worker đứng 0%% trên bảng suốt vòng đời rồi biến mất khi xong "
                "(ca thật 03/09/2026: 5 worker viết bài lô A-F, 0 lần ghi, founder mù tiến độ).\n"
                "Brief CON KHÔNG thừa hưởng luật của brief CHA — phải chép tay vào.\n"
                "Huỷ lệnh này, thêm đoạn sau vào brief rồi phát lại:\n\n%s"
                % (desc or "?", _mau_brief(desc, _du_an(cwd))))
    xau = [t for t in ten if not RX_TEN_MOC.match(t)]
    if xau:
        sua = _bo_dau(xau[0])
        them = ("\n  Sửa thành: `%s`." % sua) if RX_TEN_MOC.match(sua) else ""
        return ("⛔ CHẶN — brief của subagent «%s» đặt tên tệp mốc SAI KHUÔN: `%s`.\n"
                "Phải là `w<số>-<slug>.progress`, slug KHÔNG DẤU chỉ [a-z0-9-]. Tên sai thì "
                "progress_format_enforce.py deny ngay lệnh ghi ĐẦU TIÊN của worker, còn "
                "worker_board.py đọc cụt tên nên ghép mốc nhầm sang worker khác.%s"
                % (desc or "?", xau[0], them))
    lech = _lech_so(desc, ten)
    if lech:
        return lech
    return None


# ===== CỔNG 3: SỐ trong tên tệp mốc phải KHỚP số mở đầu `description` (W11, 19/09/2026) =====
# CA THẬT 19/09/2026: brief gọi thợ là W04 và bắt ghi `w04-ra-task-roi.progress`, nhưng sổ
# `wseq` cấp số W07 nên `description` mở đầu bằng "W07". Cổng `worker_khai_xong_gate` tra
# mốc theo tiền tố mã (`w07-`), không thấy tệp nào -> rơi xuống bản `done/` của HÔM TRƯỚC,
# việc KHÁC (`…__w07-printbelle-chan-oan__bo-do`) -> hai lần phán oan thợ đang chạy "dừng ở
# 95%, đang deploy", đồng thời để lọt đúng việc Printbelle bỏ dở. Một brief chỉ được mang
# MỘT con số: số của sổ. Đây là chỗ rẻ nhất ép điều đó, vì `description` và tên tệp mốc nằm
# cạnh nhau ngay trong cùng một lượt thả.
RX_SO_MO_TA = re.compile(r"^\s*W(\d{1,4})\b", re.I)
RX_SO_TEP = re.compile(r"^w(\d{1,4})-", re.I)


def _lech_so(desc, ten):
    """Chuỗi CHẶN nếu số trong tên tệp mốc khác số mở đầu mô tả. None = cho qua.

    Mô tả KHÔNG mở đầu bằng `W##` (agent do thợ tự đẻ: ki-su, tho-xay…) thì bỏ qua —
    không có số sổ để đối chiếu, thắt vào chỉ chặn oan."""
    m = RX_SO_MO_TA.match(desc or "")
    if not m:
        return None
    so_mo_ta = int(m.group(1))
    for t in ten:
        mt = RX_SO_TEP.match(t)
        if mt and int(mt.group(1)) != so_mo_ta:
            return ("⛔ CHẶN — brief «%s» mang HAI con số khác nhau: mô tả nói **W%02d**, "
                    "tên tệp mốc lại là `%s`.\n"
                    "Cổng đếm tra mốc theo TIỀN TỐ MÃ, lệch số là nó không thấy tệp của thợ "
                    "này rồi bốc nhầm tệp `done/` của việc khác làm bằng chứng (ca thật "
                    "19/09/2026: W04/W07 -> cổng hai lần phán oan một thợ «dừng ở 95%%, đang "
                    "deploy» trong khi nó chưa deploy gì).\n"
                    "SỬA: lấy số từ sổ `wseq` làm số DUY NHẤT — đổi tên tệp mốc thành "
                    "`w%02d-<slug>.progress` (hoặc sửa mô tả cho khớp số tệp), rồi phát lại."
                    % (desc[:60], so_mo_ta, t, so_mo_ta))
    return None

# ===== CỔNG 4: VIỆC CÓ GIAO DIỆN MÀ BRIEF KHÔNG BẮT CHỤP ẢNH -> NHẮC (W28, 21/09/2026) =====
# CA THẬT 21/09/2026: bốn brief thả trong ngày thì BA cái không có một chữ nào nhắc chụp
# màn — `grep -ci "chụp màn\|chụp ảnh\|docs/anh" /tmp/brief-w08.md /tmp/brief-w16.md
# /tmp/brief-w21.md` = 0, chỉ `/tmp/brief-w25.md` có. Hậu quả đo được: việc founder quan
# tâm nhất trong ngày (dòng thời gian của đơn + gom dải trạng thái thành ba mốc) vào báo
# cáo dưới dạng CHỮ SUÔNG kèm câu "không có màn hình để chụp"; founder mở ra không thấy:
# *"sao tao không thấy phần update timeline và chia phần mới đâu?"*
# WHY cổng nằm ở ĐÂY chứ không ở báo cáo ngày: luật #11 (SESSION_SPINE) có đủ, nhưng cổng
# chặn duy nhất là `docs/templates/kiem-bao-cao-ngay.py` — gác ở CUỐI ĐƯỜNG. Lúc báo cáo
# ngày chạy thì worker đã đóng, màn hình đã khác, KHÔNG ai chụp bù được nữa.
# WHY CHỈ NHẮC, KHÔNG CHẶN: founder chốt 21/09/2026 qua AskUserQuestion — *"Chỉ nhắc,
# không chặn"*.
# WHY KHÔNG trả `permissionDecision`: cổng này chạy cùng matcher `Agent` với các cổng
# CHẶN thật (`worker_cap_enforce`, `tien_kiem_gate`, `founder_lenh_gate`). Tài liệu
# claude-code KHÔNG nói rõ `allow` của hook này có đè `deny` của hook kia không -> trả
# quyết định chỉ để nhắc là canh bạc nới cổng. Chỉ rót `additionalContext` (PreToolUse có
# hỗ trợ) + `systemMessage`: chữ vào ngữ cảnh, luồng quyết định KHÔNG đụng tới.
RX_MAN_TEP = re.compile(r"\.(?:tsx|jsx|vue|svelte|css|scss)$", re.I)
# Chỉ nhận ĐOẠN đường dẫn đứng riêng (`src/app/orders`), KHÔNG nhận `scripts/app-config.ts`
# — dính chữ là nhận nhầm, kêu oan vài lần là người ta bơ cảnh báo luôn.
RX_MAN_THUMUC = re.compile(r"(?:^|/)(?:app|pages|components|views|screens)(?:/|$)", re.I)
# Loại trừ TẤT ĐỊNH: `src/app/api/...` là route API (Next.js nhét API trong cùng cây với
# màn), test/e2e/story không phải màn thật của người dùng.
RX_KHONG_MAN = re.compile(
    r"(?:^|/)(?:api|e2e|__tests__|__mocks__|node_modules|migrations)(?:/|$)"
    r"|\.(?:test|spec|stories|d)\.[a-z0-9]+$", re.I)
RX_BAT_CHUP = re.compile(
    r"ch[ụu]p\s*(?:m[àa]n|[ảa]nh|h[ìi]nh)|screenshot|[ảa]nh\s*(?:tr[ưu][ớo]c|sau)|"
    r"tr[ưu][ớo]c\s*/\s*sau|docs/anh|-shots/", re.I)


def _token_ghi(prompt):
    """Đường dẫn THÔ trong các dòng `GHI:` của brief.

    Chỉ đọc LỜI KHAI, KHÔNG suy vùng từ văn xuôi — đúng giao kèo đã chốt 07/09/2026
    (`worker_cap_enforce.vung_viec_moi`): brief KHAI, cổng ĐỌC KHAI. Dùng lại đúng regex
    khai của cổng đó để không đẻ bản luật thứ hai.
    """
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from worker_cap_enforce import RX_KHAI
    except Exception:
        return []
    ra = []
    for m in RX_KHAI.finditer(prompt or ""):
        for tok in re.split(r"[\s,;]+", re.sub(r"\([^()]*\)", " ", m.group(1))):
            tok = tok.strip().strip("\"'`,;.·*").rstrip("/")
            if tok and tok not in ("-", "--", "\u2013", "\u2014"):
                ra.append(tok)
    return ra


def vung_man(prompt):
    """Đường dẫn GIAO DIỆN mà brief khai sẽ GHI. [] = việc không đụng màn nào -> im.

    `dict.fromkeys` = khử trùng lặp mà GIỮ thứ tự: `RX_KHAI` gộp hai khuôn (đầu dòng +
    giữa dòng) nên một dòng `GHI:` khớp cả hai -> cùng một đường dẫn ra hai lần, lời nhắc
    in ra bị lặp trông như hai chỗ khác nhau."""
    ra = []
    for tok in dict.fromkeys(_token_ghi(prompt)):
        if RX_KHONG_MAN.search(tok):
            continue
        if RX_MAN_TEP.search(tok) or RX_MAN_THUMUC.search(tok):
            ra.append(tok)
    return ra


def nhac_anh(prompt, desc, du_an):
    """Chữ nhắc chụp ảnh ('' = không có gì để nhắc). Dùng chung với cổng lúc worker
    khai xong (`worker_khai_xong_gate.py`) — một bản luật, hai chỗ gọi."""
    prompt = str(prompt or "")
    if RX_BAT_CHUP.search(prompt):
        return ""                      # brief đã bắt chụp -> im tuyệt đối
    vung = vung_man(prompt)
    if not vung:
        return ""                      # việc thuần dữ liệu/tài liệu/hạ tầng -> im
    return (u"⚠️  VIỆC NÀY CÓ GIAO DIỆN MÀ BRIEF KHÔNG BẮT CHỤP ẢNH "
            u"(cổng nhắc W28 — CHỈ NHẮC, KHÔNG CHẶN, cứ thả tiếp)\n"
            u"   Brief «%s» khai `GHI:` %s -> người ta NHÌN THẤY kết quả việc này.\n"
            u"   Luật #11 (docs/SESSION_SPINE.md): việc có giao diện phải chụp màn NGAY "
            u"LÚC LÀM, sửa màn đã có thì chụp CẶP TRƯỚC/SAU, khoanh chỗ vừa đổi.\n"
            u"   Ảnh KHÔNG chụp bù được: lúc chốt ngày worker đã đóng, màn hình đã khác.\n"
            u"   Chép câu này vào brief rồi phát lại:\n"
            u"     «Chụp màn NGAY LÚC LÀM, cặp TRƯỚC/SAU cho màn đã có, để ở "
            u"/tmp/w<số>-shots/ (bản giữ lại: docs/anh-w<số>/), khoanh chỗ vừa đổi + một "
            u"câu chú thích tiếng Việt, GHI ĐƯỜNG DẪN ẢNH vào báo cáo cuối. Không có gì "
            u"hiện ra thì nói thẳng lý do trong báo cáo.»\n"
            u"   Ca thật 21/09/2026: 3/4 brief trong ngày thiếu câu này; việc founder hỏi "
            u"nhiều nhất về tới tay founder dưới dạng chữ suông, không một tấm ảnh."
            % ((desc or "?")[:60], " ".join(vung[:4]) + (" …" if len(vung) > 4 else "")))


# 2026-08-26 (lần 2): đổi "ask" -> "allow + nhắc". Founder đi vắng, mọi cổng HỎI đều
# treo phiên; chỉ giữ chặn cứng cho thứ làm mất dữ liệu / mất tài khoản.
NHAC = ("⛔ Subagent «{desc}» bị đặt run_in_background:false -> chạy FOREGROUND. "
        "Rule univ3: 1 main, MỌI subagent phải NGẦM để phiên chính trống cho user chat. "
        "Chỉ giữ foreground khi user đang chờ kết quả ngay để quyết bước kế; nếu không "
        "-> huỷ & phát lại, BỎ field đó đi (mặc định đã ngầm).")


def main() -> None:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        sys.exit(0)

    if str(data.get("tool_name") or "") not in AGENT_TOOLS:
        sys.exit(0)

    ti = data.get("tool_input") or {}

    # --- CỔNG 5 (W102, 09/10/2026): model mặc định CHỈ Opus, Fable chỉ khi anh cho ---
    # WHY ở đây: cổng sống ở matcher Agent, bắn cả cho main LẪN worker (thợ cũng thả con).
    # Luật nằm ở `model_opus.py` — một bản, nhai_lai_gate.soi_c7a dùng chung.
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from model_opus import soi_model
        ly_do_model = soi_model(ti)
    except Exception:
        ly_do_model = None             # fail-open
    if ly_do_model:
        json.dump({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "⛔ CHẶN — %s\nSỬA: bỏ trường `model` hoặc đặt `opus`. Anh đã bảo dùng Fable "
                "cho việc này thì thêm vào brief dòng `ANH-CHO-FABLE: <chép nguyên văn câu "
                "anh>` rồi phát lại." % ly_do_model),
        }}, sys.stdout, ensure_ascii=False)
        sys.exit(0)

    # --- CỔNG 2: brief con phải kèm câu ghi mốc (chỉ bật trong phiên đang chạy bảng) ---
    if _cha_dang_chay_bang(str(data.get("transcript_path") or "")):
        ly_do = _soi_brief(ti, data.get("cwd"))
        if ly_do:
            json.dump(
                {"hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": ly_do,
                }},
                sys.stdout, ensure_ascii=False,
            )
            sys.exit(0)

    desc = str(ti.get("description") or ti.get("subagent_type") or "subagent").strip()

    # --- CỔNG 4 (W28): việc có giao diện mà brief không bắt chụp ảnh -> NHẮC, không chặn ---
    try:
        chu_anh = nhac_anh(ti.get("prompt"), desc, _du_an(data.get("cwd")))
    except Exception:
        chu_anh = ""

    # Mặc định của harness là NGẦM -> chỉ soi khi bị tắt tường minh.
    if ti.get("run_in_background") is not False:
        if chu_anh:
            # KHÔNG kèm `permissionDecision`: xem WHY ở đầu CỔNG 4 — chỉ rót chữ, không
            # chạm vào luồng quyết định của các cổng CHẶN cùng matcher `Agent`.
            json.dump({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                              "additionalContext": chu_anh},
                       "systemMessage": chu_anh},
                      sys.stdout, ensure_ascii=False)
        sys.exit(0)

    chu = NHAC.format(desc=desc) + (("\n\n" + chu_anh) if chu_anh else "")
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": chu,
                "additionalContext": chu,
            }
        },
        sys.stdout,
        ensure_ascii=False,
    )


if __name__ == "__main__":
    main()
