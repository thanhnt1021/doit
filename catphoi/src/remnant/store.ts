/**
 * Cầu nối giữa panel và API kho tôn thừa.
 *
 * Xưởng đóng tàu hay mất mạng (ngoài triền đà sóng wifi yếu), nên MỌI lời gọi
 * mạng đều bọc try/catch và có đường lui bằng localStorage:
 *  - đọc hỏng  → trả bản chép trong máy, cờ offline = true;
 *  - ghi hỏng  → ghi vào bản chép + xếp việc vào HÀNG CHỜ, lần sau có mạng thì
 *                sync() đẩy lên cho cả xưởng cùng thấy.
 * Nhờ vậy ngoài xưởng mất mạng vẫn xem và xếp được tấm thừa.
 */
import type { Remnant, RemnantInput, RemnantPatch, RemnantStatus } from './types';
import { validateRemnantInput } from './validate';
import { normalizeRemnant, normalizeMany } from './normalize';

export const CACHE_KEY = 'catphoi.remnants.cache.v1';
export const QUEUE_KEY = 'catphoi.remnants.queue.v1';
const DEFAULT_BASE = '/api/remnants';

export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

export type QueuedOp =
  | { kind: 'add'; localId: string; input: RemnantInput }
  | { kind: 'patch'; id: string; patch: RemnantPatch }
  | { kind: 'delete'; id: string };

export interface StoreDeps {
  fetchFn?: typeof fetch;
  storage?: StorageLike | null;
  now?: () => number;
  uuid?: () => string;
  baseUrl?: string;
}

export interface ListOutcome {
  remnants: Remnant[];
  /** true = không gọi được máy chủ, đang xem bản chép trong máy. */
  offline: boolean;
  /** Số việc còn nằm trong hàng chờ để đẩy lên. */
  queued: number;
  /** Câu giải thích tiếng Việt khi offline, để panel hiện lên. */
  message?: string;
}

export interface WriteOutcome<T> {
  value: T;
  offline: boolean;
  queued: number;
  message?: string;
}

/** localStorage giả, dùng khi trình duyệt chặn (chế độ riêng tư) hoặc khi chạy test. */
export function memoryStorage(): StorageLike {
  const m = new Map<string, string>();
  return {
    getItem: (k) => (m.has(k) ? (m.get(k) as string) : null),
    setItem: (k, v) => void m.set(k, v),
    removeItem: (k) => void m.delete(k),
  };
}

function safeStorage(s: StorageLike | null | undefined): StorageLike {
  if (s) return s;
  try {
    // Thử thật: chế độ riêng tư của Safari cho đọc nhưng ném lỗi khi ghi.
    const probe = '__catphoi_probe__';
    localStorage.setItem(probe, '1');
    localStorage.removeItem(probe);
    return localStorage;
  } catch {
    return memoryStorage();
  }
}

function readJson<T>(st: StorageLike, key: string, fallback: T): T {
  try {
    const raw = st.getItem(key);
    if (!raw) return fallback;
    const v = JSON.parse(raw);
    return v == null ? fallback : (v as T);
  } catch {
    return fallback;
  }
}

function writeJson(st: StorageLike, key: string, value: unknown): void {
  try {
    st.setItem(key, JSON.stringify(value));
  } catch {
    /* hết dung lượng hoặc bị chặn — thà mất bản chép còn hơn làm sập app */
  }
}

export interface RemnantStore {
  list(status?: RemnantStatus | 'all'): Promise<ListOutcome>;
  add(input: RemnantInput): Promise<WriteOutcome<Remnant>>;
  patch(id: string, patch: RemnantPatch): Promise<WriteOutcome<Remnant | null>>;
  markUsed(id: string): Promise<WriteOutcome<Remnant | null>>;
  remove(id: string): Promise<WriteOutcome<string>>;
  /** Đẩy hàng chờ lên máy chủ. Trả số việc gửi được / còn kẹt. */
  sync(): Promise<{ sent: number; left: number }>;
  cached(): Remnant[];
  queue(): QueuedOp[];
}

