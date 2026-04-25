import { useState, useEffect, useCallback } from "react";

const DAYS = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];
const DAY_LABELS = {
  CN: "Chủ Nhật", T2: "Thứ Hai", T3: "Thứ Ba", T4: "Thứ Tư",
  T5: "Thứ Năm", T6: "Thứ Sáu", T7: "Thứ Bảy"
};

const DAILY_TEMPLATE = [
  { id: "walk", start: 5.5, end: 7, label: "Đi bộ 10k steps", type: "big", icon: "🚶" },
  { id: "buffer", start: 7, end: 7.75, label: "Về nhà, tắm rửa, ăn sáng", type: "life", icon: "🏠" },
  { id: "meditate", start: 7.75, end: 8, label: "Thiền 15 phút", type: "big", icon: "🧘" },
  { id: "draw", start: 8, end: 8.5, label: "Vẽ practice", type: "big", icon: "✏️" },
  { id: "write", start: 8.5, end: 9, label: "Free write / Journal", type: "big", icon: "📝" },
  { id: "work1", start: 9, end: 12, label: "Work Block 1", type: "work", icon: "⚡" },
  { id: "lunch", start: 12, end: 13.5, label: "Nấu + ăn trưa + nghỉ", type: "life", icon: "🍜" },
  { id: "work2", start: 13.5, end: 17, label: "Work Block 2", type: "work", icon: "💻" },
  { id: "rotate", start: 17, end: 18, label: "Rotating Slot", type: "rotate", icon: "🔄" },
  { id: "dinner", start: 18, end: 18.5, label: "Nấu + ăn tối", type: "life", icon: "🍽️" },
  { id: "evening", start: 18.5, end: 20.5, label: "Buổi tối", type: "evening", icon: "🌙" },
  { id: "anchor", start: 20.5, end: 21, label: "Evening Anchor", type: "anchor", icon: "✨" },
  { id: "sleep", start: 21, end: 23, label: "Ngủ", type: "life", icon: "😴" },
];

const WORK1_MAP = {
  T2: "Own project - working", T3: "Own project - working", T4: "Own project - working",
  T5: "Own project - working", T6: "Own project - working", T7: "Own / Discovering",
  CN: "OFF"
};
const WORK2_MAP = {
  T2: "Own project / Client", T3: "Client", T4: "Own project / Client",
  T5: "Client", T6: "Own project / Client", T7: "Meal prep + đi chợ",
  CN: "OFF"
};

const ROTATE_MAP = {
  T2: { label: "Calisthenics", type: "big" },
  T3: { label: "Tarot - lý thuyết", type: "small" },
  T4: { label: "Calisthenics", type: "big" },
  T5: { label: "Chiêm tinh - lý thuyết", type: "small" },
  T6: { label: "Calisthenics", type: "big" },
  T7: { label: "Practice Tarot / Chiêm tinh", type: "small" },
  CN: { label: "OFF", type: "off" },
};

