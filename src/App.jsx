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

// ─── ICON ────────────────────────────────────────────────
function Icon({ name, className = "", filled = false, style }) {
  return (
    <span
      className={`material-symbols-outlined ${className}`}
      style={{ ...(filled ? { fontVariationSettings: "'FILL' 1" } : {}), ...style }}
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

  const TABS = [
    { id: "today", icon: "event_note", label: "Today" },
    { id: "week", icon: "analytics", label: "Week" },
    { id: "plan", icon: "auto_stories", label: "Plan" },
  ];
  const VIEW_TITLES = { today: "Today", week: "Archive", plan: "Overview" };

  return (
    <div style={{ width: "100%", maxWidth: 520, margin: "0 auto", minHeight: "100dvh", position: "relative" }}>
      {/* ─── TOP BAR ─── */}
      <header style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 50,
        background: "rgba(13,13,13,0.85)", backdropFilter: "blur(30px)",
        borderBottom: "1px solid rgba(112,128,144,0.2)"
      }}>
        <div style={{ maxWidth: 520, margin: "0 auto", display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 20px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <Icon name="menu" style={{ color: "#8fbc8f" }} />
            <h1 style={{ fontFamily: "'Crimson Pro', serif", fontSize: 18, fontWeight: 600, letterSpacing: "0.15em", textTransform: "uppercase", color: "#d2b48c" }}>
              {VIEW_TITLES[view]}
            </h1>
          </div>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 14, color: "#8fbc8f" }}>{fmtTime(now)}</span>
        </div>
      </header>

      {/* ─── CONTENT ─── */}
      <main style={{ paddingTop: 64, paddingBottom: 80, paddingLeft: 20, paddingRight: 20 }}>
        {view === "today" && <TodayView {...{ selDay, setSelDay, today, curIdx, detail, exp, setExp, isOff, hFrac, now }} />}
        {view === "week" && <WeekView {...{ setView, setSelDay, today }} />}
        {view === "plan" && <PlanView />}
      </main>

      {/* ─── BOTTOM NAV ─── */}
      <nav style={{
        position: "fixed", bottom: 0, left: 0, right: 0, zIndex: 50, height: 64,
        background: "rgba(26,28,25,0.7)", backdropFilter: "blur(24px)",
        borderTop: "1px solid rgba(112,128,144,0.2)"
      }}>
        <div style={{ maxWidth: 520, margin: "0 auto", display: "flex", justifyContent: "space-around", alignItems: "center", height: "100%", padding: "0 24px" }}>
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => { setView(tab.id); setExp(null); }}
              style={{
                display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
                padding: "6px 12px", borderRadius: 8, border: "none", cursor: "pointer",
                background: view === tab.id ? "rgba(210,180,140,0.1)" : "transparent",
                color: view === tab.id ? "#d2b48c" : "#708090",
                transform: view === tab.id ? "scale(1.1)" : "none",
                transition: "all 0.2s"
              }}
            >
              <Icon name={tab.icon} filled={view === tab.id} />
              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, textTransform: "uppercase", marginTop: 2 }}>{tab.label}</span>
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
      {/* Date */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 16, marginBottom: 12 }}>
        <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#8c9389" }}>
          {DAY_LABELS[today]}, {fmtDate(now)}
        </p>
      </div>

      {/* Day selector */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 4, marginBottom: 16 }}>
        {DAYS.map(d => {
          const sel = d === selDay;
          const isTd = d === today;
          return (
            <button
              key={d}
              onClick={() => { setSelDay(d); setExp(null); }}
              style={{
                padding: "10px 0", borderRadius: 8, cursor: "pointer",
                fontFamily: "'JetBrains Mono', monospace", fontSize: 12, fontWeight: sel ? 600 : 400,
                background: sel ? "rgba(143,188,143,0.15)" : "transparent",
                border: sel ? "1px solid rgba(143,188,143,0.4)" : isTd ? "1px solid rgba(112,128,144,0.3)" : "1px solid transparent",
                color: sel ? "#8fbc8f" : isTd ? "#e2e3dd" : "#708090",
                transition: "all 0.15s"
              }}
            >{d}</button>
          );
        })}
      </div>

      {selDay !== today && (
        <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#708090", textAlign: "center", marginBottom: 12 }}>
          Đang xem: {DAY_LABELS[selDay]}
        </p>
      )}

      {/* Timeline */}
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {DAILY_TEMPLATE.map((slot, idx) => {
          const d = detail(slot);
          const cur = idx === curIdx;
          const isExp = exp === slot.id;
          const hasExp = ["rotate", "evening", "anchor", "work1", "work2"].includes(slot.id);
          const past = selDay === today && hFrac >= slot.end;

          if (isOff && ["work1", "work2", "rotate"].includes(slot.id)) {
            if (slot.id === "work1") return (
              <div key="off" className="glass" style={{ borderRadius: 12, padding: "20px 16px", textAlign: "center", color: "#708090", fontStyle: "italic" }}>
                <Icon name="spa" style={{ color: "rgba(143,188,143,0.4)", fontSize: 28 }} />
                <p style={{ marginTop: 8 }}>Ngày nghỉ</p>
              </div>
            );
            return null;
          }

          const typeColors = {
            big: "#8fbc8f", work: "#aad8a9", small: "#d2b48c",
            life: "#708090", rotate: "#e7c79e", evening: "#b8c8da",
            anchor: "#d2b48c", off: "#708090"
          };
          const barColor = typeColors[d.type] || "#708090";

          return (
            <div
              key={slot.id}
              onClick={() => hasExp && setExp(isExp ? null : slot.id)}
              className={cur ? "glass-active" : "glass"}
              style={{
                borderRadius: 12, position: "relative", overflow: "hidden",
                cursor: hasExp ? "pointer" : "default",
                opacity: past && !cur ? 0.5 : 1,
              }}
            >
              {/* Active bar */}
              {cur && <div className="bar-glow" style={{ position: "absolute", left: 0, top: 0, bottom: 0, background: barColor, color: barColor }} />}

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 14px", paddingLeft: cur ? 18 : 14 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, flex: 1, minWidth: 0 }}>
                  <Icon name={slot.icon} style={{ fontSize: 20, color: cur ? barColor : past ? "#555" : "#708090", flexShrink: 0 }} />
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 14, fontWeight: cur ? 600 : 400, color: cur ? "#e2e3dd" : past ? "#666" : "#d0cdc5", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {d.label}
                    </div>
                    <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: past ? "#444" : "#708090", marginTop: 2 }}>
                      {hrStr(slot.start)} — {hrStr(slot.end)}
                    </div>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>
                  {(d.type === "big" || d.type === "small") && d.label !== "OFF" && (
                    <span style={{
                      fontSize: 9, fontFamily: "'JetBrains Mono', monospace", fontWeight: 600,
                      padding: "2px 6px", borderRadius: 4,
                      background: d.type === "big" ? "rgba(143,188,143,0.15)" : "rgba(210,180,140,0.15)",
                      color: d.type === "big" ? "#8fbc8f" : "#d2b48c"
                    }}>
                      {d.type === "big" ? "BIG" : "SMALL"}
                    </span>
                  )}
                  {hasExp && (
                    <Icon name="expand_more" style={{
                      fontSize: 18, color: "#708090",
                      transform: isExp ? "rotate(180deg)" : "none", transition: "transform 0.2s"
                    }} />
                  )}
                </div>
              </div>

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
    <div style={{ padding: "0 14px 14px", borderTop: "1px solid rgba(112,128,144,0.1)" }} onClick={e => e.stopPropagation()}>
      <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#708090", textTransform: "uppercase", letterSpacing: "0.1em", marginTop: 10, marginBottom: 8 }}>
        Tất cả rotating activities
      </p>
      {ALL_ROTATE.map((a, i) => {
        const isAct = a.days.split(", ").includes(selDay);
        return (
          <div key={i} style={{
            display: "flex", justifyContent: "space-between", alignItems: "center",
            padding: "8px 10px", marginBottom: 3, borderRadius: 6,
            background: isAct ? "rgba(231,199,158,0.1)" : "transparent",
            border: isAct ? "1px solid rgba(231,199,158,0.2)" : "1px solid transparent"
          }}>
            <span style={{ fontSize: 13, color: isAct ? "#e7c79e" : "#708090" }}>{isAct && "→ "}{a.label}</span>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#708090" }}>{a.days}</span>
          </div>
        );
      })}
    </div>
  );
}

