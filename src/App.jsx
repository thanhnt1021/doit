import { useState, useEffect, useCallback } from "react";

// ─── DATA ────────────────────────────────────────────────
const DAYS = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];
const DAY_LABELS = {
  CN: "Chủ Nhật", T2: "Thứ Hai", T3: "Thứ Ba", T4: "Thứ Tư",
  T5: "Thứ Năm", T6: "Thứ Sáu", T7: "Thứ Bảy"
};

const DAILY_TEMPLATE = [
  { id: "walk", start: 5.5, end: 7, label: "Đi bộ 10k steps", type: "big", icon: "directions_walk" },
  { id: "buffer", start: 7, end: 7.75, label: "Về nhà, tắm rửa, ăn sáng", type: "life", icon: "home" },
  { id: "meditate", start: 7.75, end: 8, label: "Thiền 15 phút", type: "big", icon: "self_improvement" },
  { id: "draw", start: 8, end: 8.5, label: "Vẽ practice", type: "big", icon: "brush" },
  { id: "write", start: 8.5, end: 9, label: "Free write / Journal", type: "big", icon: "edit_note" },
  { id: "work1", start: 9, end: 12, label: "Work Block 1", type: "work", icon: "bolt" },
  { id: "lunch", start: 12, end: 13.5, label: "Nấu + ăn trưa + nghỉ", type: "life", icon: "restaurant" },
  { id: "work2", start: 13.5, end: 17, label: "Work Block 2", type: "work", icon: "terminal" },
  { id: "rotate", start: 17, end: 18, label: "Rotating Slot", type: "rotate", icon: "rebase" },
  { id: "dinner", start: 18, end: 18.5, label: "Nấu + ăn tối", type: "life", icon: "dinner_dining" },
  { id: "evening", start: 18.5, end: 20.5, label: "Buổi tối", type: "evening", icon: "nights_stay" },
  { id: "anchor", start: 20.5, end: 21, label: "Evening Anchor", type: "anchor", icon: "bedtime" },
  { id: "sleep", start: 21, end: 23, label: "Ngủ", type: "life", icon: "dark_mode" },
];

const WORK1_MAP = {
  T2: "Own project - working", T3: "Own project - working", T4: "Own project - working",
  T5: "Own project - working", T6: "Own project - working", T7: "Own / Discovering", CN: "OFF"
};
const WORK2_MAP = {
  T2: "Own project / Client", T3: "Client", T4: "Own project / Client",
  T5: "Client", T6: "Own project / Client", T7: "Meal prep + đi chợ", CN: "OFF"
};

const ROTATE_MAP = {
  T2: { label: "Calisthenics", type: "big" }, T3: { label: "Tarot - lý thuyết", type: "small" },
  T4: { label: "Calisthenics", type: "big" }, T5: { label: "Chiêm tinh - lý thuyết", type: "small" },
  T6: { label: "Calisthenics", type: "big" }, T7: { label: "Practice Tarot / Chiêm tinh", type: "small" },
  CN: { label: "OFF", type: "off" },
};

const EVENING_MAP = {
  T2: { label: "Vẽ thêm (extend practice)" }, T3: { label: "Đọc sách / xem film" },
  T4: { label: "Tự đọc Tarot cho bản thân" }, T5: { label: "Đọc sách / input chiêm tinh" },
  T6: { label: "Free - xã hội, nghỉ ngơi" }, T7: { label: "Free - xã hội, nghỉ ngơi" },
  CN: { label: "Review tuần 30p + plan tuần mới" },
};

const ANCHOR_STEPS = [
  { label: "Gratitude - 3 điều tốt trong ngày", duration: "5p", required: true },
  { label: "Đọc sách (không phone)", duration: "15-20p", required: false },
  { label: "Wind down - thở, chuẩn bị ngủ", duration: "5p", required: false },
];

