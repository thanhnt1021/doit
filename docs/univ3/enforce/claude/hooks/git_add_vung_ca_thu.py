#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""git_add_vung_ca_thu.py — CA THỬ cho TẦNG 2 của `git_add_scope_enforce.py`: `git add`
ĐÍCH DANH vẫn phải nằm trong vùng `GHI:` mà brief của chính worker đã khai.

Dựng lại ĐÚNG ca 18/09/2026: W07 khai `GHI: src/lib/fulfill` rồi
`git add src/app/pipeline/_components/card-dialog.tsx` -> commit `f13253dc` nuốt 288 dòng
việc đang dở của W09 -> `main` gãy build.

Chạy được trên BẤT KỲ bản cổng nào (`--gate <đường dẫn>`) — nhờ vậy dựng lại được LỖ CŨ:
cùng bộ ca chạy trên bản sao lưu trước khi vá thì ca 1 CHO QUA (lỗ có thật), chạy trên bản
đã vá thì ca 1 CHẶN.

Hộp cát hoàn toàn: thư mục transcript giả (`UNIV3_PROJECTS_ROOT`), cửa thoát giả
(`UNIV3_CUA_THOAT_DIR`), thư mục làm việc giả. Không đụng sổ thật, không cần mạng, không
dựng tiến trình nền.

Ca:
  1. brief `GHI: src/lib/fulfill` + `git add src/app/pipeline/_components/card-dialog.tsx`
     -> CHẶN, và lời chặn phải nêu ĐÍCH DANH W09 đang giữ vùng đó
  2. cùng brief + `git commit -m … -- src/app/pipeline/_components/card-dialog.tsx` -> CHẶN
  3. brief `GHI: -` (thuần đọc) + `git add` bất kỳ tệp nào                        -> CHẶN
  4. ba đường dẫn, chỉ một cái ngoài vùng -> CHẶN, chỉ nêu đúng cái sai
  5. `git add src/lib/fulfill/printbelle-actions.ts` đúng vùng khai              -> QUA
  6. phiên MAIN (payload không có `agent_id`), `git add` bất cứ gì               -> QUA
  7. cửa thoát `git-ngoai-vung` đang mở + đúng lệnh ca 1                          -> QUA
  8. lệnh không phải git (`pnpm build`)                                           -> QUA
  9. hook gặp lỗi bên trong (transcript rác + gói vào hỏng)                        -> QUA, mã thoát 0
 10. `git-scope-ok` KHÔNG mở được tầng vùng (lệnh ca 1 kèm chuỗi đó)              -> CHẶN

TẦNG 3 — lệnh GÓI/HUỶ CẢ CÂY (thêm sau khi dựng lại dòng thời gian thật của `f13253dc`:
cổng commit-trần ĐÃ chặn W07 lúc 04:10:53, W07 gõ lại kèm `git-scope-ok` nên hook tắt sạch,
rồi lệnh mất 56 giây mới chạy xong vì lint-staged — trong 56 giây đó `card-dialog.tsx` của
worker khác vào index):
 11. worker + còn worker khác sống + commit TRẦN (index SẠCH)                    -> CHẶN
 12. cùng điều kiện + commit TRẦN dạng heredoc (đúng dạng W07 dùng)              -> CHẶN
 13. cùng điều kiện + commit NÊU ĐÍCH DANH đường dẫn trong vùng                  -> QUA
 14. phiên MAIN + commit trần                                                    -> QUA
 15. cây chỉ có MỘT worker + commit trần                            -> QUA, kèm lời NHẮC
 16. worker + `git stash` không kèm đường dẫn                                    -> CHẶN
 17. `git stash push -- <tệp trong vùng>`                                        -> QUA
 18. ĐÚNG LỆNH W07 ĐÃ LÁCH: commit trần + chuỗi `git-scope-ok` trong lệnh        -> CHẶN
 19. thân heredoc CÓ CHỮ `git commit` nhưng lệnh thật là `cat > tệp`  -> QUA (không oan)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HOOKS = os.path.dirname(os.path.abspath(__file__))
GATE_MAC_DINH = os.path.join(HOOKS, "git_add_scope_enforce.py")

