#!/usr/bin/env python3
"""PreToolUse(Bash) hard-gate: CẤM ghi vào vùng tạm của PROJECT KHÁC.

SỰ CỐ THẬT (25/08/2026, ChicHub): `/tmp/sync-uni-state/` dùng chung cho MỌI
project trên máy. Một worker cần tìm clone SSOT của mình đã gõ

    cat /tmp/sync-uni-state/*/clone.txt | head -1

Bung ký tự đại diện xếp theo abc -> ra clone của project **vevoi** (đang có việc
watchdog dở dang) chứ không phải của ChicHub. Worker chép đè vào đó rồi mới tự
phát hiện. Lần này chỉ trúng thư mục tạm nên hoàn nguyên được; cùng lỗi mà trúng
kho luật thật của project khác thì mất việc người khác mà KHÔNG AI BIẾT.

Cổng này chặn TẤT ĐỊNH 3 mẫu (markdown = xác suất, hook = cổng):
  1. Bung ký tự đại diện trên `/tmp/sync-uni-state/*` -> CHẶN luôn, kể cả đọc.
     Đây chính là mẫu bệnh. Muốn biết clone của mình: `sync-uni.sh clone`.
  2. GHI vào `/tmp/sync-uni-state/<băm khác>` (không phải băm của project đang
     đứng) -> CHẶN. ĐỌC để chẩn đoán vẫn cho qua.
  3. GHI vào `/tmp/claude-bg-progress/<project khác>` -> CHẶN.

Băm thư mục = 12 ký tự đầu của `echo "<đường dẫn tuyệt đối>" | shasum`
(sync-uni.sh) -> sha1 của chuỗi có ký tự xuống dòng ở cuối.

Fail-open: mọi lỗi -> exit 0 (không bao giờ vỡ phiên).
"""
import hashlib
import json
import os
import re
import sys

SYNC_ROOT = "/tmp/sync-uni-state"
BG_ROOT = "/tmp/claude-bg-progress"

# Dấu hiệu GHI: động từ đổi đĩa + chuyển hướng. Không có cái nào = coi là ĐỌC.
_WRITE = re.compile(
    r"(?:(?<![\w./-])(?:cp|mv|rm|rmdir|tee|touch|mkdir|ln|rsync|install"
    r"|chmod|chown|unzip|tar)(?![\w-])"
    r"|(?<![\w./-])sed\s+-i"
    # `git -C <đường dẫn> checkout ...` -> phải nuốt được cờ/đường dẫn xen giữa,
    # nếu không thì `git -C /tmp/sync-uni-state/<khác>/ssot checkout` lọt lưới.
    r"|(?<![\w./-])git(?:\s+-\S+|\s+/\S+)*\s+"
    r"(?:checkout|restore|clean|reset|apply|stash|clone|init|add|commit|rm|mv)(?![\w-])"
    r"|>>?\s*[\"']?/tmp/)"
)
_GLOB = re.compile(re.escape(SYNC_ROOT) + r"/\*")
_SYNC_HASH = re.compile(re.escape(SYNC_ROOT) + r"/([0-9a-f]{12})")
_BG_DIR = re.compile(re.escape(BG_ROOT) + r"/([^/\s\"';|&)>]+)")


