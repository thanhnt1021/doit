# PGA — PRODUCT GROWTH ANALYSIS

## 🐵 Ngộ Không — Engine Phân tích & Tối ưu Tăng trưởng Sản phẩm

---

```yaml
---
framework: TDK-Pipeline
role: PGA (Ngộ Không)
version: 1.0
execution_protocol: v1
min_claude_model: sonnet
mode: [full, lite, delta, dimension]
related_files: [MASTER_v1.md, INFRA_v1.md, RRI-T_v1.md]
---
```

**6 Personas × 6 Dimensions × 7 Stress Axes × 4 Growth Levers × Product-Path Analysis = Product-Market Fit**

Synthesized from: Hooked · Contagious · The Mom Test · Obviously Awesome · Don't Make Me Think

---

# PART 1: CLI EXECUTION PROTOCOL

> **Claude: đọc Part 1 TRƯỚC. Follow protocol. Dùng Part 2 làm knowledge base. Dùng Part 3 cho output.**
> **Nếu đến từ MASTER_v1.md pipeline → context đã có, skip EP.3, dùng context từ MASTER.**

---

## EP.1 Khi nhận file này, Claude phải:

```
1. ĐỌC Part 1 (CLI Protocol) — hiểu CÁCH CHẠY
2. KHÔNG dump methodology ra cho user
3. Nếu đến từ MASTER pipeline → dùng context đã thu thập, skip EP.3
4. Nếu standalone (không có MASTER) → chạy EP.3 Interactive Flow
5. DÙNG Part 2 (Methodology) làm knowledge base khi analyze
6. OUTPUT theo format EP.5 — consistent mỗi lần
```

## EP.2 Execution Modes

```
MODE 1: FULL ANALYSIS ("analyze" / "phân tích sản phẩm" / "chạy PGA")
  → EP.3 → Full 5 Phases → Structured Output EP.5

MODE 2: LITE ANALYSIS ("check nhanh" / solo dev / < 100 users)
  → EP.3 shortened → Lite config (3 personas, 3 dimensions) → Focused Output

MODE 3: DELTA ("chạy lại" / "đã implement, check lại")
  → Input previous + changes → Delta Output EP.6

MODE 4: DIMENSION ("check virality" / "fix retention" / specific dimension)
  → Focus 1-2 dimensions → Deep-dive Output

MODE 5: IMPLEMENT ("làm luôn" / "code giùm" sau analysis)
  → Đọc Action Roadmap → Generate code/config cho action #1
```

## EP.3 Interactive Flow — Thu thập Context

```
BƯỚC 1: CORE INFO (hỏi nếu user chưa cung cấp)
  Q1: "Sản phẩm tên gì, loại gì?"
      → Infer type: bot | web app | mobile | game/quiz | e-commerce | content
  Q2: "Giai đoạn nào? Bao nhiêu users?"
      → Classify: idea | MVP | launched | growing | scaling | stagnant
  Q3: "Giải quyết vấn đề gì, cho ai?"
  Q4: "Vấn đề lớn nhất hiện tại?"

BƯỚC 2: ENRICHMENT (nếu stage ≥ launched)
  Q5: "Có data user behavior?" → retention, churn point, top flow
  Q6: "Biết tại sao user bỏ dùng?"
  Q7: "Đang kiếm tiền chưa? Model gì?"

BƯỚC 3: AUTO-CONFIG (confirm với user)
  → Lookup DT.1 → Output config → User confirm
```

## EP.4 Decision Tree — Auto-Config

```
TYPE = bot
  Dimensions: G1 + G2 + G3
  Personas: 🎯 + 🔄 + 📣 + 😤
  Stress: S2 Platform + S4 Content + S6 Resource
  Special: Mỗi message = 1 screen. TTFV < 30s.

TYPE = web app / SaaS
  Dimensions: G1 + G4 + G5
  Personas: 🎯 + 🤔 + 💰 + 😤
  Stress: S1 Competitor + S3 Scale + S7 Dependency
  Special: Landing page = make or break.

TYPE = game / quiz / interactive
  Dimensions: G2 + G3
  Personas: 🔄 + 📣 + 😤
  Stress: S4 Content + S1 Competitor
  Special: Core loop < 60s. Replayability = everything.

TYPE = e-commerce
  Dimensions: G1 + G4 + G5
  Personas: 🎯 + 🤔 + 💰
  Stress: S5 Trust + S1 Competitor + S7 Dependency
  Special: Checkout friction = revenue killer.

TYPE = content platform
  Dimensions: G2 + G3 + G6
  Personas: 🔄 + 📣 + 😤
  Stress: S4 Content + S3 Scale

STAGE OVERLAY:
  idea/MVP     → ADD 🤔, REMOVE 😤, Focus G4+G5 first
  launched     → Full config above
  growing      → ADD G3+G5 emphasis
  scaling      → ADD G6, full stress
  stagnant     → ADD 😤 CRITICAL, re-do G4
```

