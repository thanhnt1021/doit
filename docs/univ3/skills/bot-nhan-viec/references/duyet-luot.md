# Mẫu DUYỆT LƯỢT `/lam` (skill mục 7e) — trích từ bản gọn Nhà thuốc (PHP/SQLite + CLI Python), 12/10/2026

> Chép nguyên khối rồi đổi tên hàm sẵn có của dự án: `db()` · `giao_dich()` · `tg()` · `luu_tin()` · `viec_co()` ·
> `doi_trang_thai()` · `viec_dong()` · `khoi_dong()` · `muc_cho()` (việc đang chờ chủ nhà cho làm) · `may_nha_dang_mo()` ·
> `chat_chu_nha()` · `viec_trong_nhom()` · `esc()` · `hoi_nfc()`. Không có khoá / mã nhóm nào ở đây.
> Bản đầy đủ (Postgres, bảng thẻ): lượt = một bảng `duyet_luot` y hệt; «việc đang chờ» = thẻ nhãn «Làm sau» / `cho_khoi_dong`;
> gộp = lệnh gộp thẻ có sẵn (dời diễn biến, thẻ phụ sang Xong kèm `gop_vao`); khởi động = `khoiDongTatCa` nhưng theo danh sách mã.

## 1. Kho — hai bảng (tạo theo `sqlite_master`, KHÔNG tăng `user_version`)

```php
// trong db(), sau các bậc nâng cấp:
if (!$db->query("SELECT 1 FROM sqlite_master WHERE type='table' AND name='duyet_luot_tin'")->fetchColumn())
    $db->exec("
CREATE TABLE IF NOT EXISTS duyet_luot (
  id INTEGER PRIMARY KEY AUTOINCREMENT, trang_thai TEXT NOT NULL, ban INTEGER NOT NULL DEFAULT 0, phuong_an TEXT,
  message_id INTEGER, gop_y TEXT, lich_su TEXT NOT NULL DEFAULT '[]', ket_qua TEXT, yeu_cau_chat TEXT, yeu_cau_mid INTEGER,
  tao_luc INTEGER NOT NULL, cap_nhat INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS duyet_luot_tin (chat_id TEXT NOT NULL, message_id INTEGER NOT NULL, dl_id INTEGER NOT NULL,
  ban INTEGER NOT NULL, PRIMARY KEY(chat_id, message_id));");
```
`trang_thai`: cho-may → cho-chu-nha → gop-y → cho-chu-nha … → da-ok → dang-ap → da-ap. `lich_su` = JSON các bản + góp ý;
`ket_qua` = JSON {khoi_dong, bo_qua, gop, bo, de_sau, hoi_da_gui}.

## 2. Hằng + luật OK

```php
const DL_MO = ['cho-may', 'cho-chu-nha', 'gop-y', 'da-ok', 'dang-ap'];
const DL_CAN_MAY = ['cho-may', 'gop-y', 'da-ok', 'dang-ap'];
const DL_NHOM = ['lam', 'hoi', 'gop', 'bo', 'de_sau'];
const DL_TEN_TT = ['cho-may' => 'chờ máy dựng phương án', 'cho-chu-nha' => 'chờ anh duyệt', 'gop-y' => 'máy đang sửa theo góp ý của anh',
    'da-ok' => 'anh đã OK, chờ máy làm', 'dang-ap' => 'máy đang làm theo phương án', 'da-ap' => 'đã làm xong', 'huy' => 'đã huỷ'];
// «OK» = CẢ tin chỉ là lời đồng ý (kèm «hết»/dấu câu được). «ok nhưng 02 bỏ» là góp ý — quy tắc tất định, không đoán.
// 👍❤️ chỉ được ĐI SAU chữ đồng ý; tin chỉ có emoji và cảm xúc (message_reaction) thả lên tin phương án KHÔNG BAO GIỜ là OK (SKILL mục 4.9).
const DL_OK_RE = '/^(?:ok|oke|okie|okay|okela|duyệt|đồng ý|chốt|làm đi|cứ làm đi|được|1a)(?:\s+(?:hết|tất cả|luôn|nhé|nha|đi))*[\s.!👍❤️]*$/iu';
```

## 3. Webhook