def bo_heredoc(cmd: str) -> str:
    """Bỏ THÂN heredoc. WHY: thông điệp commit / tài liệu KỂ LẠI sự cố phải nhắc
    đúng mẫu lệnh sai — không bỏ thì chính việc ghi luật cũng bị cổng này chặn."""
    if "<<" not in cmd:
        return cmd
    ra, dau = [], None
    for dong in cmd.splitlines():
        if dau is None:
            ra.append(dong)
            m = re.search(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?", dong)
            if m:
                dau = m.group(1)
        elif dong.strip() == dau:
            dau = None
    return "\n".join(ra)


_MSG_ARG = re.compile(r"(?:-m|--message)\s+(['\"])(?:\\.|(?!\1).)*\1", re.S)


def lam_sach(cmd: str) -> str:
    """Còn lại phần THỰC SỰ là lệnh: bỏ thân heredoc + nội dung -m/--message."""
    return _MSG_ARG.sub("-m MSG", bo_heredoc(cmd))


def trong_nhay(s: str, i: int) -> bool:
    """Vị trí i có nằm trong dấu nháy không -> `*` trong nháy KHÔNG bung."""
    nhay = None
    j = 0
    while j < i:
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if nhay is None and c in "'\"":
            nhay = c
        elif nhay == c:
            nhay = None
        j += 1
    return nhay is not None


def bam(duong_dan: str) -> str:
    return hashlib.sha1((duong_dan + "\n").encode("utf-8")).hexdigest()[:12]


def chan(ly_do: str) -> None:
    json.dump(
        {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": ly_do,
        }},
        sys.stdout, ensure_ascii=False,
    )
    sys.exit(0)


def main() -> None:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        sys.exit(0)
    cmd = lam_sach((data.get("tool_input") or {}).get("command", "") or "")
    if SYNC_ROOT not in cmd and BG_ROOT not in cmd:
        sys.exit(0)

    goc = os.environ.get("CLAUDE_PROJECT_DIR") or ""
    if not goc:
        sys.exit(0)  # không biết mình là ai -> không dám chặn
    goc = goc.rstrip("/")
    bam_toi = bam(goc)
    ten_toi = os.path.basename(goc)

    m_glob = _GLOB.search(cmd)
    if m_glob and not trong_nhay(cmd, m_glob.start()):
        chan(
            "⛔ CHẶN — bung ký tự đại diện trên %s/*.\n"
            "Đây ĐÚNG mẫu đã gây sự cố 25/08: `cat %s/*/clone.txt | head -1` ra clone của\n"
            "PROJECT KHÁC (xếp theo abc), worker chép đè lên việc dở của người ta.\n"
            "Cần clone SSOT của project này: `~/.claude/universal-hooks/sync-uni.sh clone`\n"
            "Chỉ muốn nhìn tổng quan: `ls -la %s/` (không có dấu sao)."
            % (SYNC_ROOT, SYNC_ROOT, SYNC_ROOT)
        )

    # Xét TỪNG ĐOẠN lệnh, không xét cả chuỗi: một lệnh ghép hay có đoạn ghi hợp
    # lệ vào vùng của mình đứng cạnh đoạn ĐỌC vùng dự án khác để chẩn đoán.
    doan_ghi = [d for d in re.split(r"[\n;]|&&|\|\||\|", cmd) if _WRITE.search(d)]

    la = sorted({h for d in doan_ghi for h in _SYNC_HASH.findall(d) if h != bam_toi})
    if la:
        chan(
            "⛔ CHẶN — lệnh có thao tác GHI trỏ vào vùng tạm sync-uni của PROJECT KHÁC: %s\n"
            "Project đang đứng : %s\n"
            "Vùng tạm của bạn  : %s/%s\n"
            "Ghi vào vùng của project khác = đè việc dở của người ta mà không ai biết.\n"
            "Muốn ĐỌC để chẩn đoán thì bỏ hết động từ ghi ra khỏi lệnh (cat/ls/git log)."
            % (", ".join(la), goc, SYNC_ROOT, bam_toi)
        )

    lb = sorted({x for d in doan_ghi for x in _BG_DIR.findall(d)
                 if x != ten_toi and not x.startswith("<")})
    if lb:
        chan(
            "⛔ CHẶN — GHI tiến độ worker vào thư mục của PROJECT KHÁC: %s\n"
            "Project đang đứng: %s (thư mục đúng: %s/%s/)\n"
            "Đọc để đối chiếu thì được; ghi thì không."
            % (", ".join(lb), ten_toi, BG_ROOT, ten_toi)
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