## EP.5 Output Format

```
════════════════════════════════════════════════════════════════
PGA ANALYSIS — [Product Name]
Date: [auto]  |  Mode: [Full|Lite|Delta]
Type: [auto]  |  Stage: [auto]
Config: Personas [list] | Dimensions [list] | Stress [list]
════════════════════════════════════════════════════════════════

1. PRODUCT PROFILE SUMMARY
   [5 dòng max]

2. PRODUCT-PATH SUMMARY
   Flow: [entry] →(___%)→ [step1] →(___%)→ [step2] →(___%)→ [core value]
   Biggest drop-off: [step] at [___]%
   Confidence: [🟢 data | 🟡 description | 🔴 assumption]

3. HEALTH CARD
   ┌─────────────────────────────────────────────────────┐
   │ G1 First Contact:   [🟢|🟡|🔴|⬜]  [evidence]      │
   │ G2 Core Loop:       [🟢|🟡|🔴|⬜]  [evidence]      │
   │ G3 Virality:        [🟢|🟡|🔴|⬜]  [evidence]      │
   │ G4 Positioning:     [🟢|🟡|🔴|⬜]  [evidence]      │
   │ G5 Monetization:    [🟢|🟡|🔴|⬜]  [evidence]      │
   │ G6 Retention:       [🟢|🟡|🔴|⬜]  [evidence]      │
   ├─────────────────────────────────────────────────────┤
   │ Weighted Score: [___]%                               │
   │ BLOCKED AT GATE: [N or NONE]                         │
   │ Confidence: [🟢|🟡|🔴] overall                       │
   └─────────────────────────────────────────────────────┘

4. TOP GAPS (max 7, sorted by impact)
   GAP #N:
     Persona: [emoji]  Dimension: [G?]  Result: [🟢🟡🔴⬜]
     Observation: [what's happening]
     Gap: [what's missing]
     Evidence: [data]  Confidence: [🟢🟡🔴]
     Action: [specific, implementable]
     Effort: [S|M|L]  Impact: [H|M|L]
     Stress: [resilient | ⚠️ vulnerable to S?]
     Ethics: [✅ | ⚠️ flag]
     Regression: [G? may be affected]

5. PERSONA COMBO TENSIONS (top 3)

6. ACTION ROADMAP (sorted by Impact/Effort)
   🔥 DO FIRST: #1 — metric — est time — regression check — ethics
   ⭐ DO NEXT:  #2 — ...
   📋 PLAN:     #3 — ...

7. HANDOFF TO NEXT PHASE
   → Nếu trong MASTER pipeline: "PGA xong. Chuyển sang [BUILD|INFRA|RRI-T]?"
   → Nếu standalone: "Muốn tao implement action #1?"

════════════════════════════════════════════════════════════════
```

## EP.6 Delta Mode

```
INPUT: Previous Health Card + Actions implemented + New data
OUTPUT:
  HEALTH CARD DELTA: G1: [old] → [new] [↑↓—]
  REGRESSION DETECTED: [G? worsened because ___] OR [None]
  NEW TOP GAPS: [if any]
  NEXT ACTIONS: [updated roadmap]
```

## EP.7 Confidence System

```
🟢 HIGH — analytics data, ≥5 user interviews, A/B test
🟡 MEDIUM — user description, logs, 1-3 observations
🔴 LOW — assumption, no data

RULES:
  🟢 → result stands
  🟡 → result + "verify with [data] within [timeframe]"
  🔴 → "⚠️ LOW CONFIDENCE — hypothesis, not conclusion"
  Overall = lowest individual
```

## EP.8 Ethics Auto-Check