`/lam` trần (trong hàm xử lý `/lam`, sau khi đã chắc là chủ nhà):
```php
if ($doi === '' && empty($m['reply_to_message']['message_id'])) return [null, 'lam', dl_yeu_cau($chat, (int)$m['message_id'], $rieng)];
```
Chat riêng chủ nhà — đứng TRƯỚC luồng câu hỏi / Reply tin có mã:
```php
if ($rt && ($dlt = dl_cua_tin($chat, $rt))) {
    if (!luu_tin($m)) return null;              // Telegram gửi lại
    return ['loai' => 'duyet', 'text' => dl_tra_loi($m, $dlt)];   // câu đáp trả thẳng trong phản hồi webhook
}
```

```php
// /lam trần (gọi TRONG giao_dich của webhook). Trả câu đáp HTML. Lượt đang mở → báo tình trạng, không đẻ lượt thứ hai.
function dl_yeu_cau(string $chat, int $mid, bool $rieng): string {
    $d = dl_mo();
    if ($d) {
        $s = '⏳ Lượt <b>DL' . $d['id'] . '</b> đang mở' . ($d['ban'] ? ' (bản ' . $d['ban'] . ')' : '') . ' — ' . DL_TEN_TT[$d['trang_thai']] . '.';
        if ($d['trang_thai'] === 'cho-chu-nha') $s .= ' Anh Reply tin phương án mới nhất trong chat riêng: gõ <b>OK</b> hoặc góp ý.';
        return $s;
    }
    $n = count(muc_cho());
    if (!$n) return '▶ Không có việc nào đang chờ duyệt.';
    db()->prepare('INSERT INTO duyet_luot (trang_thai, yeu_cau_chat, yeu_cau_mid, tao_luc, cap_nhat) VALUES (?,?,?,?,?)')
        ->execute(['cho-may', $chat, $mid, time(), time()]);
    $id = (int)db()->lastInsertId();
    if (!may_nha_dang_mo()) // W158 — trong nhóm sếp đọc được: không nói «máy tắt», chỉ nói đang nhiều việc
        return '📝 Đã ghi yêu cầu duyệt lượt <b>DL' . $id . '</b> (' . $n . ' việc đang chờ). '
            . ($rieng ? 'Máy nhà đang tắt — mở máy là duyệt ngay, yêu cầu không mất.' : 'Hệ thống đang nhiều việc, sẽ duyệt ngay khi rảnh — yêu cầu không mất.');
    return '⏳ Đang duyệt lượt <b>DL' . $id . '</b> — ' . $n . ' việc đang chờ. Phương án (làm được ngay · cần hỏi lại · gộp) sẽ gửi vào '
        . 'chat riêng anh ' . esc(ten_chu_nha()) . ' trong vài phút; anh OK hết thì máy mới làm.';
}

// Chủ nhà Reply tin phương án trong chat riêng (gọi TRONG giao_dich, tin đã luu_tin). Trả câu đáp HTML.
function dl_tra_loi(array $m, array $tin): string {
    $d = dl_co((int)$tin['dl_id']);
    $e = '<b>DL' . $d['id'] . '</b>';
    $chu = trim(hoi_nfc((string)($m['text'] ?? $m['caption'] ?? '')));
    if (in_array($d['trang_thai'], ['da-ok', 'dang-ap', 'da-ap', 'huy'], true))
        return 'ℹ Lượt ' . $e . ' ' . DL_TEN_TT[$d['trang_thai']] . ' — tin này không đổi gì. Muốn duyệt lại thì gõ /lam.';
    if ((int)$tin['ban'] < (int)$d['ban'])
        return 'ℹ Tin anh Reply là bản ' . $tin['ban'] . ' (cũ) của ' . $e . ' — anh Reply <b>bản ' . $d['ban'] . '</b> mới nhất.';
    $ls = $d['lich_su'];
    if ($d['trang_thai'] === 'cho-chu-nha' && preg_match(DL_OK_RE, $chu)) {
        $ls[] = ['ban' => (int)$d['ban'], 'luc' => time(), 'ok' => $chu];
        dl_doi((int)$d['id'], ['trang_thai' => 'da-ok', 'lich_su' => $ls]);
        return '✅ Đã duyệt ' . $e . ' bản ' . $d['ban'] . ' — máy bắt đầu làm: ' . dl_dem($d['phuong_an'] ?? []) . '.'
            . (may_nha_dang_mo() ? '' : ' Máy nhà đang tắt — mở máy là làm.');
    }
    $chu = $chu !== '' ? $chu : '(ảnh/tệp)';
    $gop = $d['trang_thai'] === 'gop-y' && $d['gop_y'] ? $d['gop_y'] . "\n" . $chu : $chu; // góp tiếp trước khi có bản mới
    $ls[] = ['ban' => (int)$d['ban'], 'luc' => time(), 'gop_y' => $chu];
    dl_doi((int)$d['id'], ['trang_thai' => 'gop-y', 'gop_y' => mb_substr($gop, 0, 4000), 'lich_su' => $ls]);
    return '📝 Đã ghi góp ý cho ' . $e . ' bản ' . $d['ban'] . ' — máy sửa phương án rồi gửi <b>bản ' . ((int)$d['ban'] + 1) . '</b> vào đây.';
}
```