function ExpandEvening({ selDay }) {
  return (
    <div style={{ padding: "0 14px 14px", borderTop: "1px solid rgba(112,128,144,0.1)" }} onClick={e => e.stopPropagation()}>
      <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#708090", textTransform: "uppercase", letterSpacing: "0.1em", marginTop: 10, marginBottom: 8 }}>
        Gợi ý — skip được nếu có lịch xã hội
      </p>
      {ALL_EVENING.map((a, i) => {
        const isAct = a.days.split(", ").includes(selDay);
        return (
          <div key={i} style={{
            display: "flex", justifyContent: "space-between", alignItems: "center",
            padding: "8px 10px", marginBottom: 3, borderRadius: 6,
            background: isAct ? "rgba(184,200,218,0.1)" : "transparent",
            border: isAct ? "1px solid rgba(184,200,218,0.2)" : "1px solid transparent"
          }}>
            <span style={{ fontSize: 13, color: isAct ? "#b8c8da" : "#708090" }}>{isAct && "→ "}{a.label}</span>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#708090" }}>{a.days}</span>
          </div>
        );
      })}
    </div>
  );
}

function ExpandAnchor() {
  return (
    <div style={{ padding: "0 14px 14px", borderTop: "1px solid rgba(112,128,144,0.1)" }} onClick={e => e.stopPropagation()}>
      <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#708090", textTransform: "uppercase", letterSpacing: "0.1em", marginTop: 10, marginBottom: 8 }}>
        Spiritual win — luôn chạy, kể cả đi nhậu về
      </p>
      {ANCHOR_STEPS.map((s, i) => (
        <div key={i} style={{
          display: "flex", justifyContent: "space-between", alignItems: "center",
          padding: "8px 10px", marginBottom: 3, borderRadius: 6,
          background: "rgba(210,180,140,0.05)", border: "1px solid rgba(210,180,140,0.1)"
        }}>
          <span style={{ fontSize: 13, color: s.required ? "#d2b48c" : "#8c9389" }}>
            {s.label}
            {s.required && <span style={{ fontSize: 9, color: "#ffb4ab", marginLeft: 8, fontFamily: "'JetBrains Mono', monospace" }}>bắt buộc</span>}
          </span>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#708090" }}>{s.duration}</span>
        </div>
      ))}
    </div>
  );
}