const ALL_ROTATE = [
  { label: "Calisthenics", days: "T2, T4, T6", type: "big" },
  { label: "Tarot - đọc lý thuyết", days: "T3", type: "small" },
  { label: "Chiêm tinh - đọc lý thuyết", days: "T5", type: "small" },
  { label: "Practice đọc Tarot / chart", days: "T7", type: "small" },
];

const ALL_EVENING = [
  { label: "Vẽ thêm (extend practice)", days: "T2" },
  { label: "Đọc sách / xem film", days: "T3, T5" },
  { label: "Tự đọc Tarot cho bản thân", days: "T4" },
  { label: "Free - xã hội, nghỉ", days: "T6, T7" },
  { label: "Review tuần + plan tuần mới", days: "CN" },
];

// ─── UTILS ───────────────────────────────────────────────
function getVNDay(d) { return DAYS[d.getDay()]; }
function fmtDate(d) {
  return `${d.getDate().toString().padStart(2, "0")}/${(d.getMonth() + 1).toString().padStart(2, "0")}/${d.getFullYear()}`;
}
function fmtTime(d) { return d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", hour12: false }); }
function hrStr(h) {
  const hr = Math.floor(h), mn = Math.round((h - hr) * 60);
  return `${hr.toString().padStart(2, "0")}:${mn.toString().padStart(2, "0")}`;
}
function getCurSlot(now) {
  const h = now.getHours() + now.getMinutes() / 60;
  for (let i = 0; i < DAILY_TEMPLATE.length; i++) if (h >= DAILY_TEMPLATE[i].start && h < DAILY_TEMPLATE[i].end) return i;
  return -1;
}

// ─── SLOT COLORS ─────────────────────────────────────────
const SLOT_COLORS = {
  big:     { bar: "text-sage",    bg: "bg-sage/10",    border: "border-sage/30",    badge: "bg-sage/20 text-sage" },
  work:    { bar: "text-primary", bg: "bg-primary/10", border: "border-primary/30", badge: "bg-primary/20 text-primary" },
  small:   { bar: "text-tan",     bg: "bg-tan/10",     border: "border-tan/30",     badge: "bg-tan/20 text-tan" },
  life:    { bar: "text-slate",   bg: "bg-slate/5",    border: "border-slate/20",   badge: "" },
  rotate:  { bar: "text-tertiary",bg: "bg-tertiary/10",border: "border-tertiary/30",badge: "bg-tertiary/20 text-tertiary" },
  evening: { bar: "text-secondary",bg:"bg-secondary/10",border:"border-secondary/30",badge: "" },
  anchor:  { bar: "text-tan",     bg: "bg-tan/10",     border: "border-tan/30",     badge: "" },
  off:     { bar: "text-slate",   bg: "bg-slate/5",    border: "border-slate/10",   badge: "" },
};

// ─── ICON COMPONENT ──────────────────────────────────────
function Icon({ name, className = "", filled = false }) {
  return (
    <span
      className={`material-symbols-outlined ${className}`}
      style={filled ? { fontVariationSettings: "'FILL' 1" } : undefined}
    >{name}</span>
  );
}

// ─── MAIN APP ────────────────────────────────────────────
export default function App() {
  const [now, setNow] = useState(new Date());
  const [selDay, setSelDay] = useState(getVNDay(new Date()));
  const [view, setView] = useState("today");
  const [exp, setExp] = useState(null);

  useEffect(() => { const iv = setInterval(() => setNow(new Date()), 30000); return () => clearInterval(iv); }, []);

  const today = getVNDay(now);
  const curIdx = selDay === today ? getCurSlot(now) : -1;
  const isOff = selDay === "CN";
  const hFrac = now.getHours() + now.getMinutes() / 60;

  const detail = useCallback((s) => {
    if (s.id === "work1") return { ...s, label: isOff ? "OFF" : WORK1_MAP[selDay] };
    if (s.id === "work2") return { ...s, label: isOff ? "OFF" : WORK2_MAP[selDay] };
    if (s.id === "rotate") { const r = ROTATE_MAP[selDay]; return { ...s, label: r.label === "OFF" ? "OFF" : r.label, type: r.type }; }
    if (s.id === "evening") return { ...s, label: EVENING_MAP[selDay].label };
    return s;
  }, [selDay, isOff]);

  const VIEW_TITLES = { today: "Today", week: "Archive", plan: "Overview" };
  const VIEW_ICONS = { today: "event_note", week: "analytics", plan: "auto_stories" };

  return (
    <div className="min-h-dvh max-w-lg mx-auto relative">
      {/* ─── TOP APP BAR ─── */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-bg/80 backdrop-blur-3xl border-b border-slate/30">
        <div className="max-w-lg mx-auto flex justify-between items-center px-6 py-4">
          <div className="flex items-center gap-4">
            <Icon name="menu" className="text-sage cursor-pointer" />
            <h1 className="font-display text-xl uppercase tracking-widest text-tan">
              {VIEW_TITLES[view]}
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-mono text-sm text-sage">{fmtTime(now)}</span>
          </div>
        </div>
      </header>

      {/* ─── MAIN CONTENT ─── */}
      <main className="pt-[72px] pb-24 px-6">
        {view === "today" && <TodayView {...{ selDay, setSelDay, today, curIdx, detail, exp, setExp, isOff, hFrac, now }} />}
        {view === "week" && <WeekView {...{ setView, setSelDay, today }} />}
        {view === "plan" && <PlanView />}
      </main>

      {/* ─── BOTTOM NAV ─── */}
      <nav className="fixed bottom-0 left-0 right-0 z-50 h-16 bg-surface-container/60 backdrop-blur-2xl border-t border-slate/30">
        <div className="max-w-lg mx-auto flex justify-around items-center h-full px-6">
          {[
            { id: "today", icon: "event_note", label: "Today" },
            { id: "week", icon: "analytics", label: "Week" },
            { id: "plan", icon: "auto_stories", label: "Plan" },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => { setView(tab.id); setExp(null); }}
              className={`flex flex-col items-center justify-center p-2 rounded-lg transition-all ${
                view === tab.id
                  ? "text-tan scale-110 drop-shadow-[0_0_8px_rgba(143,188,143,0.4)]"
                  : "text-slate hover:bg-tan/10"
              }`}
            >
              <Icon name={tab.icon} filled={view === tab.id} />
              <span className="font-mono text-[10px] uppercase mt-0.5">{tab.label}</span>
            </button>
          ))}
        </div>
      </nav>
    </div>
  );
}