## 4. Soát phương án (tất định — thiếu là từ chối, không gửi)

```php
// Soát phương án: trả [phương án đã chuẩn hoá, danh sách lỗi]. Mọi việc đang chờ phải có mặt ĐÚNG MỘT lần.
function dl_soat(array $pa): array {
    $cho = muc_cho();
    $khac = dl_mo_khac();
    $loi = []; $dem = []; $chuan = array_fill_keys(DL_NHOM, []);
    $s = fn($x) => trim(hoi_nfc((string)$x));
    foreach (array_keys($pa) as $k) if (!in_array($k, DL_NHOM, true)) $loi[] = 'nhóm lạ «' . $k . '» (chỉ ' . implode(' · ', DL_NHOM) . ')';
    $them = function (string $ma, string $nhom) use (&$dem, &$loi, $cho) {
        if (!in_array($ma, $cho, true)) { $loi[] = $ma . ' (' . $nhom . ') không phải việc đang chờ'; return; }
        $dem[$ma][] = $nhom;
    };
    foreach (['lam' => 'du_kien', 'bo' => 'vi_sao', 'de_sau' => 'vi_sao'] as $nhom => $truong)
        foreach ((array)($pa[$nhom] ?? []) as $x) {
            $ma = $s($x['ma'] ?? '');
            $chu = $s($x[$truong] ?? '');
            if ($nhom === 'lam' && $chu === '') $loi[] = $ma . ': thiếu dòng dự kiến làm gì (du_kien)';
            $them($ma, $nhom);
            $chuan[$nhom][] = ['ma' => $ma, $truong => $chu];
        }
    foreach ((array)($pa['hoi'] ?? []) as $x) {
        $ma = $s($x['ma'] ?? ''); $ai = $s($x['ai'] ?? ''); $cau = $s($x['cau'] ?? '');
        if (!in_array($ai, ['sep', 'chu-nha'], true)) $loi[] = $ma . ': hỏi ai phải là sep | chu-nha';
        if (!preg_match('/^1\.\s+\S.*?(?<![\p{L}\d])1A(?![\p{L}\d]).*?(?<![\p{L}\d])1B(?![\p{L}\d])/su', $cau))
            $loi[] = $ma . ': câu hỏi phải đúng khuôn «1. …? 1A … · 1B …»';
        $them($ma, 'hoi');
        $chuan['hoi'][] = ['ma' => $ma, 'ai' => $ai, 'cau' => $cau, 'tieu_de' => mb_substr($s($x['tieu_de'] ?? ''), 0, 70)];
    }
    $xep = fn($ma) => array_intersect($dem[$ma] ?? [], ['lam', 'hoi', 'de_sau']);
    foreach ((array)($pa['gop'] ?? []) as $x) {
        $chinh = $s($x['chinh'] ?? '');
        $phu = array_values(array_unique(array_filter(array_map($s, (array)($x['phu'] ?? [])))));
        if (!$phu) $loi[] = 'gộp vào ' . $chinh . ': thiếu việc phụ';
        if (in_array($chinh, $phu, true)) $loi[] = 'gộp: ' . $chinh . ' vừa là việc chính vừa là việc phụ';
        foreach ($phu as $p) $them($p, 'gop');
        $chuan['gop'][] = ['chinh' => $chinh, 'phu' => $phu, 'vi_sao' => $s($x['vi_sao'] ?? '')];
    }
    foreach ($chuan['gop'] as $g) // việc chính: việc đang chờ đã xếp làm/hỏi/để sau, hoặc việc đang mở khác
        if (!(in_array($g['chinh'], $khac, true) || (in_array($g['chinh'], $cho, true) && $xep($g['chinh']))))
            $loi[] = 'gộp vào ' . $g['chinh'] . ': việc chính phải là việc đang mở, hoặc việc đang chờ đã xếp làm/hỏi/để sau';
    foreach ($dem as $ma => $ds) if (count($ds) > 1) $loi[] = $ma . ' nằm ' . count($ds) . ' chỗ (' . implode(', ', $ds) . ') — mỗi việc đúng một chỗ';
    $thieu = array_values(array_diff($cho, array_keys($dem)));
    if ($thieu) $loi[] = 'chưa xếp ' . count($thieu) . ' việc đang chờ: ' . implode(', ', $thieu);
    if (!$cho) $loi[] = 'không có việc nào đang chờ';
    return [$chuan, array_values(array_unique($loi))];
}
```