```
MỖI recommended action, TỰ ĐỘNG check:
  □ Fake scarcity?           → ❌ Flag
  □ Punishment for break?    → ❌ Flag, suggest "best streak"
  □ Forced viral?            → ❌ Flag, suggest value-first
  □ Guilt notification?      → ❌ Flag, suggest value notification
  □ Data hostage?            → ❌ Flag, suggest easy export
  □ Bait-and-switch?         → ❌ Flag, suggest transparent pricing
  □ Fake social proof?       → ❌ Flag
  □ Fear manipulation?       → ❌ Flag, suggest positive framing

  Fail → output ⚠️ + alternative.
```

---

# PART 2: METHODOLOGY REFERENCE

> **Claude: knowledge base. Không dump ra cho user.**

---

## 1. TRIẾT LÝ

> *Đừng chỉ hỏi sản phẩm có CHẠY không. Hãy hỏi sản phẩm có khiến người ta QUAY LẠI và RỦ BẠN BÈ không.*

### Cost of Discovery

```
Phát hiện sai hướng lúc...           →  Chi phí
─────────────────────────────────────────────────
PGA trước code (idea validation)      →  1×
PGA sau MVP (early feedback)          →  5×
Sau launch, ít user (wrong position)  →  20×
Sau 6 tháng, churn cao                →  50×
```

---

## 2. 6 ANALYSIS PERSONAS

| Persona | Tư duy | Focus |
|---|---|---|
| 🎯 First-Time User | "Vừa mở, hiểu gì?" | Onboarding, TTFV, first impression |
| 🔄 Returning User | "Có lý do quay lại?" | Hook loop, habit, variable reward |
| 📣 Evangelist | "Muốn khoe cái này?" | Share, social currency, virality |
| 🤔 Skeptic | "Tại sao cái này, không cái kia?" | Positioning, differentiation |
| 💰 Paying Customer | "Có đáng tiền?" | Monetization, WTP |
| 😤 Churned User | "Đã bỏ. Tại sao?" | Churn reasons, deal-breakers |

### 2.1 🎯 First-Time User

*"8 giây trước khi bấm back."*

Checklist: (1) 5s biết SP là gì? (2) TTFV < 30s (bot) / < 60s (web)? (3) ≤ 3 steps tới core value? (4) Không cần /help? (5) Error recovery? (6) Zero-state guide?

### 2.2 🔄 Returning User

Hook Loop audit:

| Component | Check | 🟢 THRIVING | 🔴 BLEEDING |
|---|---|---|---|
| Trigger | Cảm xúc nào nhắc tới SP? | ≥1 internal + ≥1 external | 0, quên SP tồn tại |
| Action | Core action effort? | ≤3 taps, <5s | >10s, confused |
| Variable Reward | Khác mỗi lần? | Unpredictable, tò mò | Same, boring |
| Investment | User tạo data riêng? | Có, improve experience | 0, fresh start |

3 loại Variable Reward: Tribe (social) · Hunt (info/content) · Self (mastery/collection)

Investment types: Data (history) · Reputation (badge) · Customization · Social (friends) · Content (journal)

### 2.3 📣 Evangelist — STEPPS

**S**ocial Currency: Share = trông cool? Unique result? Inner ring?
**T**riggers: Gắn context hàng ngày? Frequency?
**E**motion: High-arousal (awe, humor) → share. Low (meh) → kill.
**P**ublic: Output visible ngoài SP? Share card?
**P**ractical Value: Forward-worthy 1 câu?
**S**tories: Conversation piece?

Share Mechanics: ≤ 2 taps. Image card > text link. Deep link back.

### 2.4 🤔 Skeptic — Positioning

| Step | Question | Output |
|---|---|---|
| 1 | Thay thế bằng gì? (kể cả "không làm gì") | ≥3 alternatives |
| 2 | Có gì KHÁC biệt? | ≥2 unique attributes |
| 3 | Attribute → value? | 1 benefit each |
| 4 | Ai cần nhất? | 1 câu mô tả |
| 5 | Category nào? | 1 category |
| 6 | Pitch ≤ 15 từ | 1 sentence |

### 2.5 💰 Paying Customer — Mom Test

- "Lần cuối bỏ tiền cho alternative = bao nhiêu?"
- "Workflow nào mất thời gian mà cái này giải quyết?"
- "Biến mất ngày mai, dùng gì thay?"