const EVENING_MAP = {
  T2: { label: "Vẽ thêm (extend practice)" },
  T3: { label: "Đọc sách / xem film" },
  T4: { label: "Tự đọc Tarot cho bản thân" },
  T5: { label: "Đọc sách / input chiêm tinh" },
  T6: { label: "Free - xã hội, nghỉ ngơi" },
  T7: { label: "Free - xã hội, nghỉ ngơi" },
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

function getVNDay(d) { return DAYS[d.getDay()]; }
function fmtDate(d) {
  return `${d.getDate().toString().padStart(2,"0")}/${(d.getMonth()+1).toString().padStart(2,"0")}/${d.getFullYear()}`;
}
function fmtTime(d) { return d.toLocaleTimeString("vi-VN",{hour:"2-digit",minute:"2-digit",hour12:false}); }
function hrStr(h) {
  const hr=Math.floor(h), mn=Math.round((h-hr)*60);
  return `${hr.toString().padStart(2,"0")}:${mn.toString().padStart(2,"0")}`;
}
function getCurSlot(now) {
  const h=now.getHours()+now.getMinutes()/60;
  for(let i=0;i<DAILY_TEMPLATE.length;i++) if(h>=DAILY_TEMPLATE[i].start&&h<DAILY_TEMPLATE[i].end) return i;
  return -1;
}

const C = {
  big:    {bg:"#1a2f1a",br:"#2d5a2d",tx:"#8fbc8f",bd:"#2d5a2d",bt:"#c8e6c8"},
  work:   {bg:"#1a1a2f",br:"#2d2d5a",tx:"#8f8fbc",bd:"#2d2d5a",bt:"#c8c8e6"},
  small:  {bg:"#2f2a1a",br:"#5a4d2d",tx:"#bcb08f",bd:"#5a4d2d",bt:"#e6dcc8"},
  life:   {bg:"#1a1a1a",br:"#333",tx:"#888",bd:"#333",bt:"#aaa"},
  rotate: {bg:"#2f1a2a",br:"#5a2d4d",tx:"#bc8fb0",bd:"#5a2d4d",bt:"#e6c8dc"},
  evening:{bg:"#1a2a2f",br:"#2d4d5a",tx:"#8fb0bc",bd:"#2d4d5a",bt:"#c8dce6"},
  anchor: {bg:"#2f2f1a",br:"#5a5a2d",tx:"#bcbc8f",bd:"#5a5a2d",bt:"#e6e6c8"},
  off:    {bg:"#1a1a1a",br:"#333",tx:"#666",bd:"#333",bt:"#888"},
};

export default function App() {
  const [now, setNow] = useState(new Date());
  const [selDay, setSelDay] = useState(getVNDay(new Date()));
  const [view, setView] = useState("today");
  const [exp, setExp] = useState(null);

  useEffect(() => { const iv=setInterval(()=>setNow(new Date()),30000); return ()=>clearInterval(iv); }, []);

  const today = getVNDay(now);
  const curIdx = selDay===today ? getCurSlot(now) : -1;
  const isOff = selDay==="CN";
  const hFrac = now.getHours()+now.getMinutes()/60;

  const detail = useCallback((s) => {
    if(s.id==="work1") return {...s, label: isOff?"OFF":WORK1_MAP[selDay]};
    if(s.id==="work2") return {...s, label: isOff?"OFF":WORK2_MAP[selDay]};
    if(s.id==="rotate"){const r=ROTATE_MAP[selDay]; return {...s,label:r.label==="OFF"?"OFF":r.label,type:r.type};}
    if(s.id==="evening") return {...s, label:EVENING_MAP[selDay].label};
    return s;
  }, [selDay, isOff]);

  return (
    <div style={{fontFamily:"'Crimson Pro',Georgia,serif",background:"#0d0d0d",color:"#e0ddd5",minHeight:"100vh",maxWidth:520,margin:"0 auto"}}>
      <link href="https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@300;400;600;700&family=JetBrains+Mono:wght@300;400&display=swap" rel="stylesheet"/>

      <div style={{padding:"24px 20px 0",borderBottom:"1px solid #222"}}>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"baseline"}}>
          <h1 style={{fontSize:26,fontWeight:700,margin:0,color:"#f0ece4",letterSpacing:"-0.5px"}}>Weekly Life</h1>
          <span style={{fontFamily:"'JetBrains Mono',monospace",fontSize:13,color:"#8fbc8f"}}>{fmtTime(now)}</span>
        </div>
        <p style={{fontFamily:"'JetBrains Mono',monospace",fontSize:12,color:"#555",margin:"4px 0 14px"}}>
          {DAY_LABELS[today]}, {fmtDate(now)}
        </p>
        <div style={{display:"flex"}}>
          {["today","week","plan"].map(t=>(
            <button key={t} onClick={()=>{setView(t);setExp(null);}} style={{
              flex:1,padding:"10px 0 12px",background:"none",border:"none",
              borderBottom:view===t?"2px solid #8fbc8f":"2px solid transparent",
              color:view===t?"#f0ece4":"#555",fontFamily:"'Crimson Pro',serif",
              fontSize:15,fontWeight:view===t?600:400,cursor:"pointer"
            }}>
              {t==="today"?"Hôm nay":t==="week"?"Tuần":"Tổng quan"}
            </button>
          ))}
        </div>
      </div>

      <div style={{padding:"0 20px 40px"}}>
        {view==="today"&&<Today {...{selDay,setSelDay,today,curIdx,detail,exp,setExp,isOff,hFrac}}/>}
        {view==="week"&&<Week {...{setView,setSelDay,today}}/>}
        {view==="plan"&&<Plan/>}
      </div>
    </div>
  );
}

