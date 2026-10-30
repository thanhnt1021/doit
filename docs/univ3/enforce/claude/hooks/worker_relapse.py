#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""worker_relapse.py — WORKER BỊ DỪNG GIỮA CHỪNG TỰ QUAY LẠI HÀNG CHỜ.

VÌ SAO CÓ TỆP NÀY (27/08/2026, hai lần trong một buổi sáng):
  Lần 1 ~10:40 — founder: *"pause vụ HGT lại để không bị chạm trần worker, hoặc stop HGT
  với những gì đang làm được và bỏ W20 vào hàng chờ"*. Điều phối gọi `TaskStop` giết worker
  HGT nhưng KHÔNG đưa vào hàng chờ. Việc nằm chết 2 tiếng, trên bảng chỉ còn một dòng rác
  "58% · ❓ không tìm thấy agent". Founder phải tự phát hiện: *"tại sao nó lại treo?????
  bố mày đã bảo khi nào có chỗ trống thì phải đưa nó vào chờ mà???"*
  Lần 2 — điều phối nói "em cho bịt nốt chỗ này" rồi không giao cho ai.

LỖ HỔNG ĐO ĐƯỢC (không đoán): `worker_queue.py` chỉ tạo vé ở ĐÚNG MỘT cổng — nhánh
`PreToolUse Agent` của `worker_cap_enforce.py` (dòng 594 trùng vùng, dòng 657 vượt trần).
Worker ĐÃ CHẠY rồi mới bị `TaskStop`/kill/chết vì lỗi thì KHÔNG có đường nào sinh vé:
không vé, không ai nhắc, không tự thả lại. Người điều phối phải tự nhớ — đã quên 2 lần.

CÁCH BỊT (tất định, không phải markdown): mỗi lượt `UserPromptSubmit`/`SubagentStop`,
quét transcript agent của dự án; agent nào ĐÃ KẾT THÚC mà CHƯA trả báo cáo cuối và chưa
đạt 100% -> dựng lại vé hàng chờ từ chính brief NGUYÊN VĂN trong transcript phiên cha,
kèm mốc %, nhãn tiến độ cuối và dấu vết commit/stash nó để lại.

PHÂN BIỆT (chống vé rác — cốt lõi):
  - agent còn sống                       -> bỏ qua
  - harness chưa báo kết thúc            -> bỏ qua (chưa chết)
  - đuôi transcript: assistant `stop_reason` = end_turn/stop_sequence -> ĐÃ TRẢ BÁO CÁO
    CUỐI = xong việc -> KHÔNG vé  (sửa 28/8: trước xét "có TEXT mà không gọi tool" -> phán
    nhầm ngay giữa lượt worker vừa nói vừa làm, việc bị dừng không được dựng lại vé)
  - tệp tiến độ >= 100                   -> xong việc -> KHÔNG vé
  - đang có worker sống cùng slug        -> việc đã được thả lại rồi -> KHÔNG vé
  - còn lại (bị TaskStop / [Request interrupted] / chết giữa chừng) -> TẠO VÉ