// ─── TODAY VIEW ──────────────────────────────────────────
function TodayView({ selDay, setSelDay, today, curIdx, detail, exp, setExp, isOff, hFrac, now }) {
  return (
    <>
      {/* Date subtitle */}
      <p className="font-mono text-xs text-slate mt-6 mb-2">
        {DAY_LABELS[today]}, {fmtDate(now)}
      </p>

      {/* Day selector */}
      <div className="grid grid-cols-7 gap-1 mb-6">
        {DAYS.map(d => (
          <button
            key={d}
            onClick={() => { setSelDay(d); setExp(null); }}
            className={`py-2.5 rounded-lg font-mono text-xs transition-all ${
              d === selDay
                ? "glass-card text-sage font-semibold border-sage/40"
                : d === today
                  ? "text-on-surface border border-slate/20 rounded-lg"
                  : "text-slate hover:text-on-surface-variant"
            }`}
          >
            {d}
          </button>
        ))}
      </div>

      {selDay !== today && (
        <p className="font-mono text-xs text-slate text-center mb-4">
          Đang xem: {DAY_LABELS[selDay]}
        </p>
      )}

      {/* Timeline */}
      <div className="flex flex-col gap-1.5">
        {DAILY_TEMPLATE.map((slot, idx) => {
          const d = detail(slot);
          const cur = idx === curIdx;
          const isExp = exp === slot.id;
          const hasExp = ["rotate", "evening", "anchor", "work1", "work2"].includes(slot.id);
          const sc = SLOT_COLORS[d.type] || SLOT_COLORS.life;
          const past = selDay === today && hFrac >= slot.end;

          if (isOff && ["work1", "work2", "rotate"].includes(slot.id)) {
            if (slot.id === "work1") return (
              <div key="off" className="glass-card rounded-xl p-5 text-center text-slate italic">
                <Icon name="spa" className="text-sage/40 text-2xl" />
                <p className="mt-2">Ngày nghỉ</p>
              </div>
            );
            return null;
          }

          return (
            <div
              key={slot.id}
              onClick={() => hasExp && setExp(isExp ? null : slot.id)}
              className={`rounded-xl relative overflow-hidden transition-all ${
                hasExp ? "cursor-pointer" : ""
              } ${cur
                ? `glass-card ${sc.border} border`
                : past
                  ? "bg-surface/40 opacity-40"
                  : "glass-card"
              }`}
            >
              {/* Active bar */}
              {cur && <div className={`absolute left-0 top-0 bottom-0 slot-active-bar ${sc.bar}`} />}

              <div className="flex justify-between items-center p-3.5 pl-4">
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <Icon name={slot.icon} className={`text-lg ${cur ? sc.bar : past ? "text-slate/40" : "text-slate"}`} />
                  <div className="min-w-0">
                    <div className={`text-sm truncate ${cur ? "font-semibold text-on-surface" : past ? "text-slate" : "text-on-surface/90"}`}>
                      {d.label}
                    </div>
                    <div className={`font-mono text-[10px] mt-0.5 ${past ? "text-slate/30" : "text-slate"}`}>
                      {hrStr(slot.start)} — {hrStr(slot.end)}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {(d.type === "big" || d.type === "small") && d.label !== "OFF" && (
                    <span className={`text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded ${sc.badge}`}>
                      {d.type === "big" ? "BIG" : "SMALL"}
                    </span>
                  )}
                  {hasExp && (
                    <Icon
                      name="expand_more"
                      className={`text-slate text-lg transition-transform ${isExp ? "rotate-180" : ""}`}
                    />
                  )}
                </div>
              </div>

              {/* Expanded content */}
              {isExp && slot.id === "rotate" && <ExpandRotate selDay={selDay} />}
              {isExp && slot.id === "evening" && <ExpandEvening selDay={selDay} />}
              {isExp && slot.id === "anchor" && <ExpandAnchor />}
              {isExp && (slot.id === "work1" || slot.id === "work2") && !isOff && <ExpandWork id={slot.id} selDay={selDay} />}
            </div>
          );
        })}
      </div>
    </>
  );
}