## 5. Gộp (cách gộp thẻ Fulfill) + áp

```php
// Gộp kiểu Fulfill gop-the.ts (gọi TRONG giao_dich): mọi tin của việc phụ dời sang việc chính → Reply tin cũ của việc phụ tự
// vào việc chính; câu đáp / thẻ / mã phụ trỏ việc phụ cũng đổi sang việc chính (sửa câu đáp về sau không gắn lại mã phụ).
function gop_viec(string $chinh, array $phu, string $vi_sao, string $nguon): array {
    $xong = [];
    foreach ($phu as $p) {
        $vp = viec_co($p);
        if (!$vp || $p === $chinh || !viec_co($chinh)) continue;
        db()->prepare('UPDATE tin SET ma_viec=? WHERE ma_viec=?')->execute([$chinh, $p]);
        db()->prepare('UPDATE OR IGNORE ma_phu SET ma=? WHERE ma=?')->execute([$chinh, $p]);
        db()->prepare('DELETE FROM ma_phu WHERE ma=?')->execute([$p]);
        db()->prepare("UPDATE dap SET ma=?, ma_ds=REPLACE(ma_ds, ?, ?) WHERE ma=? OR instr(COALESCE(ma_ds,''), ?) > 0")
            ->execute([$chinh, '"' . $p . '"', '"' . $chinh . '"', $p, '"' . $p . '"']);
        db()->prepare('UPDATE the_viec SET ma=? WHERE ma=?')->execute([$chinh, $p]);
        doi_trang_thai($p, 'da-chuyen', true);
        db()->prepare('UPDATE viec SET chuyen_sang=? WHERE ma=?')->execute([$chinh, $p]);
        viec_dong($p, '🔗 Gộp vào ' . $chinh . ' (' . $nguon . ')' . ($vi_sao !== '' ? ' — ' . $vi_sao : ''));
        viec_dong($chinh, '🔗 Gộp ' . $p . ' vào đây (' . $nguon . ')' . ($vi_sao !== '' ? ' — ' . $vi_sao : '') . ' · tiêu đề: '
            . $vp['tieu_de'] . ' · nội dung: ' . mb_substr(trim((string)$vp['noi_dung']), 0, 600));
        cham_viec($chinh);
        $xong[] = $p;
    }
    return $xong;
}

// Áp lượt đã OK (gọi TRONG giao_dich). Lần đầu: gộp → khởi động → bỏ / để sau, sang «dang-ap». Lần sau (CLI chết giữa chừng):
// không áp lại, chỉ trả các câu hỏi chưa gửi. $thu = chỉ đọc.
function dl_ap(bool $thu): array {
    $d = dl_mo();
    if (!$d || !in_array($d['trang_thai'], ['da-ok', 'dang-ap'], true))
        throw new RuntimeException('⛔ Chưa có lượt nào chủ nhà đã OK' . ($d ? ' (DL' . $d['id'] . ' đang «' . $d['trang_thai'] . '»)' : ''));
    $pa = $d['phuong_an'] ?? [];
    $kq = $d['ket_qua'] ?? ['khoi_dong' => [], 'bo_qua' => [], 'gop' => [], 'bo' => [], 'de_sau' => [], 'hoi_da_gui' => []];
    $nguon = 'duyệt lượt DL' . $d['id'] . ' bản ' . $d['ban'];
    if ($d['trang_thai'] === 'da-ok' && !$thu) {
        foreach ($pa['gop'] ?? [] as $g)
            if ($x = gop_viec($g['chinh'], $g['phu'], $g['vi_sao'] ?? '', $nguon)) $kq['gop'][] = ['chinh' => $g['chinh'], 'phu' => $x];
        $k = khoi_dong(array_column($pa['lam'] ?? [], 'ma'), false, $nguon);
        $kq['khoi_dong'] = $k['khoi_dong'];
        $kq['bo_qua'] = $k['bo_qua'];
        foreach ($pa['lam'] ?? [] as $x) if (in_array($x['ma'], $k['khoi_dong'], true)) viec_dong($x['ma'], '▶ Dự kiến (' . $nguon . '): ' . $x['du_kien']);
        foreach ($pa['bo'] ?? [] as $x) {
            $v = viec_co($x['ma']);
            if (!$v) continue;
            if ($v['trang_thai'] === 'ghi-nhan') doi_trang_thai($x['ma'], 'huy', true); // việc đang làm chỉ bỏ phần góp ý chờ
            db()->prepare('UPDATE tin SET ghi_nhan=0 WHERE ma_viec=?')->execute([$x['ma']]);
            viec_dong($x['ma'], '✖ chủ nhà bỏ (' . $nguon . ')' . ($x['vi_sao'] !== '' ? ' — ' . $x['vi_sao'] : ''));
            $kq['bo'][] = $x['ma'];
        }
        foreach ($pa['de_sau'] ?? [] as $x) {
            viec_dong($x['ma'], '⏸ để sau (' . $nguon . ')' . ($x['vi_sao'] !== '' ? ' — ' . $x['vi_sao'] : ''));
            $kq['de_sau'][] = $x['ma'];
        }
        foreach ($pa['hoi'] ?? [] as $x) viec_dong($x['ma'], '❓ ' . $nguon . ' — hỏi ' . ($x['ai'] === 'sep' ? 'sếp' : 'chủ nhà') . ': ' . $x['cau']);
        dl_doi((int)$d['id'], ['trang_thai' => 'dang-ap', 'ket_qua' => $kq]);
    }
    $hoi = [];
    foreach ($pa['hoi'] ?? [] as $x) {
        if (in_array($x['ma'], $kq['hoi_da_gui'], true) || !($v = viec_co($x['ma']))) continue;
        $hoi[] = $x + ['viec' => $v, 'trong_nhom' => viec_trong_nhom($v)];
    }
    return ['id' => (int)$d['id'], 'ban' => (int)$d['ban'], 'trang_thai' => $thu ? $d['trang_thai'] : 'dang-ap', 'thu' => $thu,
        'phuong_an' => $pa, 'ket_qua' => $kq, 'hoi' => $hoi];
}

// Lối gửi riêng cho việc NHÓM chỉ mở khi việc đó nằm trong mục «hỏi chủ nhà» của lượt đang áp (W194 vẫn chặn mọi lối khác).
function dl_cho_hoi_rieng(int $id, string $ma): bool {
    $d = dl_co($id);
    if (!$d || $d['trang_thai'] !== 'dang-ap') return false;
    foreach ($d['phuong_an']['hoi'] ?? [] as $x) if ($x['ma'] === $ma && $x['ai'] === 'chu-nha') return true;
    return false;
}
```
`dl_gui` (gửi bản: soát → sendPhoto / sendMediaGroup vào chat riêng → ghi `duyet_luot_tin` + bản +1 trong giao dịch) và `dl_xong`
(khép lượt + một tin tóm tắt Reply tin phương án) xem bản gốc `chatbot-host/sep-viec/priv/lib.php` của Nhà thuốc.