function Today({selDay,setSelDay,today,curIdx,detail,exp,setExp,isOff,hFrac}) {
  return <>
    <div style={{display:"flex",gap:4,margin:"16px 0",justifyContent:"space-between"}}>
      {DAYS.map(d=>(
        <button key={d} onClick={()=>{setSelDay(d);setExp(null);}} style={{
          flex:1,padding:"8px 0",background:d===selDay?"#1a2f1a":"transparent",
          border:d===today&&d!==selDay?"1px solid #333":d===selDay?"1px solid #2d5a2d":"1px solid transparent",
          borderRadius:6,color:d===selDay?"#8fbc8f":d===today?"#e0ddd5":"#555",
          fontFamily:"'JetBrains Mono',monospace",fontSize:12,fontWeight:d===selDay?600:400,cursor:"pointer"
        }}>{d}</button>
      ))}
    </div>

    {selDay!==today&&<p style={{fontFamily:"'JetBrains Mono',monospace",fontSize:11,color:"#555",margin:"0 0 8px",textAlign:"center"}}>
      Đang xem: {DAY_LABELS[selDay]}
    </p>}

    <div style={{display:"flex",flexDirection:"column",gap:3}}>
      {DAILY_TEMPLATE.map((slot,idx)=>{
        const d=detail(slot);
        const cur=idx===curIdx;
        const isExp=exp===slot.id;
        const hasExp=["rotate","evening","anchor","work1","work2"].includes(slot.id);
        const c=C[d.type]||C.life;
        const past=selDay===today&&hFrac>=slot.end;

        if(isOff&&["work1","work2","rotate"].includes(slot.id)){
          if(slot.id==="work1") return <div key="off" style={{padding:"20px 14px",background:"#111",borderRadius:8,border:"1px solid #222",textAlign:"center",color:"#555",fontStyle:"italic",fontSize:15}}>🌿 Ngày nghỉ</div>;
          return null;
        }

        return <div key={slot.id} onClick={()=>hasExp&&setExp(isExp?null:slot.id)} style={{
          padding:"10px 14px",background:cur?c.bg:past?"#0a0a0a":"#111",borderRadius:8,
          cursor:hasExp?"pointer":"default",border:cur?`1px solid ${c.br}`:"1px solid #1a1a1a",
          opacity:past&&!cur?0.45:1,position:"relative",overflow:"hidden"
        }}>
          {cur&&<div style={{position:"absolute",left:0,top:0,bottom:0,width:3,background:c.tx,borderRadius:"3px 0 0 3px"}}/>}
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
            <div style={{display:"flex",alignItems:"center",gap:10,flex:1,minWidth:0}}>
              <span style={{fontSize:16,flexShrink:0}}>{slot.icon}</span>
              <div style={{minWidth:0}}>
                <div style={{fontSize:14,fontWeight:cur?600:400,color:cur?c.tx:past?"#555":"#ccc",whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}}>{d.label}</div>
                <div style={{fontFamily:"'JetBrains Mono',monospace",fontSize:10,color:past?"#444":"#555",marginTop:2}}>{hrStr(slot.start)} - {hrStr(slot.end)}</div>
              </div>
            </div>
            <div style={{display:"flex",alignItems:"center",gap:6,flexShrink:0}}>
              {(d.type==="big"||d.type==="small")&&d.label!=="OFF"&&<span style={{fontSize:9,padding:"2px 6px",borderRadius:3,background:c.bd,color:c.bt,fontFamily:"'JetBrains Mono',monospace",fontWeight:600}}>{d.type==="big"?"BIG":"SMALL"}</span>}
              {hasExp&&<span style={{fontSize:10,color:"#555",transform:isExp?"rotate(180deg)":"none",transition:"transform 0.2s"}}>▼</span>}
            </div>
          </div>

          {isExp&&slot.id==="rotate"&&<ExpandList title="TẤT CẢ ROTATING ACTIVITIES" items={ALL_ROTATE} selDay={selDay} colorKey="type"/>}
          {isExp&&slot.id==="evening"&&<ExpandList title="GỢI Ý - skip được nếu có lịch xã hội" items={ALL_EVENING} selDay={selDay} colorKey="evening"/>}
          {isExp&&slot.id==="anchor"&&<AnchorExpand/>}
          {isExp&&(slot.id==="work1"||slot.id==="work2")&&!isOff&&<WorkExpand id={slot.id} selDay={selDay}/>}
        </div>;
      })}
    </div>
  </>;
}