Mỗi agent chỉ xét MỘT lần (sổ `.da-xet.json` theo agent-id + mtime) nên chạy mọi lượt
vẫn rẻ. Fail-open tuyệt đối: hỏng gì cũng trả 0 vé, không bao giờ chặn lượt của founder.
"""
import glob
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PROJECTS_ROOT = os.environ.get("UNIV3_PROJECTS_ROOT", os.path.expanduser("~/.claude/projects"))
PROGRESS_ROOT = os.environ.get("UNIV3_PROGRESS_ROOT", "/tmp/claude-bg-progress")
# Chỉ dựng lại vé cho worker chết trong ngần này giờ. Xa hơn thì việc đã cũ, dựng vé chỉ
# làm ngập hàng chờ bằng thứ founder không còn cần.
CUA_SO_GIO = float(os.environ.get("UNIV3_RELAPSE_HOURS", "12"))
DUOI_DOC = 512 * 1024          # đuôi transcript agent: đủ thấy lượt cuối
DAU_VET_DOC = 2 * 1024 * 1024  # quét dấu vết commit/stash
CHA_DOC = 8 * 1024 * 1024
NGAT = "[Request interrupted by user]"

RX_TASK_ID = re.compile(r"<task-id>\s*([0-9A-Za-z_-]+)\s*</task-id>")
RX_STATUS = re.compile(r"<status>\s*([A-Za-z_-]+)\s*</status>")
KET_THUC = {"completed", "killed", "failed", "error", "errored",
            "cancelled", "canceled", "timeout", "timed_out"}
# NGUỒN THỨ HAI, MẠNH HƠN — BẢNG DANH SÁCH SUBAGENT harness tự chèn vào transcript cha:
#     Subagents (8):
#       acf53d51a3d18e67e  ·  general-purpose  ·  completed  ·  started 1h ago
#       a56af5d9dca91d057  ·  general-purpose  ·  killed     ·  started 4m ago
# Đo 27/8: worker W114 và W66 bị `TaskStop` KHÔNG hề có khối <task-notification> nào trong
# transcript cha (chỉ có tool_use TaskStop rồi im) -> cơ chế cũ bám mỗi <task-id>/<status>
# coi chúng CÒN SỐNG mãi mãi -> đúng cái đẻ ra dòng ma trên bảng. Bảng danh sách này thì
# harness làm mới liên tục và có TRẠNG THÁI của MỌI con, nên lần xuất hiện CUỐI CÙNG của
# một id chính là trạng thái hiện hành.
# W140 09/10/2026 — DẤU «NHẮN TIẾP THỢ CŨ». `SendMessage` vào một thợ đã xong thì harness
# chạy lại đúng agent đó và ghi vào transcript cha một tool_result
# `{"success":true,"message":"Resuming agent …","resumedAgentId":"<id>"}` (đo 05/10/2026:
# 15 lần trong phiên chính, 4 lần ở phiên khác). Bản cũ coi «kết thúc là một chiều» nên thợ
# sống lại vẫn bị tính là chết -> không đếm vào trần 5 + vùng tệp của nó coi như TRỐNG
# (`worker_queue.vung_dang_giu` đọc chung `running_workers`) -> thợ khác được thả vào đúng
# chỗ đó. Bắt cả dạng chữ thoát (`\"resumedAgentId\":\"…`) lẫn dạng JSON thường.
RX_HOI = re.compile(r'resumedAgentId\\?"\s*:\s*\\?"([0-9A-Za-z_-]+)')
RX_DS = re.compile(r"\b([0-9a-f]{15,20})\b\s*\u00b7\s*[\w.-]+\s*\u00b7\s*"
                   r"(running|completed|killed|failed|error|errored|cancelled|canceled|timeout|timed_out)\b")

RX_COMMIT = re.compile(r"\[[\w./+-]{1,40}\s+([0-9a-f]{7,40})\]")
RX_STASH = re.compile(r"stash@\{\d+\}")
# W133 (05/09/2026): sổ bàn giao từng cắt `x[:1200]` từ ĐẦU câu — đúng lúc `ĐỂ LẠI:` /
# `CHỜ VÙNG:` / `PID đã dựng` luôn nằm ở ĐUÔI báo cáo cuối (quy ước "Báo cáo cuối" của
# spine) nên bị cắt mất 100%. RX_CHOT vét các dòng này ra riêng, KHÔNG bị ảnh hưởng bởi
# giới hạn độ dài của phần thân.
RX_CHOT = re.compile(
    r"^\s*(?:ĐỂ LẠI|CHỜ VÙNG|PID đã dựng[^:\n]*)\s*:.*$", re.MULTILINE)


def _du_an(cwd):
    # WHY dùng `re.sub` chứ không phải `replace("/", "-")`: Claude Code đặt tên thư mục
    # transcript bằng cách thay MỌI ký tự không phải chữ/số thành gạch nối, không riêng
    # dấu `/`. Dự án có dấu chấm trong tên (`chiemtinh.jst4.fun`) thì quy tắc cũ dựng ra
    # `...-chiemtinh.jst4.fun` — thư mục KHÔNG tồn tại — rồi vòng lặp leo lên cha
    # `-Users-buddhy-PycharmProjects` (thư mục của dự án KHÁC) => không thấy agent nào,
    # bảng in "❓ mất dấu agent" cho mọi worker và statusLine in RỖNG (ca 09/09/2026).
    p = os.path.abspath(cwd or os.getcwd())
    while True:
        c = os.path.join(PROJECTS_ROOT, re.sub(r"[^A-Za-z0-9]", "-", p))
        if os.path.isdir(c):
            return c
        cha = os.path.dirname(p)
        if cha == p:
            return None
        p = cha


def _scope(cwd):
    return os.path.basename(os.path.abspath(cwd or os.getcwd()).rstrip("/"))


CACHE_DIR = os.path.expanduser("~/.claude/worker-cache")


def _cache_p(cha_jsonl):
    import hashlib
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, hashlib.sha1(
        cha_jsonl.encode("utf-8")).hexdigest()[:16] + ".json")


def ids_ket_thuc(cha_jsonl):
    """{agent_id: status} mà HARNESS đã báo kết thúc — ĐỌC ĐỦ CẢ TỆP, có nhớ đệm tăng dần.

    ⚠ ĐÂY LÀ CHỖ ĐÃ LÀM SẬP CƠ CHẾ (đo được 27/8): bản cũ trong `worker_board.py` chỉ đọc
    4 MB CUỐI transcript cha (`CHA_DOC_TOI_DA`), `worker_cap_enforce` cũng vậy. Worker HGT
    bị `TaskStop` lúc 10:40; hai tiếng sau khối `<task-notification><status>killed` của nó
    đã trôi ra ngoài 4 MB cuối -> mọi thứ tưởng nó CÒN SỐNG -> bảng vẽ "❓ không tìm thấy
    agent" suốt 2 tiếng và không cơ chế nào dựng lại vé. Đọc thiếu = mù, không phải an toàn.

    Nên: đọc TỪ ĐẦU một lần rồi nhớ `offset`; lượt sau chỉ đọc phần MỚI (lùi 8 KB phòng
    khối bị cắt ngang). Phiên 12 MB đọc lần đầu ~0,2 s, các lượt sau gần như 0.
    """
    p = _cache_p(cha_jsonl)
    try:
        kc = os.path.getsize(cha_jsonl)
    except OSError:
        return None
    try:
        c = json.load(open(p, encoding="utf-8"))
    except Exception:
        c = {"off": 0, "ids": {}}
    off = int(c.get("off") or 0)
    ids = dict(c.get("ids") or {})
    hoi = set(c.get("hoi") or [])          # W140: id đã được nhắn tiếp (sống lại)
    if off > kc:
        off, ids, hoi = 0, {}, set()      # tệp bị cắt/thay -> đọc lại từ đầu
    if off >= kc and ids is not None and off > 0:
        return ids
    try:
        with open(cha_jsonl, encoding="utf-8", errors="replace") as fh:
            fh.seek(max(0, off - 8192))
            noi = fh.read()
    except OSError:
        return None
    # W140: gom MỌI sự kiện rồi xử theo VỊ TRÍ trong tệp — «sống lại» chỉ có nghĩa khi so
    # thứ tự với «kết thúc». Ba loại: thông báo kết thúc (tn) · bảng danh sách (ds) · nhắn
    # tiếp (hoi). Thợ đã sống lại thì CHỈ thông báo kết thúc MỚI (tn) mới chấm chết lại; bảng
    # danh sách có thể là ảnh chụp CŨ lặp lại do prompt cache (xem chú thích dưới) nên không
    # đủ tin để giết một thợ vừa được nhắn tiếp. Thợ sống lại mà bị TaskStop không có thông
    # báo thì lưới `SONG_TOI_DA` + phiên cha chết của `running_workers` vẫn thu.
    su_kien = []
    for m in RX_TASK_ID.finditer(noi):
        s = RX_STATUS.search(noi, m.end(), m.end() + 400)
        if s and s.group(1).lower() in KET_THUC:
            su_kien.append((m.start(), "tn", m.group(1), s.group(1).lower()))
    # Bảng danh sách subagent — đọc theo THỨ TỰ TỆP nên lần xuất hiện cuối thắng.
    for m in RX_DS.finditer(noi):
        aid, tt = m.group(1), m.group(2).lower()
        if tt in KET_THUC:
            su_kien.append((m.start(), "ds", aid, tt))
    for m in RX_HOI.finditer(noi):
        su_kien.append((m.start(), "hoi", m.group(1), ""))
    su_kien.sort(key=lambda x: x[0])
    for _vt, loai, aid, tt in su_kien:
        if loai == "hoi":
            hoi.add(aid)
            ids.pop(aid, None)
        elif loai == "tn":
            ids[aid] = tt
            hoi.discard(aid)
        elif aid not in hoi:
            ids[aid] = tt
        # KHÔNG bao giờ gỡ kết luận vì thấy `running`: khối danh sách này bị lặp lại
        # NGUYÊN VĂN ở các bản ghi sau (prompt cache) nên một ảnh chụp CŨ vẫn nằm phía
        # dưới trong tệp. Đo 27/8: gỡ theo `running` làm 6 worker ĐÃ completed bị coi là
        # còn sống. Trạng thái kết thúc là MỘT CHIỀU — đã chết thì không sống lại.
    try:
        cu = os.path.getmtime(p) if os.path.exists(p) else 0
        if time.time() - cu > 3:      # bảng chạy rất dày -> không ghi đĩa mỗi lượt
            tmp = p + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump({"off": kc, "ids": ids, "hoi": sorted(hoi)}, fh)
            os.replace(tmp, p)
    except Exception:
        pass
    return ids


def _duoi_ban_ghi(jl):
    try:
        kc = os.path.getsize(jl)
        with open(jl, "rb") as fh:
            fh.seek(max(0, kc - DUOI_DOC))
            raw = fh.read()
    except OSError:
        return []
    dong = raw.split(b"\n")
    if kc > DUOI_DOC:
        dong = dong[1:]
    ra = []
    for d in dong:
        d = d.strip()
        if not d:
            continue
        try:
            ra.append(json.loads(d))
        except Exception:
            pass
    return ra


# `stop_reason` harness đóng dấu khi model KẾT LƯỢT — giữ Y HỆT `worker_cap_enforce`.
KET_LUOT = {"end_turn", "stop_sequence"}

# Dòng LỖI HẠ TẦNG harness ghi vào chỗ của một khối `text` bình thường, KÈM `stop_reason`
# kết lượt. Đây KHÔNG phải báo cáo cuối — worker chết giữa chừng vì mạng, phải đẻ vé.
# Đo thật (29/08/2026, 4 worker chết lúc mạng chập): W01/W03/W04/W05 đều kết thúc bằng
# `stop_sequence` + đúng một dòng 78-79 ký tự "API Error: Can't reach the API server…".
RX_LOI_HA_TANG = re.compile(
    r"^\s*(?:API Error\b|Can't reach the API server|The response stopped arriving"
    r"|Request timed out|Connection error|fetch failed)", re.I)


def da_tra_bao_cao(jl):
    """True = worker ĐÃ trả báo cáo cuối. CHỈ gọi SAU khi harness đã báo agent kết thúc.

    Cả hai chỗ gọi (`quet` ở tệp này và `worker_de_lai.quet`) đều đã lọc `aid in xong`
    trước — nên ở đây transcript là BẢN CUỐI, không còn khe "vừa nói vừa làm" của
    `worker_cap_enforce.da_tra_bao_cao` (bên đó soi agent CÒN SỐNG nên phải chặt hơn;
    cố ý để hai hàm khác nhau, đừng gộp).

    SỬA 29/08/2026 — CA W08 (`a54d3d62e3d9d37cb`): worker phản biện phiếu P071 đã trả báo
    cáo cuối 4.963 ký tự và commit `5110640`, harness báo `completed`, NHƯNG bản ghi cuối
    có `stop_reason: null` (harness không phải lúc nào cũng đóng dấu) -> luật cũ phán
    "chưa trả báo cáo" -> đẻ vé `0762ff1cf9` bắt chạy lại việc đã xong. Đo trên 41 worker
    kết thúc trong 12 giờ: **26 con `completed` có báo cáo cuối thật mà `stop_reason` rỗng**
    -> luật cũ sai 26 ca. Phần trăm trong tệp `.progress` là worker TỰ KHAI, KHÔNG được
    dùng làm căn cứ ngược lại tín hiệu `completed` của harness.

    LUẬT (đọc ngược từ bản ghi thật cuối cùng):
      · `user` (không phải isMeta)      -> `[Request interrupted]` / cha gửi việc mới -> False
      · assistant có khối `tool_use`    -> chết ngay lúc đang gọi lệnh                -> False
      · assistant chỉ có `thinking`/rỗng -> xét tiếp bản ghi trước
      · assistant có `text` là dòng lỗi hạ tầng -> chết vì mạng                        -> False
      · assistant có `text` thật        -> ĐÃ TRẢ BÁO CÁO CUỐI                        -> True
    """
    try:
        for r in reversed(_duoi_ban_ghi(jl)):
            if r.get("type") == "attachment":
                continue
            if r.get("type") == "user" and r.get("isMeta"):
                continue
            if r.get("type") == "user":
                return False          # bị ngắt / cha gửi việc mới -> chưa có báo cáo cuối
            if r.get("type") != "assistant":
                continue
            msg = r.get("message") or {}
            noi = msg.get("content")
            khoi = [b for b in noi if isinstance(b, dict)] if isinstance(noi, list) else []
            if any(b.get("type") == "tool_use" for b in khoi):
                return False          # đang gọi lệnh thì đứt -> việc còn dở
            if isinstance(noi, str):
                chu = noi
            else:
                chu = "\n".join(str(b.get("text") or "") for b in khoi
                                 if b.get("type") == "text")
            if not chu.strip():
                continue              # bản ghi `thinking` / rỗng -> nhìn lùi tiếp
            if RX_LOI_HA_TANG.search(chu.strip()[:200]):
                return False          # dòng lỗi hạ tầng KHÔNG phải báo cáo cuối
            return True
        return False
    except Exception:
        return False


def _brief_tu_cha(goc, aid, tool_use_id, cha_agent=""):
    """Brief NGUYÊN VĂN của worker: quét MỌI transcript phiên trong dự án, mới trước.

    `.meta.json` của subagent CHỈ có agentType/description/toolUseId (đã kiểm) — KHÔNG có
    `prompt`. Không lấy được prompt thì vé vô dụng (thả lại phải gõ tay cả brief).

    WHY quét mọi phiên chứ không chỉ phiên chứa thư mục `subagents/`: đo 27/8, worker
    `a56af5d9dca91d057` nằm trong `subagents/` của phiên `e4d8e154…` nhưng lệnh thả nó
    lại được ghi ở phiên `fdff2828…` (phiên bị resume/đổi id). Bám đúng một tệp cha là
    trượt prompt -> vé rỗng.

    Hai nguồn, lấy nguồn nào có trước:
      1. khối `tool_use` Agent/Task khớp `toolUseId` (input đủ description/prompt/model);
      2. `toolUseResult` của chính lệnh đó: `{"agentId": "<aid>", "prompt": "…"}`.
    """
    # THỨ TỰ TÌM (đo 27/8): worker có thể do MỘT WORKER KHÁC thả ra —
    # `agent-a56af5d9dca91d057.meta.json` ghi `parentAgentId: a95191bd3b2b71da0`,
    # `spawnDepth: 2`. Lệnh thả nó nằm trong transcript của CON MẸ, không nằm ở phiên nào
    # cả -> chỉ quét `*.jsonl` gốc là mãi mãi không thấy prompt, vé đẻ ra rỗng ruột.
    tep = []
    if cha_agent:
        tep += glob.glob(os.path.join(goc, "*", "subagents", "agent-%s.jsonl" % cha_agent))
    tep += sorted(glob.glob(os.path.join(goc, "*.jsonl")),
                  key=lambda f: os.path.getmtime(f), reverse=True)
    tep += sorted(glob.glob(os.path.join(goc, "*", "subagents", "agent-*.jsonl")),
                  key=lambda f: os.path.getmtime(f), reverse=True)[:60]
    moc_id = '"agentId":"%s"' % aid
    # W08 17/10/2026 — ĐỌC BYTE + DÒ VỊ TRÍ, chỉ giải mã đúng dòng chứa mã. Bản cũ giải mã
    # cả tệp rồi `splitlines()` + `replace(" ", "")` từng dòng: phiên cha 192 MB (47212242)
    # làm một lượt quét mất 11,7 giây (đo 09:3x 17/10, `cProfile`: 19,5/21,4 giây nằm ở
    # đây) > trần 5–8 giây của hook -> hook bị giết giữa chừng, sổ `.da-xet` không kịp ghi,
    # lượt sau lại quét lại từ đầu.
    khoa = [k.encode("utf-8") for k in (tool_use_id, aid) if k]
    for f in tep:
        try:
            with open(f, "rb") as fh:
                noi = fh.read()
        except OSError:
            continue
        dau = set()
        for k in khoa:
            vt = noi.find(k)
            while vt != -1:
                dau.add(noi.rfind(b"\n", 0, vt) + 1)
                vt = noi.find(k, vt + 1)
        for d0 in sorted(dau):
            c0 = noi.find(b"\n", d0)
            ln = noi[d0:c0 if c0 != -1 else len(noi)].decode("utf-8", errors="replace")
            if tool_use_id and tool_use_id in ln:
                try:
                    r = json.loads(ln)
                except Exception:
                    continue
                noi_dung = (r.get("message") or {}).get("content")
                if isinstance(noi_dung, list):
                    for b in noi_dung:
                        if isinstance(b, dict) and b.get("type") == "tool_use" \
                                and b.get("id") == tool_use_id \
                                and b.get("name") in ("Agent", "Task") \
                                and (b.get("input") or {}).get("prompt"):
                            return b["input"]
            if moc_id in ln.replace(" ", ""):
                try:
                    r = json.loads(ln)
                except Exception:
                    continue
                kq = r.get("toolUseResult")
                if isinstance(kq, dict) and kq.get("agentId") == aid and kq.get("prompt"):
                    return {"description": kq.get("description") or "",
                            "prompt": kq.get("prompt"),
                            "subagent_type": kq.get("subagentType") or "",
                            "model": kq.get("model") or ""}
    return None


def _tien_do(scope, slug):
    """(mốc, nhãn) từ tệp .progress đang sống, hoặc bản đã dọn vào done/. (None,'') nếu không có.

    W37 09/09/2026: lấy MỐC LỚN NHẤT trong toàn bộ tệp (`worker_state.moc_lon_nhat`),
    không phải dòng đầu (`.readline()`) — tệp ghi NỐI nhiều dòng đọc dòng đầu ra % thấp
    -> `quet()` tưởng worker dừng giữa chừng, dựng lại vé cho việc đã xong (cùng họ bug
    với ca S12 W36, xem `docs/bang-chung/S12-so-khong-biet-da-bam-tat-09092026.md`).
    """
    if not slug:
        return None, ""
    d = os.path.join(PROGRESS_ROOT, scope)
    ung = [os.path.join(d, slug + ".progress")]
    ung += sorted(glob.glob(os.path.join(d, "done", "*__%s__*.progress" % slug)),
                  key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0, reverse=True)
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import worker_state as _WSTATE
    except Exception:
        _WSTATE = None
    for f in ung:
        try:
            noi = open(f, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if _WSTATE is not None:
            nn, nhan = _WSTATE.moc_lon_nhat(noi)
            if nn is not None:
                return nn, nhan[:60]
        # lùi về dòng đầu nếu module chủ lỗi hoặc không dòng nào hợp khuôn
        nn_s, _, nhan_s = noi.splitlines()[0].partition("|") if noi.splitlines() else ("", "", "")
        try:
            return int(nn_s.strip()), nhan_s.strip()[:60]
        except Exception:
            continue
    return None, ""


RX_MOC = re.compile(r"echo\s+['\"](\d{1,3})\|([^'\"\n]{1,80})['\"]\s*>[^|\n]{0,120}\.progress")


def _moc_tu_transcript(jl):
    """(mốc, nhãn) lấy từ CHÍNH lệnh `echo 'NN|nhãn' > *.progress` cuối cùng trong transcript.

    WHY cần lưới này: tệp .progress có thể đã bị dọn vào done/ hoặc bị xoá tay (ca W114
    sáng 27/8 — điều phối xoá tệp cho hết dòng ma, thế là mất luôn dấu vết "dừng ở đâu").
    Transcript agent thì không ai xoá, và lệnh worker tự gõ là bằng chứng tất định.
    """
    try:
        kc = os.path.getsize(jl)
        with open(jl, encoding="utf-8", errors="replace") as fh:
            if kc > DAU_VET_DOC:
                fh.seek(kc - DAU_VET_DOC)
            noi = fh.read()
    except OSError:
        return None, ""
    m = None
    for m in RX_MOC.finditer(noi):
        pass
    if not m:
        return None, ""
    try:
        return int(m.group(1)), m.group(2).strip()[:60]
    except Exception:
        return None, ""


def _dau_vet(jl):
    """Dấu vết công sức worker để lại: sha commit + có stash hay không. Rỗng nếu không dò được."""
    try:
        kc = os.path.getsize(jl)
        with open(jl, encoding="utf-8", errors="replace") as fh:
            if kc > DAU_VET_DOC:
                fh.seek(kc - DAU_VET_DOC)
            noi = fh.read()
    except OSError:
        return ""
    sha, thay = [], set()
    for m in RX_COMMIT.finditer(noi):
        s = m.group(1)
        if s not in thay:
            thay.add(s)
            sha.append(s)
    ra = []
    if sha:
        ra.append("commit " + ", ".join(sha[-3:]))
    if RX_STASH.search(noi) or "git stash push" in noi:
        ra.append("có git stash")
    return " · ".join(ra)


def _cat_giua(t, cap=2400):
    """Cắt văn bản dài quá `cap` ký tự, GIỮ ĐẦU + ĐUÔI, cắt PHẦN GIỮA (W133).

    Trước sửa: `x[:1200]` cắt từ đầu -> mất toàn bộ đuôi, đúng chỗ quy ước "Báo cáo
    cuối" của spine luôn đặt `ĐỂ LẠI:`/`CHỜ VÙNG:`/`PID đã dựng`. Đo thật trên ca W128
    (agent a4c09698ad9bfd10e): báo cáo cuối dài 5753 ký tự, 3 dòng đó nằm ở vị trí
    5518/5554/5734 — đều SAU mốc cắt 1200 -> mất 100%.
    """
    if len(t) <= cap:
        return t
    dau = cap * 2 // 3
    duoi = cap - dau
    bi_cat = len(t) - dau - duoi
    return t[:dau] + ("\n\n… (đã cắt %d ký tự ở giữa, xem transcript nếu cần đủ) …\n\n" % bi_cat) + t[-duoi:]


def so_ban_giao(jl, cwd, aid):
    """Ghi SỔ BÀN GIAO cho worker bị dừng — trả về đường dẫn, "" nếu không ghi được.

    VÌ SAO CÓ (founder 29/08/2026: *"làm sao để cho vào hàng chờ mà vẫn lưu được công đã
    làm nhỉ"*): vé cũ chỉ lưu LỆNH GIAO VIỆC nên thả lại là worker làm từ số 0.

    ĐO THẬT trước khi làm (7 vé "bị dừng giữa chừng" của dự án này, 6 worker):
      · 2/6 ĐÃ commit (W08 `1c2ca85` · W35 `20c68cf`) -> công nằm trên đĩa, KHÔNG mất.
      · 4/6 chưa commit — mà 3 trong 4 là worker ĐI SOI (W180 "tìm nguồn sinh XML" ·
        W181 "soi base-ui nested dialog" · W182 "soi matching IDEA-SKU"): chúng KHÔNG ghi
        tệp nào để mà commit. Thứ mất là KẾT LUẬN ĐÃ SOI RA — git không giữ hộ được.
    -> Nên "bắt worker commit từng phần rồi vé ghi sha" KHÔNG chữa được ca hay gặp nhất.

    CÁCH RẺ NHẤT: KHÔNG bắt worker ghi thêm dòng nào (mỗi dòng ghi là token thật). Sổ này
    THU HOẠCH từ transcript vốn đã có — tệp đã ghi · commit · và LỜI CUỐI của chính worker
    (chỗ nó nói ra kết luận + đang dở tới đâu). Cố ý KHÔNG chép `git log`/`git diff`:
    worker sau tự chạy được, chép lại chỉ tốn token.
    """
    try:
        import worker_queue as WQ
        thu_muc = WQ.thu_muc(cwd)
        os.makedirs(thu_muc, exist_ok=True)
    except Exception:
        return ""
    tep, sha, loi = [], [], []
    try:
        kc = os.path.getsize(jl)
        with open(jl, encoding="utf-8", errors="replace") as fh:
            if kc > DAU_VET_DOC:
                fh.seek(kc - DAU_VET_DOC)
                fh.readline()
            for d in fh:
                try:
                    b = json.loads(d)
                except Exception:
                    continue
                c = (b.get("message") or {}).get("content")
                if not isinstance(c, list):
                    continue
                for k in c:
                    if not isinstance(k, dict):
                        continue
                    if k.get("type") == "tool_use":
                        fp = str((k.get("input") or {}).get("file_path") or "")
                        if fp and fp not in tep:
                            tep.append(fp)
                    elif k.get("type") == "text" and b.get("type") == "assistant":
                        t = str(k.get("text") or "").strip()
                        if len(t) >= 40:
                            loi.append(t)
                    elif k.get("type") == "tool_result":
                        ct = k.get("content")
                        if isinstance(ct, list):
                            ct = " ".join(x.get("text", "") for x in ct if isinstance(x, dict))
                        for m in RX_COMMIT.finditer(str(ct)):
                            if m.group(1) not in sha:
                                sha.append(m.group(1))
    except OSError:
        return ""
    if not (tep or sha or loi):
        return ""
    ra = ["# Sổ bàn giao — worker %s (bị dừng giữa chừng)" % aid,
          "Đọc sổ này TRƯỚC khi làm lại. `git log` / `git status` / `git diff` tự chạy được, "
          "sổ chỉ ghi thứ KHÔNG tra ra được."]
    if sha:
        ra.append("## Commit đã tạo\n" + "\n".join("- `%s`" % x for x in sha[-5:]))
    if tep:
        ra.append("## Tệp đã ghi (%d)\n" % len(tep)
                  + "\n".join("- %s" % x for x in tep[-20:]))
    if loi:
        # Vét ĐỂ LẠI:/CHỜ VÙNG:/PID đã dựng ra section RIÊNG, không chung số phận với
        # phần cắt-độ-dài bên dưới — quét vài lời cuối cho chắc (dedup theo thứ tự xuất
        # hiện, ưu tiên lời gần cuối nhất vì đó là bản chốt sau cùng).
        chot, thay = [], set()
        for x in loi[-3:]:
            for m in RX_CHOT.finditer(x):
                dong = m.group(0).strip()
                if dong not in thay:
                    thay.add(dong)
                    chot.append(dong)
        if chot:
            ra.append("## Chốt lại (vét riêng, KHÔNG bị cắt)\n"
                      + "\n".join("- " + d for d in chot))
        ra.append("## Lời cuối của chính worker — kết luận + chỗ đang dở\n"
                  + "\n\n".join("> " + _cat_giua(x).replace("\n", "\n> ") for x in loi[-2:]))
    p = os.path.join(thu_muc, "ban-giao-%s.md" % aid)
    try:
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("\n\n".join(ra) + "\n")
    except Exception:
        return ""
    return p


def _so_xet(cwd):
    import worker_queue as WQ
    return os.path.join(WQ.thu_muc(cwd), ".da-xet.json")


def _doc_so(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return {}


def _ghi_so(p, d):
    try:
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(d, fh)
        os.replace(tmp, p)
    except Exception:
        pass


# P138 11/10/2026 — VÉ THẢ LẠI PHẢI MANG DÒNG `CHỜ VÙNG` CỦA THỢ TRƯỚC.
# Ca thật: thợ P137 khai `CHỜ VÙNG: src/lib/notifications src/lib/mebox …` (TR dòng 1392) rồi
# dừng ở 35%; máy hồi sinh vé `9e5d43d6e9` chép NGUYÊN brief cũ, `vung: ""` -> thả lại là kẹt y
# nguyên. Quét NGƯỢC nhiều lượt chứ không chỉ lượt cuối: lượt cuối của thợ đó (TR dòng 1418,
# 286 ký tự «…tôi kết thúc lượt ở đây») không còn dòng `CHỜ VÙNG` —
# `worker_de_lai.bao_cao_cuoi` (chỉ lượt cuối) ra rỗng, đo 11/10.
RX_CHO_VUNG = re.compile(r"^[\s>*#·\-]*(?:CHỜ VÙNG|CHO VUNG|Chờ vùng)\s*:\s*(.+)$", re.M)
RX_CHO_VUNG_RONG = re.compile(r"^(?:kh[ôo]ng(?:\s+c[óo])?|none|-|—|n/?a)\b", re.I)


def cho_vung_cuoi(jl):
    """Dòng `CHỜ VÙNG:` gần nhất (khác «không») trong các lượt assistant ở đuôi transcript."""
    for r in reversed(_duoi_ban_ghi(jl)):
        if r.get("type") != "assistant":
            continue
        c = (r.get("message") or {}).get("content")
        van = ""
        if isinstance(c, list):
            van = "\n".join(str(b.get("text") or "") for b in c
                            if isinstance(b, dict) and b.get("type") == "text")
        elif isinstance(c, str):
            van = c
        for m in reversed(list(RX_CHO_VUNG.finditer(van))):
            v = m.group(1).strip().strip("`").strip()
            if v and not RX_CHO_VUNG_RONG.match(v):
                return v
    return ""


def khoi_cho_vung(so, nn, cho_vung):
    return ("⚠ THỢ TRƯỚC (%s) DỪNG Ở %s VÌ KẸT VÙNG: %s\n"
            "Dòng `GHI:` bên dưới là của brief CŨ — SỬA cho đủ theo phiếu (gộp thêm các vùng "
            "trên) TRƯỚC khi thả; cổng GHI-khớp-phiếu (P138) sẽ chặn nếu chưa đủ.\n\n"
            % (so or "W??", ("%d%%" % nn) if nn is not None else "mốc không rõ", cho_vung))


def ket_luan(jl, scope):
    """«xong» | «dung» cho agent ĐÃ kết thúc — CÙNG luật với `quet()` (mốc nói trước, lời khai sau).

    W08 17/10/2026: `worker_board.dong_bo_trang_thai` từng ghi `done` cho MỌI dòng sổ số mất
    bóng trên bảng, kể cả thợ chết ở 50% -> `wseq list` in «xong» cho việc đang dở. Nay bảng
    hỏi hàm này trước khi đóng sổ; một luật, hai chỗ dùng, không đo lần hai.
    """
    try:
        import worker_board as WB
        meta = json.load(open(jl[:-len(".jsonl")] + ".meta.json", encoding="utf-8"))
        mo_ta = str(meta.get("description") or "")
        slug_td = WB.slug_td_cua_agent(jl)
    except Exception:
        mo_ta, slug_td = "", ""
    try:
        import worker_board as WB
        nn, _ = _tien_do(scope, slug_td or WB.slug_hoa(mo_ta))
    except Exception:
        nn = None
    if nn is None:
        nn, _ = _moc_tu_transcript(jl)
    if nn is not None:
        return "xong" if nn >= 100 else "dung"
    return "xong" if da_tra_bao_cao(jl) else "dung"


def quet(cwd, dry=False):
    """Quét worker chết giữa chừng -> tạo vé. Trả về [(số vé, tên việc, mốc, lý do)]."""
    try:
        import worker_queue as WQ
        import worker_board as WB
    except Exception:
        return []
    goc = _du_an(cwd)
    if not goc:
        return []
    scope = _scope(cwd)
    bay_gio = time.time()
    so_p = _so_xet(cwd)
    so = _doc_so(so_p)
    moi = []
    # slug của worker CÒN SỐNG: việc đã được thả lại rồi thì tuyệt đối không đẻ vé thứ hai.
    song_slug = set()
    try:
        for a in WB.quet_agent(cwd, bay_gio)[0]:
            song_slug.add(a.get("slug") or "")
            song_slug.add(a.get("slug_td") or "")
    except Exception:
        pass
    song_slug.discard("")

    # W08 17/10/2026 (Task-17102026-03) — PHIÊN CHA CHẾT THÌ THỢ CHẾT THEO, KHÔNG CHỜ HARNESS.
    # Máy đơ/tắt cứng giết cả tiến trình phiên -> harness KHÔNG BAO GIỜ kịp ghi khối
    # `<task-notification>` kết thúc vào transcript cha. Bản cũ chỉ tin nguồn đó
    # (`if aid not in xong: continue`) nên thợ chết theo máy bị coi là "còn sống" mãi mãi:
    # ca thật sáng 17/10 — W01 (portfolio, 50%) và W03 (6 ca E2E, 30%) của phiên 47212242
    # chết lúc máy quá tải, 0 vé, 0 sổ bàn giao, việc rơi mất. Dùng CÙNG thước sống/chết với
    # bảng (`worker_board.ket_thuc_cua` -> `worker_cap_enforce.phien_con_song`): agent chỉ
    # chết theo phiên khi KHÔNG phiên nào chứa nó (kể cả symlink của phiên nối tiếp) còn sống.
    try:
        import worker_cap_enforce as _WCE
        _song_ids = _WCE.phien_con_song()
    except Exception:
        _song_ids = None
    _tep_cua = {}       # aid -> [tệp thật, *symlink] cho `cha_con_giu` (W35 28/10)
    if _song_ids is not None:
        for _jl in sorted(glob.glob(os.path.join(goc, "*", "subagents", "agent-*.jsonl"))):
            _a = os.path.basename(_jl)[len("agent-"):-len(".jsonl")]
            _ds = _tep_cua.setdefault(_a, [])
            (_ds.insert(0, _jl) if not os.path.islink(_jl) else _ds.append(_jl))

    cache_cha = {}
    for jl in glob.glob(os.path.join(goc, "*", "subagents", "agent-*.jsonl")):
        try:
            mt = os.path.getmtime(jl)
        except OSError:
            continue
        if (bay_gio - mt) > CUA_SO_GIO * 3600:
            continue
        aid = os.path.basename(jl)[len("agent-"):-len(".jsonl")]
        if so.get(aid) == int(mt):
            continue                       # đã xét đúng bản này rồi
        phien = os.path.dirname(os.path.dirname(jl)) + ".jsonl"
        if phien not in cache_cha:
            cache_cha[phien] = ids_ket_thuc(phien)
        xong = cache_cha[phien]
        # W35 28/10: tính cả phiên cha mở lại cùng mã — tiến trình cũ chết, thợ chết theo.
        chet_theo_phien = (_song_ids is not None and bool(_tep_cua.get(aid))
                           and _WCE.cha_con_giu(_tep_cua[aid]) is False)
        if chet_theo_phien and (xong is None or aid not in xong):
            xong = dict(xong or {}, **{aid: "phiên cha đã chết — máy tắt/đơ"})
        if xong is None:
            continue                       # mất nguồn tất định -> không dám phán
        if aid not in xong:
            continue                       # harness chưa báo kết thúc, phiên cha còn sống
        # từ đây: agent ĐÃ kết thúc. Xét xem xong việc hay bị dừng giữa chừng.
        if not dry:
            so[aid] = int(mt)
        meta = {}
        try:
            meta = json.load(open(jl[:-len(".jsonl")] + ".meta.json", encoding="utf-8"))
        except Exception:
            pass
        mo_ta = str(meta.get("description") or "")
        slug_td = ""
        try:
            slug_td = WB.slug_td_cua_agent(jl)
        except Exception:
            pass
        slug = slug_td or WB.slug_hoa(mo_ta)
        if slug in song_slug or WB.slug_hoa(mo_ta) in song_slug:
            continue                       # đã có worker khác đang làm lại việc này
        nn, nhan = _tien_do(scope, slug_td or WB.slug_hoa(mo_ta))
        if nn is None:
            nn, nhan = _moc_tu_transcript(jl)
        if nn is not None and nn >= 100:
            continue                       # đã 100% -> xong, không vé
        # ĐẢO THỨ TỰ (29/08/2026, W187 — theo phát hiện của W173):
        # trước đây `da_tra_bao_cao(jl)` được xét TRƯỚC phép so mốc, nên worker khai
        # "xong" ở 92% là thoát ngay, không bao giờ tới được dòng so mốc -> không đẻ vé,
        # không ai làm nốt. Ca thật: W144 dừng 92% («Smoke demo + prod, chụp ảnh») khai
        # "xong, ĐỂ LẠI: không có" -> 4 màn giao diện vỡ lọt tới tay founder.
        # Nay: MỐC nói trước. Chỉ khi mốc >= 100 (dòng trên) hoặc KHÔNG có mốc nào để đo
        # thì mới tin lời khai. Lời khai không phải bằng chứng — mốc mới là.
        if nn is None and da_tra_bao_cao(jl):
            continue                       # không đo được mốc -> đành tin báo cáo cuối
        brief = _brief_tu_cha(goc, aid, meta.get("toolUseId"),
                              meta.get("parentAgentId") or "") or {}
        ti = {"description": brief.get("description") or mo_ta,
              "prompt": brief.get("prompt") or "",
              "subagent_type": brief.get("subagent_type") or meta.get("agentType") or "",
              "model": brief.get("model") or "",
              "isolation": brief.get("isolation") or ""}
        if not ti["description"]:
            continue
        ly = "bị dừng giữa chừng (%s)" % xong.get(aid, "kết thúc")
        them = {"bi_dung": True, "moc": nn, "nhan_cuoi": nhan,
                "dau_vet": _dau_vet(jl), "agent": aid,
                "ban_giao": "" if dry else so_ban_giao(jl, cwd, aid),
                "co_prompt": bool(ti["prompt"])}
        # P138: không tự nới dòng `GHI:` (luật «brief KHAI, cổng ĐỌC KHAI»,
        # worker_cap_enforce.vung_viec_moi) — chỉ dán cảnh báo lên ĐẦU prompt + trường riêng.
        cv = cho_vung_cuoi(jl)
        if cv:
            them["cho_vung"] = cv
            m_so = re.match(r"\s*(W\d+)", mo_ta)
            if ti["prompt"] and not ti["prompt"].startswith("⚠ THỢ TRƯỚC"):
                ti["prompt"] = khoi_cho_vung(m_so.group(1) if m_so else "", nn, cv) + ti["prompt"]
            ly += " — kẹt vùng: %s" % cv[:120]
        if dry:
            moi.append(("(dry)", ti["description"][:50], nn, ly, bool(ti["prompt"])))
            continue
        if not WQ.them(cwd, ti, ly, them_truong=them):
            continue        # đã có agent SỐNG làm chính việc này -> không đẻ vé (xem
                            # worker_queue.them §chiều ngược của đối soát)
        v = WQ.tim(cwd, ti) or {}
        moi.append((v.get("so") or "W??", WQ.ten_ve(v), nn, ly, bool(ti["prompt"])))
    if not dry:
        # gọn sổ: bỏ agent đã ra khỏi cửa sổ quét
        con = {}
        for jl in glob.glob(os.path.join(goc, "*", "subagents", "agent-*.jsonl")):
            a = os.path.basename(jl)[len("agent-"):-len(".jsonl")]
            if a in so:
                con[a] = so[a]
        _ghi_so(so_p, con)
    return moi


def _tu_kiem():
    """`worker_relapse.py --tu-kiem` — 9 ca THẬT lấy từ transcript 28-29/08/2026.

    Ca gốc: W08 (`a54d3d62e3d9d37cb`) trả báo cáo 4.963 ký tự + commit, harness `completed`,
    `.progress` dừng 95% -> luật cũ vẫn đẻ vé `0762ff1cf9` bắt chạy lại việc đã xong.
    """
    import tempfile

    def tep(*ban_ghi):
        fd, p = tempfile.mkstemp(suffix=".jsonl")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for b in ban_ghi:
                f.write(json.dumps(b, ensure_ascii=False) + "\n")
        return p

    def tro_ly(txt, stop=None, tool=False):
        noi = [{"type": "thinking", "thinking": "..."}]
        if tool:
            noi.append({"type": "tool_use", "id": "t1", "name": "Bash", "input": {}})
        if txt is not None:
            noi.append({"type": "text", "text": txt})
        return {"type": "assistant", "message": {"role": "assistant", "content": noi,
                                                 "stop_reason": stop}}

    BC = "Xong. Chế độ CHALLENGE — 14/14 anchor đã verify. Commit `5110640`. " * 12
    ca = [
        ("W08 completed, báo cáo dài, stop_reason RỖNG", tep(tro_ly(BC, None)), True),
        ("worker xong, harness có đóng dấu end_turn", tep(tro_ly(BC, "end_turn")), True),
        ("báo cáo NGẮN vẫn là báo cáo", tep(tro_ly("W36 kết thúc. Vé W202 giữ nguyên số.", None)), True),
        ("chết vì mạng: API Error + stop_sequence", tep(tro_ly(BC, "end_turn"),
            tro_ly("API Error: Can't reach the API server — check your internet or DNS (ENOTFOUND)",
                   "stop_sequence")), False),
        ("chết vì mạng: response stopped arriving", tep(tro_ly(
            "API Error: The response stopped arriving. The response above may be incomplete.",
            "stop_sequence")), False),
        ("bị TaskStop: [Request interrupted by user]", tep(tro_ly(BC, None),
            {"type": "user", "message": {"role": "user", "content": [
                {"type": "text", "text": "[Request interrupted by user]"}]}}), False),
        ("đứt ngay lúc đang gọi lệnh", tep(tro_ly("đang chạy tiếp", None, tool=True)), False),
        ("bản ghi cuối chỉ có thinking -> nhìn lùi tiếp", tep(tro_ly(BC, None),
            {"type": "assistant", "message": {"role": "assistant", "content": [
                {"type": "thinking", "thinking": "..."}], "stop_reason": None}}), True),
        ("nhiễu isMeta ở cuối không làm lệch kết luận", tep(tro_ly(BC, None),
            {"type": "user", "isMeta": True, "message": {"role": "user",
             "content": "SYSTEM NOTIFICATION"}}), True),
    ]
    n = 0
    for ten, p_, mong in ca:
        that = da_tra_bao_cao(p_)
        ok = that == mong
        n += ok
        print("  %s %-46s đã-trả-báo-cáo=%-5s (mong %s) -> %s"
              % ("✅" if ok else "❌", ten, that, mong,
                 "KHÔNG vé" if that else "ĐẺ VÉ"))
        os.remove(p_)
    print("worker_relapse --tu-kiem: %d/%d %s" % (n, len(ca), "PASS" if n == len(ca) else "FAIL"))
    return 0 if n == len(ca) else 1


if __name__ == "__main__":
    if "--tu-kiem" in sys.argv:
        sys.exit(_tu_kiem())
    _dry = "--dry" in sys.argv
    _cwd = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    for r in quet(_cwd, dry=_dry):
        print("VE %s | %s | mốc=%s | %s | có prompt=%s" % r)
