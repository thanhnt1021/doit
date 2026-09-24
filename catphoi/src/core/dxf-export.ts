/**
 * Xuất DXF R12 ASCII (AC1009) — định dạng tương thích rộng nhất, AutoCAD 2007
 * và FastCAM đều đọc được.
 *
 * Layer:
 *  - CUT   : đường cắt chi tiết (POLYLINE khép kín, dùng HÌNH GỐC đã xoay/dịch)
 *  - SHEET : viền tấm tôn
 *  - LABEL : nhãn P0/P1… (tắt layer này trong FastCAM là hết nhãn)
 * Gốc toạ độ (0,0) nằm ở góc dưới-trái tấm.
 */
import type { Part, Placement, Point, Ring, SheetLayout } from '../types';
import { applyPlacementRing, ringBBox } from '../types';

const NL = '\r\n';
const DEC = 6;

function g(code: number, value: string | number): string {
  return `${code}${NL}${value}${NL}`;
}

function n(v: number): string {
  return Number(v.toFixed(DEC)).toString();
}

function header(minX: number, minY: number, maxX: number, maxY: number): string {
  return (
    g(0, 'SECTION') + g(2, 'HEADER') +
    g(9, '$ACADVER') + g(1, 'AC1009') +
    g(9, '$INSUNITS') + g(70, 4) +
    g(9, '$MEASUREMENT') + g(70, 1) +
    g(9, '$EXTMIN') + g(10, n(minX)) + g(20, n(minY)) + g(30, '0') +
    g(9, '$EXTMAX') + g(10, n(maxX)) + g(20, n(maxY)) + g(30, '0') +
    g(0, 'ENDSEC')
  );
}

function tables(): string {
  let s = g(0, 'SECTION') + g(2, 'TABLES');
  // LTYPE
  s += g(0, 'TABLE') + g(2, 'LTYPE') + g(70, 1);
  s += g(0, 'LTYPE') + g(2, 'CONTINUOUS') + g(70, 0) + g(3, 'Solid line') + g(72, 65) + g(73, 0) + g(40, '0');
  s += g(0, 'ENDTAB');
  // LAYER
  const layers: [string, number][] = [['0', 7], ['CUT', 7], ['SHEET', 5], ['LABEL', 3]];
  s += g(0, 'TABLE') + g(2, 'LAYER') + g(70, layers.length);
  for (const [name, color] of layers) {
    s += g(0, 'LAYER') + g(2, name) + g(70, 0) + g(62, color) + g(6, 'CONTINUOUS');
  }
  s += g(0, 'ENDTAB');
  s += g(0, 'ENDSEC');
  return s;
}

function polyline(ring: Ring, layer: string): string {
  let s = g(0, 'POLYLINE') + g(8, layer) + g(66, 1) + g(10, '0') + g(20, '0') + g(30, '0') + g(70, 1);
  for (const p of ring) {
    s += g(0, 'VERTEX') + g(8, layer) + g(10, n(p.x)) + g(20, n(p.y)) + g(30, '0') + g(70, 32);
  }
  s += g(0, 'SEQEND') + g(8, layer);
  return s;
}

function text(at: Point, height: number, content: string, layer: string): string {
  return (
    g(0, 'TEXT') + g(8, layer) +
    g(10, n(at.x)) + g(20, n(at.y)) + g(30, '0') +
    g(40, n(height)) + g(1, content) +
    g(72, 1) + g(73, 1) +
    g(11, n(at.x)) + g(21, n(at.y)) + g(31, '0')
  );
}

function rectRing(x0: number, y0: number, w: number, h: number): Ring {
  return [
    { x: x0, y: y0 }, { x: x0 + w, y: y0 }, { x: x0 + w, y: y0 + h }, { x: x0, y: y0 + h },
  ];
}

interface PlacedEntity {
  rings: Ring[];
  label: string;
  center: Point;
  labelHeight: number;
}

function placedEntities(
  sheet: SheetLayout, partsById: Map<string, Part>, dx: number, dy: number
): PlacedEntity[] {
  const out: PlacedEntity[] = [];
  for (const pl of sheet.placements) {
    const part = partsById.get(pl.partId);
    if (!part) continue;
    const moved: Placement = { ...pl, x: pl.x + dx, y: pl.y + dy };
    const rings = part.rings.map((r) => applyPlacementRing(r, moved));
    const b = ringBBox(rings[0]);
    const w = b.maxX - b.minX;
    const h = b.maxY - b.minY;
    out.push({
      rings,
      label: part.qty > 1 ? `${part.id}#${pl.instance + 1}` : part.id,
      center: { x: (b.minX + b.maxX) / 2, y: (b.minY + b.maxY) / 2 },
      labelHeight: Math.max(20, Math.min(80, Math.min(w, h) / 6)),
    });
  }
  return out;
}

/** Xuất 1 tấm ra DXF R12. */
export function exportSheetDxfR12(sheet: SheetLayout, partsById: Map<string, Part>): string {
  const ents = placedEntities(sheet, partsById, 0, 0);
  let body = g(0, 'SECTION') + g(2, 'ENTITIES');
  body += polyline(rectRing(0, 0, sheet.width, sheet.height), 'SHEET');
  for (const e of ents) {
    for (const r of e.rings) body += polyline(r, 'CUT');
    body += text(e.center, e.labelHeight, e.label, 'LABEL');
  }
  body += g(0, 'ENDSEC');
  return header(0, 0, sheet.width, sheet.height) + tables() + body + g(0, 'EOF');
}

/** Xuất nhiều tấm vào 1 file, các tấm đặt cạnh nhau theo trục X. */
export function exportAllSheetsDxfR12(
  sheets: SheetLayout[], partsById: Map<string, Part>, gapBetweenSheets = 200
): string {
  let body = g(0, 'SECTION') + g(2, 'ENTITIES');
  let dx = 0;
  let maxX = 0;
  let maxY = 0;
  sheets.forEach((sheet, i) => {
    body += polyline(rectRing(dx, 0, sheet.width, sheet.height), 'SHEET');
    for (const e of placedEntities(sheet, partsById, dx, 0)) {
      for (const r of e.rings) body += polyline(r, 'CUT');
      body += text(e.center, e.labelHeight, e.label, 'LABEL');
    }
    body += text(
      { x: dx + sheet.width / 2, y: sheet.height + 120 }, 150,
      `TAM ${String(i + 1).padStart(2, '0')}`, 'LABEL'
    );
    maxX = dx + sheet.width;
    maxY = Math.max(maxY, sheet.height + 300);
    dx += sheet.width + gapBetweenSheets;
  });
  body += g(0, 'ENDSEC');
  return header(0, 0, maxX, maxY) + tables() + body + g(0, 'EOF');
}

/** tam-01_2000x6000.dxf */
export function sheetFileName(sheet: SheetLayout, ext: string): string {
  const idx = String(sheet.index + 1).padStart(2, '0');
  return `tam-${idx}_${Math.round(sheet.width)}x${Math.round(sheet.height)}.${ext}`;
}