function ExpandList({title,items,selDay,colorKey}) {
  return <div style={{marginTop:10,paddingTop:10,borderTop:"1px solid #222"}} onClick={e=>e.stopPropagation()}>
    <p style={{fontSize:11,color:"#666",margin:"0 0 8px",fontFamily:"'JetBrains Mono',monospace"}}>{title}</p>
    {items.map((a,i)=>{
      const isAct=a.days.split(", ").includes(selDay);
      const rc=colorKey==="type"?(C[a.type]||C.life):C.evening;
      return <div key={i} style={{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"6px 8px",marginBottom:3,borderRadius:4,background:isAct?rc.bg:"transparent",border:isAct?`1px solid ${rc.br}`:"1px solid transparent"}}>
        <span style={{fontSize:13,color:isAct?rc.tx:"#555"}}>{isAct?"→ ":""}{a.label}</span>
        <span style={{fontFamily:"'JetBrains Mono',monospace",fontSize:10,color:isAct?rc.bt:"#444"}}>{a.days}</span>
      </div>;
    })}
  </div>;
}

function AnchorExpand() {
  return <div style={{marginTop:10,paddingTop:10,borderTop:"1px solid #222"}} onClick={e=>e.stopPropagation()}>
    <p style={{fontSize:11,color:"#666",margin:"0 0 8px",fontFamily:"'JetBrains Mono',monospace"}}>SPIRITUAL WIN - luôn chạy, kể cả đi nhậu về</p>
    {ANCHOR_STEPS.map((s,i)=><div key={i} style={{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"6px 8px",marginBottom:3,borderRadius:4,background:"#1a1a15",border:"1px solid #2a2a1a"}}>
      <span style={{fontSize:13,color:s.required?"#bcbc8f":"#888"}}>{s.label} {s.required&&<span style={{fontSize:9,color:"#bc8f8f"}}>bắt buộc</span>}</span>
      <span style={{fontFamily:"'JetBrains Mono',monospace",fontSize:10,color:"#666"}}>{s.duration}</span>
    </div>)}
  </div>;
}