// ─── EXPAND PANELS ───────────────────────────────────────
function ExpandRotate({ selDay }) {
  return (
    <div className="px-4 pb-4 border-t border-slate/10" onClick={e => e.stopPropagation()}>
      <p className="font-mono text-[10px] text-slate uppercase tracking-widest mt-3 mb-2">
        Tất cả rotating activities
      </p>
      {ALL_ROTATE.map((a, i) => {
        const isAct = a.days.split(", ").includes(selDay);
        return (
          <div key={i} className={`flex justify-between items-center py-2 px-3 rounded-lg mb-1 ${isAct ? "bg-tertiary/10 border border-tertiary/20" : ""}`}>
            <span className={`text-sm ${isAct ? "text-tertiary" : "text-slate"}`}>
              {isAct && "→ "}{a.label}
            </span>
            <span className="font-mono text-[10px] text-slate">{a.days}</span>
          </div>
        );
      })}
    </div>
  );
}

function ExpandEvening({ selDay }) {
  return (
    <div className="px-4 pb-4 border-t border-slate/10" onClick={e => e.stopPropagation()}>
      <p className="font-mono text-[10px] text-slate uppercase tracking-widest mt-3 mb-2">
        Gợi ý — skip được nếu có lịch xã hội
      </p>
      {ALL_EVENING.map((a, i) => {
        const isAct = a.days.split(", ").includes(selDay);
        return (
          <div key={i} className={`flex justify-between items-center py-2 px-3 rounded-lg mb-1 ${isAct ? "bg-secondary/10 border border-secondary/20" : ""}`}>
            <span className={`text-sm ${isAct ? "text-secondary" : "text-slate"}`}>
              {isAct && "→ "}{a.label}
            </span>
            <span className="font-mono text-[10px] text-slate">{a.days}</span>
          </div>
        );
      })}
    </div>
  );
}