function ExpandWork({ id, selDay }) {
  const map = id === "work1" ? WORK1_MAP : WORK2_MAP;
  return (
    <div style={{ padding: "0 14px 14px", borderTop: "1px solid rgba(112,128,144,0.1)" }} onClick={e => e.stopPropagation()}>
      <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#708090", textTransform: "uppercase", letterSpacing: "0.1em", marginTop: 10, marginBottom: 8 }}>
        {id === "work1" ? "Peak — deep work, analytical" : "Trough — execution, routine"}
      </p>
      {DAYS.filter(d => d !== "CN").map(d => {
        const act = d === selDay;
        return (
          <div key={d} style={{
            display: "flex", justifyContent: "space-between", alignItems: "center",
            padding: "6px 10px", marginBottom: 2, borderRadius: 6,
            background: act ? "rgba(170,216,169,0.1)" : "transparent",
            border: act ? "1px solid rgba(170,216,169,0.2)" : "1px solid transparent"
          }}>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, fontWeight: 600, minWidth: 28, color: act ? "#aad8a9" : "#555" }}>{d}</span>
            <span style={{ fontSize: 12, color: act ? "#e2e3dd" : "#708090" }}>{map[d]}</span>
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
    <div style={{ marginTop: 16 }}>
      {sections.map((sec, si) => (
        <section key={si} style={{ marginBottom: 32 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <Icon name={sec.icon} style={{ color: "#d2b48c", fontSize: 20 }} />
              <h2 style={{ fontFamily: "'Crimson Pro', serif", fontSize: 22, fontWeight: 500, color: "#e2e3dd" }}>{sec.title}</h2>
            </div>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#708090" }}>{sec.time}</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {sec.data.map((it, i) => {
              const isTd = it.day === today;
              const typeColors = { big: "#8fbc8f", work: "#aad8a9", small: "#d2b48c", evening: "#b8c8da", off: "#708090" };
              const barColor = typeColors[it.type] || "#708090";
              return (
                <div
                  key={i}
                  onClick={() => { setSelDay(it.day); setView("today"); }}
                  className={isTd ? "glass-active" : "glass"}
                  style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 12px", borderRadius: 10, cursor: "pointer", position: "relative", overflow: "hidden" }}
                >
                  {isTd && <div className="bar-glow" style={{ position: "absolute", left: 0, top: 0, bottom: 0, background: barColor, color: barColor }} />}
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, fontWeight: 600, minWidth: 28, color: isTd ? barColor : "#555", paddingLeft: isTd ? 6 : 0 }}>{it.day}</span>
                  <span style={{ fontSize: 14, flex: 1, color: isTd ? "#e2e3dd" : "#999" }}>{it.label}</span>
                  {it.type === "big" && it.label !== "OFF" && (
                    <span style={{ fontSize: 8, fontFamily: "'JetBrains Mono', monospace", fontWeight: 600, padding: "2px 5px", borderRadius: 3, background: "rgba(143,188,143,0.15)", color: "#8fbc8f" }}>BIG</span>
                  )}
                  {it.type === "small" && (
                    <span style={{ fontSize: 8, fontFamily: "'JetBrains Mono', monospace", fontWeight: 600, padding: "2px 5px", borderRadius: 3, background: "rgba(210,180,140,0.15)", color: "#d2b48c" }}>SMALL</span>
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
          <p style={{ color: "#c2c9be", lineHeight: 1.6, marginBottom: 12 }}>
            Nền tảng xây trên <span style={{ color: "#e7c79e" }}>3 Daily Wins</span>:{" "}
            <span style={{ color: "#8fbc8f" }}>Physical</span> (sáng) →{" "}
            <span style={{ color: "#aad8a9" }}>Mental</span> (ngày) →{" "}
            <span style={{ color: "#d2b48c" }}>Spiritual</span> (tối)
          </p>
          <ul style={{ listStyle: "none", padding: 0 }}>
            {["Circadian: analytical sáng (peak), creative chiều (recovery)", "Big Goals = morning sacred zone", "Small Goals = rotating slots only"].map((t, i) => (
              <li key={i} style={{ display: "flex", gap: 8, fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#8c9389", marginBottom: 4 }}>
                <span style={{ color: "#8fbc8f" }}>/</span> {t}
              </li>
            ))}
          </ul>
        </div>
      )
    },
    {
      k: "bg", icon: "castle", title: "Big Goals (Mục tiêu lớn)",
      content: (
        <div>
          {["Vẽ đều (daily) — cầm bút lên là vẽ được", "Viết đều (daily) — chạm bàn phím là viết được", "Thiền đều (daily, 10-15 phút)", "Thể dục — đi bộ 10k + calisthenics 3x/tuần", "Ăn uống có kế hoạch — 1 thực đơn/tuần", "Làm việc — own projects + client"].map((g, i) => (
            <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "8px 0", borderBottom: "1px solid rgba(66,73,64,0.5)" }}>
              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 13, color: "#8fbc8f", paddingTop: 2 }}>{String(i + 1).padStart(2, "0")}</span>
              <p style={{ fontSize: 14, color: "#e2e3dd" }}>{g}</p>
            </div>
          ))}
        </div>
      )
    },
    {
      k: "sg", icon: "target", title: "Small Goals (Mục tiêu nhỏ)",
      content: (
        <div>
          {[
            { label: "Luyện Tarot lý thuyết + practice đọc bài", cat: "Rotating" },
            { label: "Luyện Chiêm tinh lý thuyết + practice đọc chart", cat: "Rotating" },
            { label: "Viết có chủ đề → bài viết (upgrade từ free write)", cat: "Upgrade" },
          ].map((g, i) => (
            <div key={i} style={{ padding: 12, borderRadius: 6, background: "rgba(26,28,25,0.6)", borderLeft: "2px solid rgba(210,180,140,0.4)", marginBottom: 8 }}>
              <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#d2b48c", textTransform: "uppercase", marginBottom: 4 }}>{g.cat}</p>
              <p style={{ fontSize: 14, color: "#c2c9be" }}>{g.label}</p>
            </div>
          ))}
        </div>
      )
    },
    {
      k: "an", icon: "bedtime", title: "Evening Anchor",
      content: (
        <div>
          <p style={{ color: "rgba(255,180,171,0.6)", fontSize: 14, fontStyle: "italic", marginBottom: 12 }}>Luôn chạy, kể cả đi nhậu về.</p>
          {ANCHOR_STEPS.map((s, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 0", borderBottom: "1px solid rgba(112,128,144,0.1)" }}>
              <div style={{ width: 6, height: 6, borderRadius: "50%", background: s.required ? "#e7c79e" : "rgba(112,128,144,0.3)", flexShrink: 0 }} />
              <span style={{ fontSize: 14, flex: 1, color: s.required ? "#e2e3dd" : "#c2c9be" }}>{s.label}</span>
              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#708090" }}>{s.duration}</span>
            </div>
          ))}
        </div>
      )
    },
    {
      k: "up", icon: "trending_up", title: "Upgrade Path",
      content: (
        <div style={{ position: "relative", marginLeft: 16, marginTop: 8 }}>
          <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 1, background: "#424940" }} />
          {[
            { when: "Streak viết stable 4-6 tuần", then: "2-3 buổi free write → viết bài", active: true },
            { when: "Groove vẽ stable", then: "30p → 45-60p (dậy sớm hơn hoặc lấy từ tối)", active: false },
            { when: "Body adapt", then: "Calisthenics 3x → 4-5x/tuần", active: false },
            { when: "Slot trống ở rotating/tối", then: "Thêm small goal. Không lấy từ morning sacred zone.", active: false },
          ].map((u, i) => (
            <div key={i} style={{ position: "relative", paddingLeft: 24, marginBottom: 20, opacity: u.active ? 1 : 0.5 }}>
              <div style={{ position: "absolute", left: -3, top: 6, width: 7, height: 7, borderRadius: "50%", background: u.active ? "#8fbc8f" : "#708090", boxShadow: `0 0 0 4px #0d0d0d` }} />
              <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#8fbc8f", textTransform: "uppercase" }}>Khi: {u.when}</p>
              <p style={{ fontSize: 14, color: "#c2c9be", marginTop: 4 }}>→ {u.then}</p>
            </div>
          ))}
        </div>
      )
    },
  ];

  return (
    <div style={{ marginTop: 16 }}>
      {/* Hero */}
      <section style={{ marginBottom: 32 }}>
        <h2 style={{ fontFamily: "'Crimson Pro', serif", fontSize: 40, fontWeight: 600, lineHeight: 1.1, letterSpacing: "-0.02em", color: "#e2e3dd", marginBottom: 8 }}>Sacred Plan</h2>
        <p style={{ color: "#c2c9be", fontStyle: "italic", fontSize: 18 }}>Architecting the quiet life through intentional ritual.</p>
      </section>

      {/* Accordion */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {sections.map(s => (
          <div key={s.k} className="glass" style={{ borderRadius: 12, overflow: "hidden" }}>
            <button
              onClick={() => setOpen(open === s.k ? null : s.k)}
              style={{
                display: "flex", justifyContent: "space-between", alignItems: "center",
                width: "100%", padding: 16, cursor: "pointer", textAlign: "left",
                background: "transparent", border: "none", color: "#e2e3dd"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <Icon name={s.icon} style={{ color: "#d2b48c" }} />
                <h3 style={{ fontFamily: "'Crimson Pro', serif", fontSize: 18, fontWeight: 500 }}>{s.title}</h3>
              </div>
              <Icon name="expand_more" style={{ color: "#708090", transform: open === s.k ? "rotate(180deg)" : "none", transition: "transform 0.2s" }} />
            </button>
            {open === s.k && (
              <div style={{ padding: "0 16px 16px", borderTop: "1px solid rgba(112,128,144,0.1)" }}>
                <div style={{ paddingTop: 12 }}>{s.content}</div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Bento cards */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 32 }}>
        <div className="glass" style={{ padding: 16, borderRadius: 12, gridColumn: "span 2" }}>
          <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#e7c79e", textTransform: "uppercase", letterSpacing: "0.15em", marginBottom: 8 }}>Core Intent</p>
          <p style={{ fontFamily: "'Crimson Pro', serif", fontSize: 24, color: "#d2b48c", fontStyle: "italic" }}>"Silence is the think-tank of the soul."</p>
        </div>
        <div className="glass" style={{ padding: 16, borderRadius: 12, display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center" }}>
          <Icon name="self_improvement" style={{ color: "#8fbc8f", fontSize: 32, marginBottom: 8 }} />
          <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#708090", textTransform: "uppercase" }}>Balance</p>
          <p style={{ fontSize: 18, color: "#e2e3dd" }}>Equanimity</p>
        </div>
        <div className="glass" style={{ padding: 16, borderRadius: 12, display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center" }}>
          <Icon name="bolt" style={{ color: "#d2b48c", fontSize: 32, marginBottom: 8 }} />
          <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#708090", textTransform: "uppercase" }}>Energy</p>
          <p style={{ fontSize: 18, color: "#e2e3dd" }}>Vitality</p>
        </div>
      </div>
    </div>
  );
}