function WorkExpand({id,selDay}) {
  const map=id==="work1"?WORK1_MAP:WORK2_MAP;
  return <div style={{marginTop:10,paddingTop:10,borderTop:"1px solid #222"}} onClick={e=>e.stopPropagation()}>
    <p style={{fontSize:11,color:"#666",margin:"0 0 8px",fontFamily:"'JetBrains Mono',monospace"}}>{id==="work1"?"PEAK - deep work, analytical":"TROUGH - execution, routine"}</p>
    {DAYS.filter(d=>d!=="CN").map(d=>{
      const act=d===selDay;
      return <div key={d} style={{display:"flex",justifyContent:"space-between",padding:"4px 8px",marginBottom:2,borderRadius:4,background:act?"#1a1a2f":"transparent",border:act?"1px solid #2d2d5a":"1px solid transparent"}}>
        <span style={{fontFamily:"'JetBrains Mono',monospace",fontSize:11,color:act?"#8f8fbc":"#444",minWidth:24,fontWeight:600}}>{d}</span>
        <span style={{fontSize:12,color:act?"#c8c8e6":"#555"}}>{map[d]}</span>
      </div>;
    })}
  </div>;
}

function Week({setView,setSelDay,today}) {
  const secs=[
    {title:"ROTATING 17:00-18:00",data:DAYS.map(d=>({day:d,label:ROTATE_MAP[d].label,type:ROTATE_MAP[d].type}))},
    {title:"WORK BLOCK 1 (9-12h)",data:DAYS.map(d=>({day:d,label:WORK1_MAP[d],type:"work"}))},
    {title:"WORK BLOCK 2 (13:30-17h)",data:DAYS.map(d=>({day:d,label:WORK2_MAP[d],type:"work"}))},
    {title:"BUỔI TỐI (gợi ý)",data:DAYS.map(d=>({day:d,label:EVENING_MAP[d].label,type:"evening"}))},
  ];
  return <div style={{paddingTop:16}}>
    {secs.map((s,si)=><div key={si} style={{marginBottom:20}}>
      <h3 style={{fontFamily:"'JetBrains Mono',monospace",fontSize:11,color:"#555",margin:"0 0 8px",letterSpacing:"0.5px"}}>{s.title}</h3>
      <div style={{display:"flex",flexDirection:"column",gap:2}}>
        {s.data.map((it,i)=>{
          const c=C[it.type]||C.life;
          const isTd=it.day===today;
          return <div key={i} onClick={()=>{setSelDay(it.day);setView("today");}} style={{
            display:"flex",alignItems:"center",gap:10,padding:"8px 10px",
            background:isTd?c.bg:"#111",borderRadius:6,
            border:isTd?`1px solid ${c.br}`:"1px solid #1a1a1a",cursor:"pointer"
          }}>
            <span style={{fontFamily:"'JetBrains Mono',monospace",fontSize:11,color:isTd?c.tx:"#444",minWidth:24,fontWeight:600}}>{it.day}</span>
            <span style={{fontSize:13,color:isTd?c.tx:"#777",flex:1}}>{it.label}</span>
            {it.type==="big"&&it.label!=="OFF"&&<span style={{fontSize:8,padding:"1px 4px",borderRadius:2,background:c.bd,color:c.bt,fontFamily:"'JetBrains Mono',monospace"}}>BIG</span>}
            {it.type==="small"&&<span style={{fontSize:8,padding:"1px 4px",borderRadius:2,background:c.bd,color:c.bt,fontFamily:"'JetBrains Mono',monospace"}}>SMALL</span>}
          </div>;
        })}
      </div>
    </div>)}
  </div>;
}