function ExpandAnchor() {
  return (
    <div className="px-4 pb-4 border-t border-slate/10" onClick={e => e.stopPropagation()}>
      <p className="font-mono text-[10px] text-slate uppercase tracking-widest mt-3 mb-2">
        Spiritual win — luôn chạy, kể cả đi nhậu về
      </p>
      {ANCHOR_STEPS.map((s, i) => (
        <div key={i} className="flex justify-between items-center py-2 px-3 rounded-lg mb-1 bg-tan/5 border border-tan/10">
          <span className={`text-sm ${s.required ? "text-tan" : "text-slate"}`}>
            {s.label}
            {s.required && <span className="text-[9px] text-error ml-2 font-mono">bắt buộc</span>}
          </span>
          <span className="font-mono text-[10px] text-slate">{s.duration}</span>
        </div>
      ))}
    </div>
  );
}

function ExpandWork({ id, selDay }) {
  const map = id === "work1" ? WORK1_MAP : WORK2_MAP;
  return (
    <div className="px-4 pb-4 border-t border-slate/10" onClick={e => e.stopPropagation()}>
      <p className="font-mono text-[10px] text-slate uppercase tracking-widest mt-3 mb-2">
        {id === "work1" ? "Peak — deep work, analytical" : "Trough — execution, routine"}
      </p>
      {DAYS.filter(d => d !== "CN").map(d => {
        const act = d === selDay;
        return (
          <div key={d} className={`flex justify-between items-center py-2 px-3 rounded-lg mb-1 ${act ? "bg-primary/10 border border-primary/20" : ""}`}>
            <span className={`font-mono text-xs font-semibold min-w-[28px] ${act ? "text-primary" : "text-slate/40"}`}>{d}</span>
            <span className={`text-sm ${act ? "text-on-surface" : "text-slate"}`}>{map[d]}</span>
          </div>
        );
      })}
    </div>
  );
}