export function createRemnantStore(deps: StoreDeps = {}): RemnantStore {
  const st = safeStorage(deps.storage);
  const now = deps.now ?? (() => Date.now());
  const base = deps.baseUrl ?? DEFAULT_BASE;
  const doFetch: typeof fetch = deps.fetchFn
    ?? ((...a: Parameters<typeof fetch>) => fetch(...a));
  const uuid =
    deps.uuid
    ?? (() => {
      try {
        return crypto.randomUUID();
      } catch {
        return `r${now().toString(36)}${Math.random().toString(36).slice(2, 10)}`;
      }
    });

  // Bản chép trong máy có thể còn dữ liệu KIỂU CŨ (mảnh thừa rời, chưa có khổ
  // tấm gốc) — chuẩn hoá ngay lúc đọc để phần còn lại của app chỉ thấy một kiểu.
  const getCache = () => normalizeMany(readJson<unknown[]>(st, CACHE_KEY, []));
  const setCache = (v: Remnant[]) => writeJson(st, CACHE_KEY, v);
  const getQueue = () => readJson<QueuedOp[]>(st, QUEUE_KEY, []);
  const setQueue = (v: QueuedOp[]) => writeJson(st, QUEUE_KEY, v);
  const pushQueue = (op: QueuedOp) => {
    const q = getQueue();
    q.push(op);
    setQueue(q);
    return q.length;
  };

  /** Gọi API. Ném Error có câu tiếng Việt; phân biệt "mạng hỏng" với "máy chủ chê". */
  async function call<T>(path: string, init?: RequestInit): Promise<T> {
    let res: Response;
    try {
      res = await doFetch(base + path, {
        ...init,
        headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
      });
    } catch (e) {
      const err = new Error('Không nối được máy chủ.') as Error & { offline?: boolean };
      err.offline = true;
      void e;
      throw err;
    }
    let data: any = null;
    try {
      data = await res.json();
    } catch {
      data = null;
    }
    if (!res.ok || !data || data.ok !== true) {
      const msg = (data && data.error) || `Máy chủ trả lỗi ${res.status}.`;
      if (res.status >= 500) {
        const err = new Error(msg) as Error & { offline?: boolean };
        err.offline = true;
        throw err;
      }
      throw new Error(msg);
    }
    return data as T;
  }

  const isOffline = (e: unknown) => Boolean((e as { offline?: boolean })?.offline);

  async function list(status: RemnantStatus | 'all' = 'available'): Promise<ListOutcome> {
    try {
      const data = await call<{ remnants: Remnant[] }>(`?status=${encodeURIComponent(status)}`);
      const server = normalizeMany(data.remnants).map((r) => ({ ...r, pending: false }));
      // Giữ lại các tấm mới thêm lúc mất mạng, chúng chưa có trên máy chủ.
      const queuedAdds = getQueue().filter((o): o is Extract<QueuedOp, { kind: 'add' }> => o.kind === 'add');
      const localIds = new Set(queuedAdds.map((o) => o.localId));
      const keptLocal = getCache().filter((r) => localIds.has(r.id));
      const merged = [...keptLocal, ...server];
      setCache(merged);
      return { remnants: merged, offline: false, queued: getQueue().length };
    } catch (e) {
      if (!isOffline(e)) throw e;
      const cached = getCache();
      const wanted = status === 'all' ? cached : cached.filter((r) => r.status === status);
      return {
        remnants: wanted,
        offline: true,
        queued: getQueue().length,
        message: 'Mất mạng — đang xem bản lưu trong máy này. Có mạng lại sẽ tự đồng bộ.',
      };
    }
  }

  async function add(input: RemnantInput): Promise<WriteOutcome<Remnant>> {
    const bad = validateRemnantInput(input);
    if (bad) throw new Error(bad);
    const clean: RemnantInput = {
      name: input.name.trim(),
      widthMm: input.widthMm,
      lengthMm: input.lengthMm,
      // VIỆC 3: gửi kèm khổ tấm gốc + các lỗ đã cắt. Máy chủ bản cũ bỏ qua 3
      // trường này mà vẫn lưu được nhờ `polygon`, nên không sợ lệch bản.
      sheetWidthMm: input.sheetWidthMm ?? input.widthMm,
      sheetLengthMm: input.sheetLengthMm ?? input.lengthMm,
      cuts: input.cuts ?? input.polygon.slice(1),
      polygon: input.polygon,
      note: (input.note || '').trim(),
    };
    try {
      const data = await call<{ remnant: Remnant }>('', {
        method: 'POST',
        body: JSON.stringify(clean),
      });
      const r = { ...normalizeRemnant(data.remnant), pending: false };
      setCache([r, ...getCache().filter((x) => x.id !== r.id)]);
      return { value: r, offline: false, queued: getQueue().length };
    } catch (e) {
      if (!isOffline(e)) throw e;
      const t = now();
      const local: Remnant = {
        ...normalizeRemnant({ ...clean, id: `local-${uuid()}`, createdAt: t, updatedAt: t }),
        pending: true,
      };
      setCache([local, ...getCache()]);
      const queued = pushQueue({ kind: 'add', localId: local.id, input: clean });
      return {
        value: local,
        offline: true,
        queued,
        message: 'Mất mạng — đã lưu tạm trong máy này, có mạng lại sẽ tự gửi lên.',
      };
    }
  }

  function applyPatchLocal(id: string, p: RemnantPatch): Remnant | null {
    const cache = getCache();
    const i = cache.findIndex((r) => r.id === id);
    if (i < 0) return null;
    const next: Remnant = { ...cache[i], ...p, updatedAt: now() };
    cache[i] = next;
    setCache(cache);
    return next;
  }

  async function patch(id: string, p: RemnantPatch): Promise<WriteOutcome<Remnant | null>> {
    if (p.name !== undefined && !p.name.trim()) {
      throw new Error('Tên tấm thừa không được để trống.');
    }
    const body: RemnantPatch = {};
    if (p.name !== undefined) body.name = p.name.trim();
    if (p.note !== undefined) body.note = p.note.trim();
    if (p.status !== undefined) body.status = p.status;

    // Tấm còn nằm trong hàng chờ thì chưa có trên máy chủ — sửa thẳng vào hàng chờ.
    if (id.startsWith('local-')) {
      const q = getQueue();
      const op = q.find((o) => o.kind === 'add' && o.localId === id) as Extract<QueuedOp, { kind: 'add' }> | undefined;
      if (op) {
        if (body.name !== undefined) op.input.name = body.name;
        if (body.note !== undefined) op.input.note = body.note;
        setQueue(q);
        const v = applyPatchLocal(id, body);
        return { value: v, offline: true, queued: q.length };
      }
    }

    try {
      const data = await call<{ remnant: Remnant }>(`/${encodeURIComponent(id)}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      });
      const r = { ...normalizeRemnant(data.remnant), pending: false };
      const cache = getCache();
      const i = cache.findIndex((x) => x.id === id);
      if (i >= 0) cache[i] = r; else cache.unshift(r);
      setCache(cache);
      return { value: r, offline: false, queued: getQueue().length };
    } catch (e) {
      if (!isOffline(e)) throw e;
      const v = applyPatchLocal(id, body);
      const queued = pushQueue({ kind: 'patch', id, patch: body });
      return {
        value: v,
        offline: true,
        queued,
        message: 'Mất mạng — đã sửa trong máy này, có mạng lại sẽ tự gửi lên.',
      };
    }
  }

  const markUsed = (id: string) => patch(id, { status: 'used' });

  async function remove(id: string): Promise<WriteOutcome<string>> {
    const dropLocal = () => setCache(getCache().filter((r) => r.id !== id));

    if (id.startsWith('local-')) {
      const q = getQueue().filter((o) => !(o.kind === 'add' && o.localId === id));
      setQueue(q);
      dropLocal();
      return { value: id, offline: true, queued: q.length };
    }
    try {
      await call<{ deleted: string }>(`/${encodeURIComponent(id)}`, { method: 'DELETE' });
      dropLocal();
      return { value: id, offline: false, queued: getQueue().length };
    } catch (e) {
      if (!isOffline(e)) throw e;
      dropLocal();
      const queued = pushQueue({ kind: 'delete', id });
      return {
        value: id,
        offline: true,
        queued,
        message: 'Mất mạng — đã xoá trong máy này, có mạng lại sẽ tự xoá trên máy chủ.',
      };
    }
  }

  async function sync(): Promise<{ sent: number; left: number }> {
    let q = getQueue();
    let sent = 0;
    while (q.length > 0) {
      const op = q[0];
      try {
        if (op.kind === 'add') {
          const data = await call<{ remnant: Remnant }>('', {
            method: 'POST',
            body: JSON.stringify(op.input),
          });
          const real = { ...normalizeRemnant(data.remnant), pending: false };
          // Đổi mã tạm thành mã thật ở cả bản chép lẫn các việc còn lại trong hàng chờ.
          setCache(getCache().map((r) => (r.id === op.localId ? real : r)));
          for (const o of q) {
            if (o.kind === 'patch' && o.id === op.localId) o.id = real.id;
            if (o.kind === 'delete' && o.id === op.localId) o.id = real.id;
          }
        } else if (op.kind === 'patch') {
          await call(`/${encodeURIComponent(op.id)}`, { method: 'PATCH', body: JSON.stringify(op.patch) });
        } else {
          await call(`/${encodeURIComponent(op.id)}`, { method: 'DELETE' });
        }
        q.shift();
        sent++;
        setQueue(q);
      } catch (e) {
        if (isOffline(e)) break; // vẫn mất mạng — để dành lần sau
        // Máy chủ chê hẳn (404 tấm đã bị người khác xoá, dữ liệu sai...) → bỏ việc này,
        // giữ lại việc sau, chứ đứng đó thử mãi thì hàng chờ tắc vĩnh viễn.
        q.shift();
        setQueue(q);
      }
      q = getQueue();
    }
    return { sent, left: q.length };
  }

  return {
    list,
    add,
    patch,
    markUsed,
    remove,
    sync,
    cached: getCache,
    queue: getQueue,
  };
}