function Plan() {
  const [open,setOpen]=useState(null);
  const secs=[
    {k:"ph",t:"🧭 Triết lý",c:<div>
      <p style={ps}><b style={{color:"#8fbc8f"}}>3 Daily Wins:</b> Physical (sáng) → Mental (ngày) → Spiritual (tối)</p>
      <p style={ps}><b style={{color:"#8f8fbc"}}>Circadian:</b> Analytical sáng (peak), creative chiều (recovery). Trough 13-15h chỉ routine.</p>
      <p style={ps}><b style={{color:"#bc8fb0"}}>Ưu tiên:</b> Big Goals = morning sacred zone. Small Goals = rotating slots only.</p>
    </div>},
    {k:"bg",t:"🎯 Big Goals",c:<div>{[
      "Vẽ đều (daily) - cầm bút lên là vẽ được",
      "Viết đều (daily) - chạm bàn phím là viết được",
      "Thiền đều (daily, 10-15 phút)",
      "Thể dục - đi bộ 10k + calisthenics 3x/tuần",
      "Ăn uống có kế hoạch - 1 thực đơn/tuần",
      "Làm việc - own projects + client",
    ].map((g,i)=><div key={i} style={{padding:"6px 0",borderBottom:"1px solid #1a1a1a",fontSize:13,color:"#ccc"}}><span style={{color:"#8fbc8f",marginRight:8}}>{i+1}.</span>{g}</div>)}</div>},
    {k:"sg",t:"📌 Small Goals",c:<div>{[
      "Luyện Tarot lý thuyết + practice đọc bài",
      "Luyện Chiêm tinh lý thuyết + practice đọc chart",
      "Viết có chủ đề → bài viết (upgrade từ free write)",
    ].map((g,i)=><div key={i} style={{padding:"6px 0",borderBottom:"1px solid #1a1a1a",fontSize:13,color:"#ccc"}}><span style={{color:"#bcb08f",marginRight:8}}>{i+1}.</span>{g}</div>)}</div>},
    {k:"an",t:"✨ Evening Anchor",c:<div>
      <p style={{...ps,color:"#bc8f8f",fontStyle:"italic"}}>Luôn chạy, kể cả đi nhậu về.</p>
      {ANCHOR_STEPS.map((s,i)=><div key={i} style={{padding:"6px 0",borderBottom:"1px solid #1a1a1a",fontSize:13,display:"flex",justifyContent:"space-between"}}>
        <span style={{color:s.required?"#bcbc8f":"#888"}}>{s.label}</span>
        <span style={{fontFamily:"'JetBrains Mono',monospace",fontSize:11,color:"#555"}}>{s.duration}</span>
      </div>)}
    </div>},
    {k:"up",t:"📈 Khi nào Upgrade",c:<div>{[
      {w:"Streak viết stable 4-6 tuần",a:"2-3 buổi free write → viết bài"},
      {w:"Groove vẽ stable",a:"30p → 45-60p (dậy sớm hơn hoặc lấy từ tối)"},
      {w:"Body adapt",a:"Calisthenics 3x → 4-5x/tuần"},
      {w:"Slot trống ở rotating/tối",a:"Thêm small goal. Không lấy từ morning sacred zone."},
    ].map((u,i)=><div key={i} style={{padding:"8px 0",borderBottom:"1px solid #1a1a1a"}}>
      <div style={{fontSize:12,color:"#8fbc8f",fontFamily:"'JetBrains Mono',monospace"}}>KHI: {u.w}</div>
      <div style={{fontSize:13,color:"#ccc",marginTop:4}}>→ {u.a}</div>
    </div>)}</div>},
  ];
  return <div style={{paddingTop:16}}>{secs.map(s=><div key={s.k} style={{marginBottom:4}}>
    <button onClick={()=>setOpen(open===s.k?null:s.k)} style={{width:"100%",padding:"12px 14px",background:open===s.k?"#1a1a1a":"#111",border:"1px solid #1a1a1a",borderRadius:open===s.k?"6px 6px 0 0":6,color:"#e0ddd5",fontFamily:"'Crimson Pro',serif",fontSize:15,fontWeight:600,cursor:"pointer",textAlign:"left",display:"flex",justifyContent:"space-between"}}>
      {s.t}<span style={{color:"#555",fontSize:11,transform:open===s.k?"rotate(180deg)":"none",transition:"transform 0.2s"}}>▼</span>
    </button>
    {open===s.k&&<div style={{padding:"12px 14px",background:"#0d0d0d",border:"1px solid #1a1a1a",borderTop:"none",borderRadius:"0 0 6px 6px"}}>{s.c}</div>}
  </div>)}</div>;
}

const ps={fontSize:13,color:"#aaa",margin:"0 0 10px",lineHeight:1.6};