// ─── WEEK VIEW ───────────────────────────────────────────
function WeekView({ setView, setSelDay, today }) {
  const sections = [
    { title: "Rotating", time: "17:00 — 18:00", icon: "rebase", data: DAYS.map(d => ({ day: d, label: ROTATE_MAP[d].label, type: ROTATE_MAP[d].type })) },
    { title: "Work Block 1", time: "09:00 — 12:00", icon: "bolt", data: DAYS.map(d => ({ day: d, label: WORK1_MAP[d], type: "work" })) },
    { title: "Work Block 2", time: "13:30 — 17:00", icon: "terminal", data: DAYS.map(d => ({ day: d, label: WORK2_MAP[d], type: "work" })) },
    { title: "Evening", time: "18:30 — 20:30", icon: "nights_stay", data: DAYS.map(d => ({ day: d, label: EVENING_MAP[d].label, type: "evening" })) },
  ];

  return (
    <div className="mt-6">
      {sections.map((sec, si) => (
        <section key={si} className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <Icon name={sec.icon} className="text-tan text-xl" />
              <h2 className="font-display text-xl text-on-surface">{sec.title}</h2>
            </div>
            <span className="font-mono text-xs text-slate">{sec.time}</span>
          </div>

          <div className="space-y-1.5">
            {sec.data.map((it, i) => {
              const isTd = it.day === today;
              const sc = SLOT_COLORS[it.type] || SLOT_COLORS.life;
              return (
                <div
                  key={i}
                  onClick={() => { setSelDay(it.day); setView("today"); }}
                  className={`flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all ${
                    isTd
                      ? `glass-card ${sc.border} border relative overflow-hidden`
                      : "glass-card hover:bg-surface-container-high/40"
                  }`}
                >
                  {isTd && <div className={`absolute left-0 top-0 bottom-0 slot-active-bar ${sc.bar}`} />}
                  <span className={`font-mono text-xs font-semibold min-w-[28px] ${isTd ? sc.bar : "text-slate/40"}`}>
                    {it.day}
                  </span>
                  <span className={`text-sm flex-1 ${isTd ? "text-on-surface" : "text-on-surface-variant"}`}>
                    {it.label}
                  </span>
                  {it.type === "big" && it.label !== "OFF" && (
                    <span className={`text-[8px] font-mono font-semibold px-1.5 py-0.5 rounded ${sc.badge}`}>BIG</span>
                  )}
                  {it.type === "small" && (
                    <span className={`text-[8px] font-mono font-semibold px-1.5 py-0.5 rounded ${SLOT_COLORS.small.badge}`}>SMALL</span>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}

// ─── PLAN VIEW ───────────────────────────────────────────
function PlanView() {
  const [open, setOpen] = useState(null);

  const sections = [
    {
      k: "ph", icon: "auto_stories", title: "Philosophy (Triết lý)",
      content: (
        <div>
          <p className="text-on-surface-variant leading-relaxed mb-3">
            Nền tảng xây trên <span className="text-tertiary">3 Daily Wins</span>:{" "}
            <span className="text-sage">Physical</span> (sáng) →{" "}
            <span className="text-primary">Mental</span> (ngày) →{" "}
            <span className="text-tan">Spiritual</span> (tối)
          </p>
          <ul className="space-y-1 font-mono text-xs text-slate">
            <li className="flex gap-2"><span className="text-sage">/</span> Circadian: analytical sáng (peak), creative chiều (recovery)</li>
            <li className="flex gap-2"><span className="text-sage">/</span> Big Goals = morning sacred zone</li>
            <li className="flex gap-2"><span className="text-sage">/</span> Small Goals = rotating slots only</li>
          </ul>
        </div>
      )
    },
    {
      k: "bg", icon: "castle", title: "Big Goals (Mục tiêu lớn)",
      content: (
        <div className="space-y-3">
          {[
            "Vẽ đều (daily) — cầm bút lên là vẽ được",
            "Viết đều (daily) — chạm bàn phím là viết được",
            "Thiền đều (daily, 10-15 phút)",
            "Thể dục — đi bộ 10k + calisthenics 3x/tuần",
            "Ăn uống có kế hoạch — 1 thực đơn/tuần",
            "Làm việc — own projects + client",
          ].map((g, i) => (
            <div key={i} className="flex items-start gap-3">
              <span className="font-mono text-sm text-sage pt-0.5">{String(i + 1).padStart(2, "0")}</span>
              <p className="text-on-surface text-sm">{g}</p>
            </div>
          ))}
        </div>
      )
    },
    {
      k: "sg", icon: "target", title: "Small Goals (Mục tiêu nhỏ)",
      content: (
        <div className="space-y-2">
          {[
            { label: "Luyện Tarot lý thuyết + practice đọc bài", cat: "Rotating" },
            { label: "Luyện Chiêm tinh lý thuyết + practice đọc chart", cat: "Rotating" },
            { label: "Viết có chủ đề → bài viết (upgrade từ free write)", cat: "Upgrade" },
          ].map((g, i) => (
            <div key={i} className="p-3 rounded-lg bg-surface-container-low border-l-2 border-tan/40">
              <p className="font-mono text-[10px] text-tan uppercase mb-0.5">{g.cat}</p>
              <p className="text-on-surface-variant text-sm">{g.label}</p>
            </div>
          ))}
        </div>
      )
    },
    {
      k: "an", icon: "bedtime", title: "Evening Anchor",
      content: (
        <div>
          <p className="text-error/60 text-sm italic mb-3">Luôn chạy, kể cả đi nhậu về.</p>
          {ANCHOR_STEPS.map((s, i) => (
            <div key={i} className="flex items-center gap-3 py-2.5 border-b border-slate/10">
              <div className={`w-2 h-2 rounded-full ${s.required ? "bg-tertiary" : "bg-slate/30"}`} />
              <span className={`text-sm flex-1 ${s.required ? "text-on-surface" : "text-on-surface-variant"}`}>{s.label}</span>
              <span className="font-mono text-[10px] text-slate">{s.duration}</span>
            </div>
          ))}
        </div>
      )
    },
    {
      k: "up", icon: "trending_up", title: "Upgrade Path",
      content: (
        <div className="relative ml-4 mt-2">
          <div className="absolute left-0 top-0 bottom-0 w-px bg-outline-variant" />
          <div className="space-y-5">
            {[
              { when: "Streak viết stable 4-6 tuần", then: "2-3 buổi free write → viết bài", active: true },
              { when: "Groove vẽ stable", then: "30p → 45-60p (dậy sớm hơn hoặc lấy từ tối)", active: false },
              { when: "Body adapt", then: "Calisthenics 3x → 4-5x/tuần", active: false },
              { when: "Slot trống ở rotating/tối", then: "Thêm small goal. Không lấy từ morning sacred zone.", active: false },
            ].map((u, i) => (
              <div key={i} className={`relative pl-6 ${u.active ? "" : "opacity-50"}`}>
                <div className={`absolute left-[-3px] top-1.5 w-1.5 h-1.5 rounded-full ring-4 ring-bg ${u.active ? "bg-sage" : "bg-slate"}`} />
                <p className="font-mono text-xs text-sage uppercase">Khi: {u.when}</p>
                <p className="text-on-surface-variant text-sm mt-1">→ {u.then}</p>
              </div>
            ))}
          </div>
        </div>
      )
    },
  ];

  return (
    <div className="mt-6">
      {/* Hero */}
      <section className="mb-8">
        <h2 className="font-display text-[40px] leading-[1.1] tracking-tight text-on-surface mb-2">Sacred Plan</h2>
        <p className="text-on-surface-variant italic">Architecting the quiet life through intentional ritual.</p>
      </section>

      {/* Accordion */}
      <div className="space-y-2">
        {sections.map(s => (
          <div key={s.k} className="glass-card rounded-xl overflow-hidden">
            <button
              onClick={() => setOpen(open === s.k ? null : s.k)}
              className="flex justify-between items-center w-full p-4 cursor-pointer text-left"
            >
              <div className="flex items-center gap-3">
                <Icon name={s.icon} className="text-tan" />
                <h3 className="font-display text-lg text-on-surface">{s.title}</h3>
              </div>
              <Icon
                name="expand_more"
                className={`text-slate transition-transform ${open === s.k ? "rotate-180" : ""}`}
              />
            </button>
            {open === s.k && (
              <div className="px-4 pb-4 border-t border-slate/10 pt-3">
                {s.content}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Bento cards */}
      <div className="mt-8 grid grid-cols-2 gap-3">
        <div className="glass-card p-4 rounded-xl col-span-2">
          <p className="font-mono text-[10px] text-tertiary uppercase tracking-widest mb-2">Core Intent</p>
          <p className="font-display text-2xl text-tan italic">"Silence is the think-tank of the soul."</p>
        </div>
        <div className="glass-card p-4 rounded-xl flex flex-col justify-center items-center text-center">
          <Icon name="self_improvement" className="text-sage text-3xl mb-2" />
          <p className="font-mono text-[10px] text-slate uppercase">Balance</p>
          <p className="text-lg text-on-surface">Equanimity</p>
        </div>
        <div className="glass-card p-4 rounded-xl flex flex-col justify-center items-center text-center">
          <Icon name="bolt" className="text-tan text-3xl mb-2" />
          <p className="font-mono text-[10px] text-slate uppercase">Energy</p>
          <p className="text-lg text-on-surface">Vitality</p>
        </div>
      </div>
    </div>
  );
}