WTP signals: Đã trả cho alternatives? Bỏ TIME cho free? Phàn nàn "giá mà có thêm X"?

### 2.6 😤 Churned User

| Churn Type | Signal | Root Cause |
|---|---|---|
| Never Activated | 1 session, never return | G1 fail |
| Early Churn | 2-3 sessions then stop | G2 fail |
| Late Churn | Weeks then stop | G6 fail — content cạn |
| Forced Churn | Wanted to continue, blocked | Paywall / platform |
| Competitive | Switched to alternative | G4 fail |
| Emotional | Bad experience | Trust broken |

---

## 3. 6 PRODUCT DIMENSIONS

| Dimension | Central Question |
|---|---|
| G1: First Contact | User hiểu + nhận value trong bao lâu? |
| G2: Core Loop | Vòng lặp cốt lõi có gây nghiện? |
| G3: Virality | SP tự lan truyền? |
| G4: Positioning | SP khác biệt gì trong đầu user? |
| G5: Monetization | Giá trị nào user chịu trả? |
| G6: Retention | Giữ user sau tuần đầu? |

### Result Types & Scoring

| Result | Ký hiệu | Weight |
|---|---|---|
| THRIVING | 🟢 | 1.0 |
| SURVIVING | 🟡 | 0.5 |
| BLEEDING | 🔴 | 0.0 |
| ABSENT | ⬜ | 0.0 (excluded) |

```
Weighted Score = Σ(result × dim_weight) / Σ(dim_weight) × 100%
Priority dimension (from DT.1) = 2.0, non-priority = 1.0, ABSENT = excluded
```

### Gates

```
Gate 1: G1 ≥ 🟡 (user phải hiểu SP)
Gate 2: G2 ≥ 🟡 (phải có lý do quay lại)
Gate 3: G3 ≥ 🟡 OR G5 ≥ 🟡 (viral hoặc kiếm tiền)
Gate 4: G6 ≥ 🟡 (giữ được user)
```

---

## 4. 7 STRESS AXES

| # | Axis | Scenario |
|---|---|---|
| S1 | COMPETITOR | Clone, giá rẻ hơn, UX tốt hơn |
| S2 | PLATFORM | API deprecated, platform block |
| S3 | SCALE | 10x users đột ngột |
| S4 | CONTENT | Content cạn, novelty hết |
| S5 | TRUST | Bug mất data, AI output sai |
| S6 | RESOURCE | Solo dev burnout, nghỉ → product chết? |
| S7 | DEPENDENCY | API tăng giá 10x, library deprecated |

Top combos: S3×S5 (viral+crash) · S1×S2 (competitor native) · S6×S7 (solo+API down)

---

## 5. DIAGNOSIS DECISION TREE

```
"User không hiểu SP"        → G1 🔴 → Simplify onboarding
"Dùng 1 lần rồi bỏ"        → G2 🔴 → Check Trigger/Reward/Investment
"Dùng nhưng không share"    → G3 🔴 → Check STEPPS, share mechanics
"Thích nhưng không trả tiền" → G5 🔴 → Free too generous? Paywall too early?
"Trả tiền rồi cancel"       → G6 🔴 → Content exhaustion? Value plateau?
"Không khác competitor"      → G4 🔴 → Run Positioning Canvas
```

---

## 6. PERSONA COMBO TENSIONS

```
🎯×🔄  Simple vs Deep      "Onboarding bỏ feature = lý do quay lại?"
📣×💰  Viral vs Paywall     "Best content free hay premium?"
🔄×😤  Hook vs Churn        "Hook có nhưng vẫn churn — sai loại hook?"
🎯×📣  Onboard vs Share     "Cần data để share ↔ data = friction"
🎯×💰  Trial length         "Usage-limited > time-limited"
🤔×📣  Niche vs Mass        "Niche first, expand after PMF"
```

---

## 7. GROWTH REGRESSION

```
Share buttons mọi nơi         → G1 cluttered
Paywall thêm                  → G6 churn tăng
Simplify (bỏ features)        → G2 power users mất depth
Gamification                  → G4 feels cheap
Push notification tăng         → G6 annoying → churn
```

---

## 8. VIETNAMESE MARKET

