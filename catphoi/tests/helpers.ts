import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

export const FIXTURE = resolve(__dirname, '../fixtures/gui-son.dxf');

export const FIXTURE_MISSING_MSG =
  'THIẾU FIXTURE: không tìm thấy catphoi/fixtures/gui-son.dxf. ' +
  'File bản vẽ thật của khách KHÔNG được commit lên repo (xem .gitignore). ' +
  'Hãy chép "Gửi Sơn.dxf" vào catphoi/fixtures/gui-son.dxf rồi chạy lại test.';

export function hasFixture(): boolean {
  return existsSync(FIXTURE);
}

export function readFixture(): string {
  return readFileSync(FIXTURE, 'utf8');
}