## 6. Lối máy (api.php)

```php
case 'chua-doc':  … tra(['ok' => true, 'tin' => $ds, 'duyet_luot' => dl_can_may()]);
case 'duyet-luot-xem': tra(['ok' => true, 'dl' => $d, 'cho' => muc_cho(), 'mo_khac' => dl_mo_khac()]);
case 'phuong-an':  thu → [$chuan, $loi] = dl_soat(...) ; thật → dl_gui($pa, $text, $anh)
case 'ap-phuong-an': $thu ? dl_ap(true) : giao_dich(fn() => dl_ap(false))
case 'ap-hoi':  giao_dich(fn() => dl_hoi_da_gui($id, $ma))
case 'ap-xong': dl_xong($id)
case 'gui': … if (rieng && viec_trong_nhom($v) && !(duyet_luot && dl_cho_hoi_rieng(duyet_luot, ma))) → 409
```

## 7. CLI — con canh thoát khi lượt cần máy

```python
            r = api("chua-doc", timeout=30)
            ds, dl = r["tin"], r.get("duyet_luot")
            …
            # W198 — lượt duyệt cần máy: báo khi lượt/trạng thái đổi, hoặc báo rồi mà quá --nhac-phut vẫn y nguyên.
            dl_bao = tt.get("dl_bao") or {}
            khoa_dl = "%s:%s:%s" % (dl["id"], dl["trang_thai"], dl["cap_nhat"]) if dl else None
            bao_dl = bool(dl) and (dl_bao.get("khoa") != khoa_dl or bay_gio - dl_bao.get("luc", 0) >= a.nhac_phut * 60)
            if bao_dl:
                dl_bao = {"khoa": khoa_dl, "luc": bay_gio}
            json.dump({"luc": dt.datetime.now(VN).isoformat(timespec="seconds"), "so_chua_doc": len(ds),
                       "ids": sorted(con), "da_bao": sorted((da_bao & con) | {t["id"] for t in moi}),
                       "theo_du_an": theo_du_an, "bao_luc": {str(k): v for k, v in bao_luc.items()},
                       "dl_bao": dl_bao if dl else {}, "duyet_luot": dl},
                      open(TT, "w"), ensure_ascii=False)
            if bao_dl:
                print("🔔 " + dong_duyet_luot(dl) + " — xong thì BẬT LẠI con canh")
                return
```