### Payment & Trust
- QR/Momo/ZaloPay > credit card
- Anchor strong, odd pricing (99k not 100k)
- Trust người thật > brand
- Zalo/FB >> Telegram cho share
- "Free trước, hay thì trả"

### Behavior
- Peak 20:00-23:00
- Lunch 11:30-13:00
- Payday (5, 15, cuối tháng) → premium upsell
- Screenshot > link cho share
- Vietnamese-first, not translated

---

## 9. ANTI-PATTERNS

| # | Pattern | Fix |
|---|---|---|
| 1 | Feature factory | Kill <5% usage features |
| 2 | Build and hope | Design virality INTO product |
| 3 | Premature monetization | Hook BEFORE paywall |
| 4 | Copy the leader | Learn WHY, apply principle |
| 5 | Survey-driven | Behavior > opinion |
| 6 | Virality before retention | Fix G2/G6 BEFORE G3 |
| 7 | Solo chamber | 😤 persona mandatory |
| 8 | Metric-blind | Define metric BEFORE build |

---

## 10. INTEGRATION VỚI BỘ TDK

```
PGA → MASTER: Action roadmap → MASTER validates problem → routes BUILD
PGA → RRI-T:  PGA 🔴 module → RRI-T test affected module
PGA → INFRA:  PGA action needs infra (cron, storage, CDN) → INFRA setup
RRI-T → PGA:  RRI-T ⚠️ PAINFUL → PGA input: friction in G1/G2/G6
RRI-T → PGA:  RRI-T 🔲 MISSING → PGA validates: build or not?
INFRA → PGA:  INFRA constraint → PGA adjusts recommendations
```

---

# PART 3: BENCHMARKS & TEMPLATES

---

## BM.1 Benchmarks by Type

```
BOT:        D1 ret ≥25% 🟢 | 10-24% 🟡 | <10% 🔴    TTFV <30s 🟢
WEB APP:    Conv ≥5% 🟢 | 2-4% 🟡 | <2% 🔴          TTFV <60s 🟢
GAME/QUIZ:  D1 ret ≥35% 🟢 | 15-34% 🟡 | <15% 🔴    Loop <60s 🟢
E-COMMERCE: Conv ≥3% 🟢 | 1-2% 🟡 | <1% 🔴          Cart aband <50% 🟢
CONTENT:    D1 ret ≥20% 🟢 | 10-19% 🟡 | <10% 🔴     Share ≥8% 🟢

Stage modifiers: MVP ×0.7 | Launched ×1.0 | Growing ×1.2
```

## T.1 Hook Loop Template

```
TRIGGER:  Internal: [emotion]  External: [notification]  Freq: [daily/weekly]
ACTION:   Core: [what]  Taps: [N]  Time: [Ns]
REWARD:   Type: [Tribe|Hunt|Self]  Varies: [what]
INVEST:   Creates: [what]  Switching cost: [what lost]
LOOP:     Duration: [Ns]  Viability: [Strong|Moderate|Weak|Broken]
ETHICS:   [✅|⚠️]
```

## T.2 Positioning Canvas

```
ALTERNATIVES: 1.___ 2.___ 3.___ 4.(nothing)
UNIQUE: 1.___ 2.___
VALUE MAP: [attr]→[benefit]
TARGET (1 sentence): ___
PITCH (≤15 words): "___"
```

## T.3 STEPPS Audit

```
S Social Currency:  [🟢🟡🔴]  Evidence: ___
T Triggers:         [🟢🟡🔴]  Evidence: ___
E Emotion:          [🟢🟡🔴]  Evidence: ___
P Public:           [🟢🟡🔴]  Evidence: ___
P Practical Value:  [🟢🟡🔴]  Evidence: ___
S Stories:          [🟢🟡🔴]  Evidence: ___
WEAKEST: ___  ACTION: ___
```

## T.4 Growth Regression Matrix

```
ACTION: [description]  TARGET: [G?] ↑
G1: [OK|⚠️]  G2: [OK|⚠️]  G3: [OK|⚠️]
G4: [OK|⚠️]  G5: [OK|⚠️]  G6: [OK|⚠️]
⚠️ count: ___ → [OK(0-1) | REVIEW(2) | ABORT(3+)]
```

---

*PGA_v1.md — Bộ Tây Du Ký Pipeline v1.0*
*🐵 Ngộ Không — Product Growth Analysis Engine*