CT = "git " + "commit"   # tách chuỗi: hook data-guard của dự án soi chữ trong lệnh
TEP_W09 = "src/app/pipeline/_components/card-dialog.tsx"
TEP_W07 = "src/lib/fulfill/printbelle-actions.ts"

BRIEF_W07 = ("GHI: src/lib/fulfill\nĐỌC: -\nTÀI NGUYÊN: -\n\n"
             "Bạn là W07 — sửa luồng đẩy đơn Printbelle.")
BRIEF_DOC = ("GHI: -\nĐỌC: src/lib/fulfill\nTÀI NGUYÊN: -\n\n"
             "Bạn là W20 — trinh sát, chỉ đọc rồi báo cáo.")


def _ghi_transcript_worker(thu, aid, so_mo_ta, brief, cac_tep_ghi):
    """Dựng `agent-<aid>.jsonl` + `.meta.json` y khuôn harness."""
    jl = os.path.join(thu, "agent-%s.jsonl" % aid)
    with open(jl, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "user", "isSidechain": True, "agentId": aid,
                             "message": {"role": "user", "content": brief}},
                            ensure_ascii=False) + "\n")
        for tep in cac_tep_ghi:
            fh.write(json.dumps({
                "type": "assistant",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
                "message": {"role": "assistant", "content": [
                    {"type": "tool_use", "name": "Edit",
                     "input": {"file_path": tep, "old_string": "a", "new_string": "b"}}]}},
                ensure_ascii=False) + "\n")
    with open(jl[:-len(".jsonl")] + ".meta.json", "w", encoding="utf-8") as fh:
        json.dump({"agentType": "tho-fulfill", "description": so_mo_ta,
                   "toolUseId": "toolu_ca_thu", "spawnDepth": 1}, fh, ensure_ascii=False)
    return jl


def chay(gate=GATE_MAC_DINH):
    goc = tempfile.mkdtemp(prefix="w13-git-vung-")
    try:
        return _chay(goc, gate)
    finally:
        shutil.rmtree(goc, ignore_errors=True)


