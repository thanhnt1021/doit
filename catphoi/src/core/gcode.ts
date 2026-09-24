/**
 * Sinh G-code tham khảo cho máy cắt plasma/hơi chạy G-code.
 * Chưa có file G-code mẫu của máy nên dùng dialect phổ thông, mọi mã đều cấu hình được.
 * Thứ tự cắt: lỗ trước, bao ngoài sau; chi tiết nhỏ cắt trước; đi theo đường ngắn nhất.
 */
import type { GcodeOptions, Part, Point, Ring, SheetLayout } from '../types';
import { DEFAULT_GCODE_OPTIONS, applyPlacementRing, signedArea } from '../types';
import { labelPoint, offsetRingsForKerf, pointInRing } from './geometry';
import { placementLabel, type ExportExtras } from './dxf-export';

interface CutRing {
  ring: Ring;
  isHole: boolean;
}

interface CutPart {
  label: string;
  area: number;
  /** Điểm mốc để sắp thứ tự cắt — dùng điểm cực nên luôn nằm trong chi tiết. */
  center: Point;
  rings: CutRing[];
}

function clamp(v: number, lo: number, hi: number): number {
  return v < lo ? lo : v > hi ? hi : v;
}

/**
 * Tính điểm bắt đầu lead-in: đi thẳng, vuông góc cạnh đầu tiên, nằm NGOÀI vùng cắt.
 * Với vòng bao ngoài thì "ngoài" là ngoài chi tiết; với lỗ thì "ngoài" là phần bỏ đi
 * (tức là bên trong lỗ).
 */
function leadInPoint(ring: Ring, isHole: boolean, len: number, W: number, H: number): Point {
  const a = ring[0];
  const b = ring[1 % ring.length];
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const l = Math.hypot(dx, dy) || 1;
  // pháp tuyến phải của hướng đi
  let nx = dy / l;
  let ny = -dx / l;
  let p = { x: a.x + nx * len, y: a.y + ny * len };
  const inside = pointInRing(p, ring);
  const wantInside = isHole; // với lỗ, mồi cắt nằm trong lòng lỗ (phần bỏ đi)
  if (inside !== wantInside) {
    nx = -nx;
    ny = -ny;
    p = { x: a.x + nx * len, y: a.y + ny * len };
  }
  // không được ra ngoài tấm
  if (p.x < 0 || p.y < 0 || p.x > W || p.y > H) {
    for (let k = 4; k >= 1; k--) {
      const q = { x: a.x + nx * (len * k) / 5, y: a.y + ny * (len * k) / 5 };
      if (q.x >= 0 && q.y >= 0 && q.x <= W && q.y <= H) return q;
    }
    return { x: clamp(a.x, 0, W), y: clamp(a.y, 0, H) };
  }
  return p;
}

export function generateGcode(
  sheet: SheetLayout, partsById: Map<string, Part>, opts: Partial<GcodeOptions> = {},
  extra: ExportExtras = {}
): string {
  const o: GcodeOptions = { ...DEFAULT_GCODE_OPTIONS, ...opts };
  const dec = Math.max(0, Math.min(4, o.decimals));
  const fmt = (v: number) => v.toFixed(dec);
  const kerf = Math.max(0, extra.kerf ?? 0);

  const items: CutPart[] = [];
  for (const pl of sheet.placements) {
    const part = partsById.get(pl.partId);
    if (!part) continue;
    const nominal = part.rings.map((r) => applyPlacementRing(r, pl));
    // Đường chạy mỏ = hình danh nghĩa đã bù kerf (bao ngoài nở, lỗ thu vào).
    const cut = offsetRingsForKerf(nominal, kerf);
    const rings = cut.map((ring, i) => ({ ring, isHole: i > 0 }));
    items.push({
      label: placementLabel(part, pl.instance, extra.labels),
      area: part.area,
      center: labelPoint(nominal),
      rings,
    });
  }

  // chi tiết nhỏ trước, rồi nearest-neighbor theo tâm
  items.sort((a, b) => a.area - b.area);
  const order: CutPart[] = [];
  const pool = items.slice();
  let cur: Point = { x: 0, y: 0 };
  while (pool.length) {
    let bi = 0;
    let bd = Infinity;
    for (let i = 0; i < pool.length; i++) {
      const d = Math.hypot(pool[i].center.x - cur.x, pool[i].center.y - cur.y);
      // giữ ưu tiên "nhỏ trước": phạt theo diện tích
      const score = d + (pool[i].area / 1e6) * 800;
      if (score < bd) {
        bd = score;
        bi = i;
      }
    }
    const it = pool.splice(bi, 1)[0];
    order.push(it);
    cur = it.center;
  }

  const lines: string[] = [];
  lines.push(`(XEP PHOI TON - TAM ${String(sheet.index + 1).padStart(2, '0')} - ${Math.round(sheet.width)}x${Math.round(sheet.height)}mm)`);
  lines.push('(G-CODE THAM KHAO - CHAY THU KHONG TAI TRUOC KHI CAT THAT)');
  lines.push(
    kerf > 0
      ? `(DA BU KERF ${kerf}mm TRONG FILE - PHAI TAT BU KERF BEN MAY/FASTCAM KEO BU HAI LAN)`
      : '(KHONG BU KERF - HAY BU TREN MAY HOAC FASTCAM)'
  );
  lines.push(`(SO CHI TIET: ${items.length})`);
  lines.push('G21');
  lines.push('G90');
  lines.push('G17');

  for (const it of order) {
    lines.push(`(CHI TIET ${it.label})`);
    const ordered = it.rings.slice().sort((a, b) => Number(b.isHole) - Number(a.isHole)); // lỗ trước
    for (const cr of ordered) {
      let ring = cr.ring;
      // bảo đảm mọi toạ độ nằm trong tấm
      ring = ring.map((p) => ({ x: clamp(p.x, 0, sheet.width), y: clamp(p.y, 0, sheet.height) }));
      // chiều cắt: bao ngoài CCW, lỗ CW (giữ nguyên chiều của hình gốc)
      if (cr.isHole && signedArea(ring) > 0) ring = ring.slice().reverse();
      if (!cr.isHole && signedArea(ring) < 0) ring = ring.slice().reverse();
      const start = o.leadIn > 0 ? leadInPoint(ring, cr.isHole, o.leadIn, sheet.width, sheet.height) : ring[0];
      lines.push(`G00 X${fmt(start.x)} Y${fmt(start.y)}`);
      lines.push(o.torchOn);
      lines.push(`G01 X${fmt(ring[0].x)} Y${fmt(ring[0].y)} F${o.feedRate}`);
      for (let i = 1; i < ring.length; i++) {
        lines.push(`G01 X${fmt(ring[i].x)} Y${fmt(ring[i].y)}`);
      }
      lines.push(`G01 X${fmt(ring[0].x)} Y${fmt(ring[0].y)}`);
      lines.push(o.torchOff);
    }
  }
  lines.push('G00 X0 Y0');
  lines.push('M30');

  if (o.lineNumbers) {
    let nn = 10;
    return lines.map((l) => (l.startsWith('(') ? l : `N${(nn += 10)} ${l}`)).join('\n') + '\n';
  }
  return lines.join('\n') + '\n';
}

export function gcodeFileName(sheet: SheetLayout, ext: string): string {
  const idx = String(sheet.index + 1).padStart(2, '0');
  return `tam-${idx}_${Math.round(sheet.width)}x${Math.round(sheet.height)}.${ext}`;
}