## 8. CLI — chú thích phương án + câu hỏi khi áp

```python
def dl_chu_thich(pa, ct, dl_ma, ban):
    """Chú thích tin phương án (≤ 1024 ký tự). Mã dài quá thì liệt kê STT (khớp ảnh) thay cho mã."""
    hang = dl_dong(pa, ct)

    def soan(theo_stt):
        out = ["📋 <b>[%s] Duyệt lượt · bản %s</b> · %d việc đang chờ" % (e(dl_ma), ban, len(hang)), ""]
        for k, ten, _, icon in DL_NHOM:
            ds = [h for h in hang if h[0] == k]
            if not ds:
                continue
            if k == "hoi":
                ai = {x["ma"]: DL_AI.get(x["ai"], x["ai"]) for x in pa["hoi"]}
                muc = ["%s (%s)" % (h[1] if theo_stt else h[2], ai[h[2]]) for h in ds]
            elif k == "gop":
                muc = []
                for g in pa["gop"]:
                    st = [str(h[1]) if theo_stt else h[2] for h in ds if h[2] in g["phu"]]
                    muc.append("%s → %s" % (", ".join(st), g["chinh"]))
            else:
                muc = [str(h[1]) if theo_stt else h[2] for h in ds]
            out.append("%s <b>%s (%d):</b> %s" % (icon, ten, len(ds), e(" · ".join(muc))))
        out += ["", "📍 <b>Xem ở:</b> bảng chi tiết trong ảnh" + (" (số là STT trong bảng)" if theo_stt else ""),
                "👉 <b>Cần làm:</b> <b>%s</b> — Reply tin này: gõ <b>OK</b> = duyệt hết · hoặc góp ý từng mục, vd «2 bỏ · 5 hỏi sếp "
                "thêm giá · gộp 3 với 7»" % TEN_CHU_NHA]
        return "\n".join(out)
    h = soan(False)
    return h if do_dai_thay(h) <= TRAN_CAPTION else soan(True)


def dl_ns_hoi(x, v, dl_id, thu, anh=None):
    """Namespace cho cmd_gui: câu «cần hỏi lại» của lượt. Hỏi sếp → NHÓM (Reply tin gốc tự động); hỏi chủ nhà → chat riêng có ảnh
    bảng việc trên đầu (máy chủ chỉ mở lối riêng cho việc nhóm khi câu nằm trong lượt đang áp)."""
    rieng = x["ai"] == "chu-nha"
    td = gon(x.get("tieu_de")) or gon(v.get("tieu_de")) or "(chưa đặt tiêu đề)"
    td = td if len(td) <= TRAN_TIEU_DE else td[:TRAN_TIEU_DE - 1].rstrip() + "…"
    nguoi = ten_giao(v)
    return argparse.Namespace(
        ma=x["ma"], tieu_de=td, noi_dung=None, hoi=[x["cau"]], da_lam=None,
        xem_o="ảnh bảng việc bên trên" if rieng else ("tin giao việc gốc phía trên" if v.get("tin_goc") else "sổ việc của Trợ lý hệ thống"),
        dong_cuoi=None, luu_y=None, ngan=None, reply_to=None, anh=[anh] if anh else [], nhan_anh=[], anh_co_chu=bool(anh), thu=thu,
        du_an=None, rieng=rieng, bi_mat=False, can_lam=None, ten=[nguoi] if nguoi else [], khong_anh=None, chu_de=None,
        vi_sao="%s duyệt lượt %s: việc này cần làm rõ trước khi làm" % (TEN_CHU_NHA, "DL%s" % dl_id), duyet_luot=dl_id)


def cmd_ap_phuong_an(a):
    """W198 — áp lượt chủ nhà đã OK. Máy chủ (một giao dịch) gộp → khởi động → bỏ / để sau; CLI gửi từng câu «cần hỏi lại» qua
    cmd_gui rồi ghi ap-hoi (chạy lại không gửi trùng); xong hết thì ap-xong (máy chủ báo chủ nhà). --thu: chỉ in."""
    r = api("ap-phuong-an", {"thu": a.thu})
    kq = r["ket_qua"]
    print("%sLượt DL%s bản %s · khởi động: %s · gộp: %s · bỏ: %s · để sau: %s" % (
        "(thử: chưa đổi gì) " if a.thu else "", r["id"], r["ban"], ", ".join(kq["khoi_dong"]) or ("(sẽ: %s)" % ", ".join(
            x["ma"] for x in r["phuong_an"].get("lam") or []) if a.thu else "—"),
        "; ".join("%s → %s" % (", ".join(g["phu"]), g["chinh"]) for g in kq["gop"]) or "—", ", ".join(kq["bo"]) or "—",
        ", ".join(kq["de_sau"]) or "—"))
    if kq.get("bo_qua"):
        print("Không còn chờ nên không khởi động: " + ", ".join(kq["bo_qua"]))
    import tempfile
    for x in r["hoi"]:
        anh = dl_anh_viec(x["viec"], r["id"], os.path.join(tempfile.gettempdir(), "dl-hoi-%s.png" % x["ma"])) if x["ai"] == "chu-nha" else None
        print("— câu hỏi %s → %s:" % (x["ma"], "chat riêng %s" % TEN_CHU_NHA if anh else "NHÓM (sếp), Reply tin gốc"))
        cmd_gui(dl_ns_hoi(x, x["viec"], r["id"], a.thu, anh))
        if anh and os.path.exists(anh):
            os.remove(anh)
        if not a.thu:
            api("ap-hoi", {"id": r["id"], "ma": x["ma"]})
    if a.thu:
        return
    x = api("ap-xong", {"id": r["id"]})
    print("Đã khép DL%s%s" % (r["id"], " — đã báo chủ nhà" if x.get("gui") else " — ⚠ báo chủ nhà hỏng (xem nhật ký máy chủ)"))
```
Ảnh bảng (`dl_anh`, Pillow): dải đỏ «Duyệt lượt DLn · bản b» · tiêu đề «Phương án dự kiến — N việc đang chờ» · hàng đầu bảng nền
tối «STT · Mã việc · Việc · Dự kiến / câu hỏi / gộp vào» · mỗi nhóm một hàng màu (làm ngay xanh lá, hỏi cam, gộp xanh dương, bỏ /
để sau xám) · hộp ghi chú vàng «<chủ nhà> Reply tin này: gõ OK … hoặc góp ý từng mục theo STT/mã». Cao quá ~6500 px thì chia trang
(album ≤ 3 ảnh; Telegram: rộng + cao ≤ 10000, tỉ lệ ≤ 20).