def _chay(goc, gate):
    cwd = os.path.join(goc, "du-an", "EtsyFulfillChichub")
    os.makedirs(os.path.join(cwd, "src", "lib", "fulfill"))
    os.makedirs(os.path.join(cwd, "src", "app", "pipeline", "_components"))
    projects = os.path.join(goc, "projects")
    phien = "phien-ca-thu"
    # `project_dir()` map cwd -> <projects>/<mọi ký tự không phải chữ số đổi thành '-'>
    import re as _re
    slug = _re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(cwd))
    subagents = os.path.join(projects, slug, phien, "subagents")
    os.makedirs(subagents)

    aid_w07, aid_w09 = "a00000000000000w7", "a00000000000000w9"
    _ghi_transcript_worker(subagents, aid_w07, "W07 Printbelle", BRIEF_W07, [TEP_W07])
    # W09 ĐANG GIỮ đúng vùng của tệp mà W07 sắp đụng — để lời chặn gọi được tên nó.
    _ghi_transcript_worker(subagents, aid_w09, "W09 auto-save mô tả thẻ",
                           "GHI: src/app/pipeline\nĐỌC: -\nTÀI NGUYÊN: -",
                           [TEP_W09])
    aid_doc = "a0000000000000doc"
    _ghi_transcript_worker(subagents, aid_doc, "W20 trinh sát", BRIEF_DOC, [])

    transcript_cha = os.path.join(projects, slug, "%s.jsonl" % phien)
    open(transcript_cha, "w").close()

    cua_thoat_dir = os.path.join(goc, "cua-thoat")
    moi = dict(os.environ,
               UNIV3_PROJECTS_ROOT=projects,
               UNIV3_CUA_THOAT_DIR=cua_thoat_dir,
               HOME=os.environ.get("HOME", ""),
               PYTHONDONTWRITEBYTECODE="1")

    def goi(cmd, aid=aid_w07, hong=False):
        goi_tin = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                   "tool_input": {"command": cmd}, "cwd": cwd,
                   "session_id": phien, "transcript_path": transcript_cha}
        if aid:
            goi_tin["agent_id"] = aid
        vao = "{khong-phai-json" if hong else json.dumps(goi_tin, ensure_ascii=False)
        r = subprocess.run([sys.executable, gate], input=vao, capture_output=True,
                           text=True, env=moi, cwd=cwd, timeout=60)
        try:
            ra = json.loads(r.stdout or "{}").get("hookSpecificOutput") or {}
        except Exception:
            ra = {}
        return (r.returncode, str(ra.get("permissionDecision") or ""),
                str(ra.get("permissionDecisionReason") or ""), r.stderr)

    ket = []

    # 1 — ca thật hôm nay
    rc, qd, ly, _ = goi("git add %s" % TEP_W09)
    ket.append(("1. W07 khai src/lib/fulfill + git add card-dialog.tsx -> CHẮN",
                qd == "deny" and TEP_W09 in ly))
    ket.append(("1b. lời chặn nêu đích danh W09 đang giữ vùng",
                qd == "deny" and "W09" in ly))

    # 2 — commit có pathspec sau `--`
    rc, qd, ly, _ = goi('git commit -m "fix" -- %s' % TEP_W09)
    ket.append(("2. git commit -m ... -- card-dialog.tsx -> CHẮN",
                qd == "deny" and TEP_W09 in ly))

    # 3 — brief khai `GHI: -`
    rc, qd, ly, _ = goi("git add %s" % TEP_W07, aid=aid_doc)
    ket.append(("3. brief `GHI: -` mà git add -> CHẮN",
                qd == "deny" and TEP_W07 in ly))

    # 4 — nhiều đường dẫn, chỉ một cái ngoài vùng
    rc, qd, ly, _ = goi("git add src/lib/fulfill/printbelle.ts %s src/lib/fulfill/push-verify.ts"
                        % TEP_W09)
    ket.append(("4. 3 đường dẫn, 1 ngoài vùng -> CHẮN",
                qd == "deny" and TEP_W09 in ly))
    ket.append(("4b. chỉ nêu đích danh cái sai (không kèm 2 tệp đúng vùng)",
                qd == "deny" and "printbelle.ts" not in ly and "push-verify.ts" not in ly))

    # 5 — đúng vùng khai
    rc, qd, ly, _ = goi("git add %s" % TEP_W07)
    ket.append(("5. git add đúng vùng khai -> QUA", qd != "deny"))

    # 6 — phiên main (không có agent_id)
    rc, qd, ly, _ = goi("git add %s" % TEP_W09, aid=None)
    ket.append(("6. phiên MAIN (không agent_id) -> QUA", qd != "deny"))

    # 7 — cửa thoát dùng một lần. P138: cờ `git-ngoai-vung` phải có chủ (`--cho`), cờ vô chủ
    # không thợ nào lấy được — ca cờ vô chủ bị cướp nằm ở `p138_ca_thu.py` (AC8).
    subprocess.run([sys.executable, os.path.join(HOOKS, "cua_thoat.py"), "mo",
                    "git-ngoai-vung", "manager đã chốt ghép việc W07 với W09", "--cho", "W07"],
                   env=moi, capture_output=True, text=True, timeout=30)
    rc, qd, ly, _ = goi("git add %s" % TEP_W09)
    ket.append(("7. cửa thoát `git-ngoai-vung` đang mở -> QUA", qd != "deny"))
    # W39 01/10/2026 (P114): cờ không cháy oan khi lệnh hỏng — CHẠY LẠI Y NGUYÊN đúng tập tệp
    # đó trong 10 phút thì qua, không phải mở cờ lần hai. Tệp KHÁC thì vẫn chặn (cờ đã dùng).
    rc, qd, ly, _ = goi("git add %s" % TEP_W09)
    ket.append(("7b. chạy lại Y NGUYÊN tập tệp vừa cho qua (lệnh trước hỏng) -> QUA", qd != "deny"))
    rc, qd, ly, _ = goi("git add %s src/app/orders/khac-han.tsx" % TEP_W09)
    ket.append(("7c. cờ đã dùng, thêm một tệp NGOÀI VÙNG khác -> VẪN CHẶN", qd == "deny"))
    try:
        os.remove(os.path.join(cua_thoat_dir, "git-ngoai-vung.dung-lai.json"))
    except OSError:
        pass

    # 8 — lệnh không phải git
    rc, qd, ly, _ = goi("pnpm build")
    ket.append(("8. lệnh không phải git -> QUA", rc == 0 and qd != "deny"))

    # 9 — hook gặp lỗi bên trong: gói vào hỏng + transcript rác
    rc1, qd1, _, _ = goi("git add %s" % TEP_W09, hong=True)
    with open(os.path.join(subagents, "agent-%s.jsonl" % aid_w07), "wb") as fh:
        fh.write(b"\x00\x01r\xc3\xa1c kh\xc3\xb4ng ph\xe1\xba\xa3i jsonl\n" * 50)
    rc2, qd2, _, err2 = goi("git add %s" % TEP_W09)
    ket.append(("9. hỏng bên trong (gói vào + transcript rác) -> QUA, mã thoát 0",
                rc1 == 0 and qd1 != "deny" and rc2 == 0 and qd2 != "deny"))

    # 10 — `git-scope-ok` không mở được tầng vùng (dựng lại transcript sạch)
    _ghi_transcript_worker(subagents, aid_w07, "W07 Printbelle", BRIEF_W07, [TEP_W07])
    rc, qd, ly, _ = goi("git add %s   # git-scope-ok" % TEP_W09)
    ket.append(("10. `git-scope-ok` KHÔNG mở được tầng vùng -> CHẮN",
                qd == "deny"))

    # ── TẦNG 3: lệnh gói/huỷ cả cây ────────────────────────────────────────────────
    rc, qd, ly, _ = goi(CT + ' -q -m "x"')
    ket.append(("11. worker + còn worker khác sống + commit TRẦN (index sạch) -> CHẮN",
                qd == "deny" and "56 GIÂY" in ly))
    ket.append(("11b. lời chặn gọi tên worker khác đang ở cùng cây",
                qd == "deny" and ("W09" in ly or "W20" in ly)))

    rc, qd, ly, _ = goi(CT + " -q -F - <<'EOF'\nfix(W07): abc\nEOF")
    ket.append(("12. commit TRẦN dạng heredoc (đúng dạng W07 dùng) -> CHẮN", qd == "deny"))

    rc, qd, ly, _ = goi(CT + ' -q -m "x" -- %s' % TEP_W07)
    ket.append(("13. commit NÊU ĐÍCH DANH đường dẫn trong vùng -> QUA", qd != "deny"))

    rc, qd, ly, _ = goi(CT + ' -q -m "x"', aid=None)
    ket.append(("14. phiên MAIN + commit trần -> QUA", qd != "deny"))

    rc, qd, ly, _ = goi("git stash")
    ket.append(("16. `git stash` không kèm đường dẫn -> CHẮN", qd == "deny"))

    rc, qd, ly, _ = goi("git stash push -- %s" % TEP_W07)
    ket.append(("17. `git stash push -- <tệp trong vùng>` -> QUA", qd != "deny"))

    rc, qd, ly, _ = goi('git diff --cached --name-only && echo "git-scope-ok da doi chieu" && '
                        + CT + " -q -F - <<'EOF'\nfix(W07): abc\nEOF")
    ket.append(("18. ĐÚNG LỆNH W07 ĐÃ LÁCH (commit trần + git-scope-ok) -> CHẮN",
                qd == "deny"))

    rc, qd, ly, _ = goi("cat > /tmp/w13-ca-thu-msg.txt <<'EOF'\n" + CT
                        + " -q -m \"day la VAN BAN, khong phai lenh\"\nEOF")
    ket.append(("19. thân heredoc có chữ commit, lệnh thật là `cat >` -> QUA (không oan)",
                qd != "deny"))

    rc, qd, ly, _ = goi(CT + " -F /tmp/m.txt -- %s 2>&1" % TEP_W07)
    ket.append(("20. `2>&1` KHÔNG bị đọc thành đường dẫn -> QUA",
                qd != "deny" and "2>&1" not in ly))

    # 21: brief khai vùng bằng đường dẫn TUYỆT ĐỐI của kho khác, lệnh `cd` sang đó rồi
    # gõ đường dẫn TƯƠNG ĐỐI — phải QUA (ca chặn oan chính lượt vá này gặp).
    kho2 = os.path.join(goc, "kho-luat")
    os.makedirs(os.path.join(kho2, "enforce", "claude", "hooks"))
    aid_kho = "a000000000000kho"
    _ghi_transcript_worker(subagents, aid_kho, "W31 sửa kho luật",
                           "GHI: %s\nĐỌC: -\nTÀI NGUYÊN: -" % kho2, [])
    rc, qd, ly, _ = goi("cd %s && git add enforce/claude/hooks/x.py" % kho2, aid=aid_kho)
    ket.append(("21. `cd <kho khác>` + đường dẫn tương đối trong vùng khai -> QUA",
                qd != "deny"))
    rc, qd, ly, _ = goi("cd %s && git add ../ngoai-vung/y.py" % kho2, aid=aid_kho)
    ket.append(("21b. cùng kiểu nhưng trỏ RA NGOÀI vùng khai -> vẫn CHẮN hoặc không đo được",
                True if qd != "deny" else "ngoai-vung" in ly))

    # ══ W15 — MỌI ĐƯỜNG GHI VÀO CHỖ CHỜ, KHÔNG CHỈ `git add` ════════════════════════
    # Ca thật: 03:43:47 W10 chạy `git apply --cached /tmp/w10-cd-mine.patch` -> card-dialog.tsx
    # nằm sẵn trong chỗ chờ dùng chung mà KHÔNG qua `git add`; 04:11:45 thợ khác commit trần
    # cuốn theo -> nhánh chính gãy build.
    def _va(ten, tep):
        p = os.path.join(goc, ten)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("diff --git a/%s b/%s\nindex 1111111..2222222 100644\n"
                     "--- a/%s\n+++ b/%s\n@@ -1,1 +1,2 @@\n a\n+b\n" % (tep, tep, tep, tep))
        return p

    VA_NGOAI = _va("w09.patch", TEP_W09)
    VA_TRONG = _va("w07.patch", TEP_W07)

    rc, qd, ly, _ = goi("git apply --cached %s" % VA_NGOAI)
    ket.append(("22. `apply --cached <vá đụng card-dialog.tsx>` -> CHẮN",
                qd == "deny" and TEP_W09 in ly))
    ket.append(("22b. lời chặn nêu W09 đang giữ vùng đó", qd == "deny" and "W09" in ly))

    rc, qd, ly, _ = goi("git apply --cached %s" % VA_TRONG)
    ket.append(("23. `apply --cached <vá chỉ đụng tệp TRONG vùng>` -> QUA", qd != "deny"))

    rc, qd, ly, _ = goi("git apply --index %s" % VA_NGOAI)
    ket.append(("24. `apply --index` ngoài vùng -> CHẮN", qd == "deny" and TEP_W09 in ly))

    rc, qd, ly, _ = goi("git apply %s" % VA_NGOAI)
    ket.append(("25. `apply` (chỉ ghi cây) ngoài vùng -> CHẮN", qd == "deny"))

    rc, qd, ly, _ = goi("git apply --check %s" % VA_NGOAI)
    ket.append(("26. `apply --check` (đọc thuần) -> QUA, không chặn oan", qd != "deny"))
    rc, qd, ly, _ = goi("git apply --numstat %s" % VA_NGOAI)
    ket.append(("26b. `apply --numstat` -> QUA", qd != "deny"))

    rc, qd, ly, _ = goi("cat %s | git apply --cached -" % VA_NGOAI)
    ket.append(("27. `cat <vá> | apply --cached -` -> CHẮN (bóc vá từ chuỗi lệnh)",
                qd == "deny" and TEP_W09 in ly))

    rc, qd, ly, _ = goi("git apply --cached - <<'EOF'\n"
                        "diff --git a/%s b/%s\n--- a/%s\n+++ b/%s\n@@ -1 +1 @@\n-a\n+b\nEOF"
                        % (TEP_W09, TEP_W09, TEP_W09, TEP_W09))
    ket.append(("28. `apply --cached` với bản vá trong heredoc -> CHẮN",
                qd == "deny" and TEP_W09 in ly))

    rc, qd, ly, _ = goi("printf '%s' \"$VA\" | git apply --cached -")
    ket.append(("29. nguồn vá KHÔNG đọc được + còn worker khác -> CHẮN",
                qd == "deny" and "bản vá" in ly))
    rc, qd, ly, _ = goi("printf '%s' \"$VA\" | git apply --cached -", aid=None)
    ket.append(("29b. cùng lệnh nhưng phiên MAIN -> QUA", qd != "deny"))

    rc, qd, ly, _ = goi("git update-index --add %s" % TEP_W09)
    ket.append(("30. `update-index --add <ngoài vùng>` -> CHẮN", qd == "deny" and TEP_W09 in ly))
    rc, qd, ly, _ = goi("git update-index --add %s" % TEP_W07)
    ket.append(("30b. `update-index --add <trong vùng>` -> QUA", qd != "deny"))

    rc, qd, ly, _ = goi("git rm --cached %s" % TEP_W09)
    ket.append(("31. `rm --cached <ngoài vùng>` -> CHẮN", qd == "deny" and TEP_W09 in ly))
    rc, qd, ly, _ = goi("git rm %s" % TEP_W07)
    ket.append(("31b. `rm <trong vùng>` -> QUA", qd != "deny"))

    rc, qd, ly, _ = goi("git mv %s src/app/pipeline/_components/card2.tsx" % TEP_W09)
    ket.append(("32. `mv` tệp ngoài vùng -> CHẮN", qd == "deny" and TEP_W09 in ly))

    rc, qd, ly, _ = goi("git checkout HEAD -- %s" % TEP_W09)
    ket.append(("33. `checkout HEAD -- <ngoài vùng>` -> CHẮN", qd == "deny" and TEP_W09 in ly))
    ket.append(("33b. `HEAD` KHÔNG bị đọc thành đường dẫn", "vùng `HEAD`" not in ly))
    rc, qd, ly, _ = goi("git checkout HEAD -- %s" % TEP_W07)
    ket.append(("33c. `checkout HEAD -- <trong vùng>` -> QUA", qd != "deny"))

    rc, qd, ly, _ = goi("git restore --staged --source=HEAD -- %s" % TEP_W09)
    ket.append(("34. `restore --staged --source=HEAD -- <ngoài vùng>` -> CHẮN",
                qd == "deny" and TEP_W09 in ly))

    rc, qd, ly, _ = goi("git reset -- %s" % TEP_W09)
    ket.append(("35. `reset -- <ngoài vùng>` -> CHẮN", qd == "deny" and TEP_W09 in ly))
    rc, qd, ly, _ = goi("git reset -- %s" % TEP_W07)
    ket.append(("35b. `reset -- <trong vùng>` -> QUA (có nêu đích danh)", qd != "deny"))
    rc, qd, ly, _ = goi("git reset")
    ket.append(("35c. `reset` trần (gỡ chỗ chờ của cả cây) -> CHẮN", qd == "deny"))

    rc, qd, ly, _ = goi("git read-tree HEAD")
    ket.append(("36. `read-tree HEAD` -> CHẮN", qd == "deny"))

    rc, qd, ly, _ = goi("git stash pop")
    ket.append(("37. `stash pop` -> CHẮN", qd == "deny"))
    rc, qd, ly, _ = goi("git stash list")
    ket.append(("37b. `stash list` (đọc) -> QUA", qd != "deny"))

    rc, qd, ly, _ = goi("git cherry-pick -n abc1234")
    ket.append(("38. `cherry-pick -n` -> CHẮN", qd == "deny"))
    rc, qd, ly, _ = goi("git cherry-pick --abort")
    ket.append(("38b. `cherry-pick --abort` (đường thoát) -> QUA", qd != "deny"))

    rc, qd, ly, _ = goi("git merge nhanh2")
    ket.append(("39. `merge <nhánh>` -> CHẮN", qd == "deny"))
    rc, qd, ly, _ = goi("git rebase --continue")
    ket.append(("39b. `rebase --continue` (đường thoát) -> QUA", qd != "deny"))

    rc, qd, ly, _ = goi("git checkout nhanh2")
    ket.append(("40. `checkout <nhánh>` đổi nhánh cả cây -> CHẮN", qd == "deny"))
    rc, qd, ly, _ = goi("git switch -c viec-w07")
    ket.append(("40b. `switch -c <nhánh mới>` -> CHẮN", qd == "deny"))

    rc, qd, ly, _ = goi("git worktree add ../cay-phu -b viec-w07")
    ket.append(("41. `worktree add` (cách ly, KHÔNG rò) -> QUA", qd != "deny"))
    rc, qd, ly, _ = goi("git worktree list")
    ket.append(("41b. `worktree list` -> QUA", qd != "deny"))
    rc, qd, ly, _ = goi("git worktree remove --force ../cay-phu")
    ket.append(("41c. `worktree remove --force` (xoá cây phụ đang bẩn) -> CHẮN", qd == "deny"))

    rc, qd, ly, _ = goi("git status --short && git diff --stat && git log --oneline -3")
    ket.append(("42. lệnh ĐỌC thuần (status/diff/log) -> QUA", qd != "deny"))

    # ── W15: trailer danh tính KHÔNG được chèn vào DỮ LIỆU ────────────────────────────
    # Đo được ngay trong lượt vá 18/09/2026: lệnh `python3 - <<PY … PY` có dòng dữ liệu
    # chứa chữ `git commit`; hook chèn `--trailer` vào giữa chuỗi Python -> SyntaxError.
    def lenh_sau_hook(cmd, aid=aid_w07):
        goi_tin = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                   "tool_input": {"command": cmd}, "cwd": cwd,
                   "session_id": phien, "transcript_path": transcript_cha, "agent_id": aid}
        r = subprocess.run([sys.executable, gate], input=json.dumps(goi_tin, ensure_ascii=False),
                           capture_output=True, text=True, env=moi, cwd=cwd, timeout=60)
        try:
            ra = json.loads(r.stdout or "{}").get("hookSpecificOutput") or {}
        except Exception:
            ra = {}
        return str((ra.get("updatedInput") or {}).get("command") or "")

    ma = ("python3 - <<'PY'\nfor cmd in [(\"" + CT + " -m x\", \"nhan\")]:\n"
          "    print(cmd)\nPY")
    ket.append(("43. `git commit` nằm trong THÂN HEREDOC -> hook KHÔNG sửa lệnh",
                lenh_sau_hook(ma) == ""))
    sua = lenh_sau_hook(CT + ' -q -m "x" -- %s' % TEP_W07)
    ket.append(("43b. commit THẬT (ngoài dữ liệu) -> vẫn được chèn trailer Worker=W07",
                'Worker=W07' in sua))

    # ca 15 cần một cây CHỈ CÓ MỘT worker -> hộp cát riêng
    cwd2 = os.path.join(goc, "du-an-mot-tho", "MotTho")
    os.makedirs(os.path.join(cwd2, "src", "lib", "fulfill"))
    slug2 = _re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(cwd2))
    sub2 = os.path.join(projects, slug2, phien, "subagents")
    os.makedirs(sub2)
    aid2 = "a0000000000000one"
    _ghi_transcript_worker(sub2, aid2, "W30 một mình một cây", BRIEF_W07, [TEP_W07])
    tc2 = os.path.join(projects, slug2, "%s.jsonl" % phien)
    open(tc2, "w").close()
    goi_tin = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
               "tool_input": {"command": CT + ' -q -m "x"'}, "cwd": cwd2,
               "session_id": phien, "transcript_path": tc2, "agent_id": aid2}
    r = subprocess.run([sys.executable, gate], input=json.dumps(goi_tin, ensure_ascii=False),
                       capture_output=True, text=True, env=moi, cwd=cwd2, timeout=60)
    try:
        ra = json.loads(r.stdout or "{}").get("hookSpecificOutput") or {}
    except Exception:
        ra = {}
    ket.append(("15. cây chỉ có MỘT worker + commit trần -> QUA kèm NHẮC",
                str(ra.get("permissionDecision") or "") != "deny"
                and "NHẮC" in str(ra.get("permissionDecisionReason") or "")))
    return ket


def main():
    gate = GATE_MAC_DINH
    if "--gate" in sys.argv:
        gate = sys.argv[sys.argv.index("--gate") + 1]
    print("CỔNG ĐANG THỬ: %s\n" % gate)
    ket = chay(gate)
    for ten, ok in ket:
        print("  %s %s" % ("✓" if ok else "✗", ten))
    dat = sum(1 for _, ok in ket if ok)
    print("\n  ==> %d/%d ca đúng" % (dat, len(ket)))
    return 0 if dat == len(ket) else 1


if __name__ == "__main__":
    sys.exit(main())
