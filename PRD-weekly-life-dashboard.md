# PRD: Weekly Life Dashboard

**Author**: Unlimab
**Date**: 25/04/2026
**Status**: Draft
**Version**: 0.2

---

## 1. Context & Background

### 1.1 Problem Statement

**Unlimab**, một solo builder đang vận hành hệ thống thói quen hàng ngày với 6 big goals và nhiều small goals rotating theo tuần,

**NEEDS A WAY TO** nhìn thấy, tương tác, và tuỳ chỉnh lịch tuần real-time trên mobile - biết ngay "bây giờ làm gì", rotating gì, và tự điều chỉnh khung giờ theo nhịp sống thực tế,

**BECAUSE** plan dạng markdown phẳng không cho phép tra cứu nhanh theo thời điểm, không phản ánh được sự linh hoạt cần thiết khi nhịp ngày thay đổi (ví dụ: dậy sớm hơn, cần buffer di chuyển, thay đổi giờ tập), dẫn đến mất momentum duy trì thói quen dài hạn.

### 1.2 Background

- Plan đã được thiết kế đầy đủ dưới dạng markdown (weekly-plan.md) bao gồm: daily template cố định, weekly rotating slots, evening menu flexible, evening anchor, và upgrade path.
- Bản MVP v0.1 đã build dưới dạng React artifact trên Claude.ai, đang hoạt động với real-time slot detection và 3 views (Today/Week/Plan).
- Vấn đề phát sinh: khung giờ hardcode không phù hợp khi user cần điều chỉnh theo thực tế (dậy sớm/muộn hơn, thêm buffer di chuyển giữa các slot, thay đổi độ dài session).

### 1.3 Assumptions & Hypotheses

- **H1**: User check lịch nhiều lần/ngày, mỗi lần chỉ cần thấy 1 slice nhỏ (< 3 giây tìm thấy đúng slot).
- **H2**: Khung giờ sẽ thay đổi trong giai đoạn đầu (2-4 tuần) khi user tìm rhythm phù hợp, sau đó ổn định.
- **H3**: User dùng chủ yếu trên mobile (check lúc đi bộ về, lúc chuyển slot, lúc tối).
- **H4**: Không cần track completion ở giai đoạn này - focus vào "biết phải làm gì", chưa cần "đánh dấu đã làm".

---

## 2. Goals & Metrics

### 2.1 Objectives

- **Primary**: Mở app → biết ngay "bây giờ làm gì" trong < 3 giây.
- **Secondary**: User tự điều chỉnh được khung giờ mà không cần rebuild artifact.

### 2.2 Success Metrics

| Metric | Baseline (v0.1) | Target (v0.2) | Đo bằng |
|--------|-----------------|---------------|---------|
| Thời gian tìm slot hiện tại | ~3s (đã đạt) | < 3s (giữ nguyên) | Observation |
| Số ngày liên tiếp mở check | Chưa đo | 14 ngày liên tục | Self-report |
| Tần suất chỉnh lại giờ | N/A | Giảm dần sau 2 tuần | Observation |

### 2.3 North Star Metric

Số ngày liên tiếp user mở dashboard check lịch (proxy cho habit adoption).

---

## 3. User Stories & Scope

### 3.1 User Persona

**Unlimab** - Solo builder, 22-35, đang xây dựng daily routine mới. Dùng mobile là chính. Cần flexibility vì lịch ngày chưa cố định hoàn toàn. Ghét over-engineering, cần đơn giản và nhanh.

### 3.2 User Stories

| ID | Priority | User Story | Acceptance Criteria |
|----|----------|------------|---------------------|
| US-1 | P0 | Là user, tao muốn mở app và thấy ngay slot hiện tại được highlight theo giờ thật | Giờ real-time, update mỗi 30s, slot hiện tại có visual indicator rõ ràng |
| US-2 | P0 | Là user, tao muốn chọn ngày trong tuần (T2-CN) để xem rotating + evening menu của ngày đó | Day selector 7 nút, tap = switch, ngày hiện tại đánh dấu riêng |
| US-3 | P0 | Là user, tao muốn thấy daily template áp dụng cho mọi ngày với rotating thay đổi theo ngày | Daily template cố định + rotating/evening/work blocks thay đổi theo ngày đã chọn |
| US-4 | P0 | Là user, tao muốn chỉnh giờ bắt đầu/kết thúc của từng slot (ví dụ: đi bộ 5:15-6:45 thay vì 5:30-7:00) | Tap vào giờ của slot → input field → save → persist qua sessions |
| US-5 | P0 | Là user, tao muốn thêm/xoá/rename slot tuỳ ý (ví dụ: thêm "Di chuyển ra quán cafe 15p" sau thiền) | Nút thêm slot, chọn vị trí, nhập tên + giờ + type. Xoá/rename slot đã có |
| US-6 | P1 | Là user, tao muốn thấy rõ đâu là BIG goal, đâu là SMALL goal | Badge BIG/SMALL trên mỗi slot, color-coded theo type |
| US-7 | P1 | Là user, tao muốn tap vào rotating/evening slot và thấy tất cả unique activities để biết options | Expand panel hiện danh sách activities + ngày nào chạy cái nào, highlight ngày đang xem |
| US-8 | P1 | Là user, tao muốn xem tổng quan tuần dạng grid | Tab Tuần: 4 section (rotating, work1, work2, tối), tap ngày → jump Today view |
| US-9 | P1 | Là user, tao muốn xem philosophy, goals, upgrade path | Tab Tổng quan: accordion sections |
| US-10 | P2 | Là user, tao muốn reset về lịch mặc định nếu chỉnh sai | Nút "Reset về mặc định" trong Settings, confirm trước khi reset |

### 3.3 Scope

**IN SCOPE (v0.2)**:
- Real-time slot detection (đã có)
- Day selector T2-CN (đã có)
- 3 views: Today / Tuần / Tổng quan (đã có)
- Expand rotating/evening/anchor/work slots (đã có)
- Custom time: chỉnh giờ start/end mỗi slot
- Custom slots: thêm/xoá/rename slot (ví dụ: thêm "Di chuyển" 15p)
- Persist custom settings qua sessions (artifact persistent storage)
- Reset to default

**OUT OF SCOPE (v0.2)**:
- Track completion / check-off
- Notification / reminder
- Sync với Google Calendar
- Multi-user / share schedule
- Meal plan chi tiết (chỉ label "Nấu + ăn")
- Statistics / streaks tracking

---

## 4. Design & UX

### 4.1 Views

**Today View (default)**
- Timeline dọc, slot hiện tại highlighted với thanh màu bên trái
- Slot đã qua mờ đi (opacity thấp)
- Day selector (CN-T2-T3-T4-T5-T6-T7) ở trên
- Tap slot expandable → chi tiết rotating/evening/anchor/work
- Tap giờ của slot → edit mode (input start/end time)
- Nút "+" giữa 2 slot → thêm slot mới

**Week View**
- 4 section dọc: Rotating, Work Block 1, Work Block 2, Buổi tối
- Mỗi section hiện 7 ngày, highlight hôm nay
- Tap ngày → jump sang Today view ngày đó

**Plan View**
- Accordion: Triết lý, Big Goals, Small Goals, Evening Anchor, Khi nào Upgrade
- Static reference, không cần edit

### 4.2 Edit Time Flow

```
User tap vào "05:30 - 07:00" trên slot Đi bộ
  → Giờ chuyển thành 2 input fields [05:30] [07:00]
  → User chỉnh thành [05:15] [06:45]
  → Tap ngoài hoặc bấm ✓ → save
  → Slot tiếp theo tự động suggest adjust (06:45 thay vì 07:00)
  → Persist vào storage
```

### 4.3 Add Slot Flow

```
User tap nút "+" giữa slot Thiền và slot Vẽ
  → Modal nhỏ: Tên slot, Start time, End time, Type (big/small/life)
  → Ví dụ: "Di chuyển ra cafe", 08:00-08:15, life
  → Save → slot mới xuất hiện trong timeline
  → Persist vào storage
```

### 4.4 Aha Moments

| Stage | Aha Moment | Trigger |
|-------|------------|---------|
| First open | "Nó biết bây giờ tao đang ở slot nào" | Auto-highlight current slot real-time |
| Explore | "Tap vào ngày khác thấy hết rotating" | Day selector + expand panels |
| Customize | "Tao chỉnh giờ xong nó nhớ luôn" | Edit time + persist + reload vẫn giữ |
| Habit | "Sáng nào cũng mở check trước khi bắt đầu" | Daily usage > 14 ngày |

---

## 5. Technical

### 5.1 Tech Stack

| Layer | Choice | Lý do |
|-------|--------|-------|
| Frontend | React artifact (.jsx) | Chạy trực tiếp trong Claude.ai, không deploy riêng |
| Styling | Tailwind + inline styles | Có sẵn trong artifact environment |
| State | useState + useReducer | Quản lý schedule state + edit state |
| Persistence | window.storage API (artifact persistent storage) | Lưu custom times/slots qua sessions, key-value store |
| Time | JavaScript Date + setInterval 30s | Real-time slot detection |

### 5.2 Data Model

```
Key: "schedule-config"
Value: {
  version: "0.2",
  customSlots: [
    {
      id: "walk",
      label: "Đi bộ 10k steps",
      start: 5.25,    // 5:15 - user đã custom
      end: 6.75,      // 6:45
      type: "big",
      icon: "🚶",
      isCustom: false  // slot gốc, chỉ chỉnh giờ
    },
    {
      id: "commute-cafe",
      label: "Di chuyển ra quán cafe",
      start: 8.0,
      end: 8.25,
      type: "life",
      icon: "☕",
      isCustom: true   // slot user thêm mới
    },
    // ...
  ],
  // Rotating và evening giữ nguyên logic theo ngày,
  // không cần custom vì đã có map cố định
}
```

### 5.3 Storage Strategy

- **Read on mount**: load "schedule-config" → nếu có thì dùng custom, nếu không thì dùng default
- **Write on change**: mỗi lần user edit time hoặc add/remove slot → save toàn bộ config
- **Reset**: xoá key "schedule-config" → revert về DAILY_TEMPLATE mặc định
- **Migration**: check version field, nếu cũ hơn thì merge với default mới

---

## 6. Risks & Open Questions

### 6.1 Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| User chỉnh giờ overlap giữa 2 slots | Med | High | Validate: không cho end > start của slot sau, warning nếu gap < 0 |
| Artifact persistent storage mất data | Med | Low | Có nút Export config (copy JSON), nút Reset về default |
| Performance trên mobile với nhiều slot | Low | Low | Giữ component nhẹ, không animation nặng, max ~20 slots |
| User quên link artifact | Med | Med | Bookmark hoặc add to home screen |

### 6.2 Open Questions

- [ ] Có cần cho user custom rotating map (đổi ngày tập Calisthenics) hay giữ cố định?
- [ ] Có cần export/import config để backup?
- [ ] Khi nào thêm completion tracking (v0.3)?

### 6.3 Dependencies

- Claude.ai artifact environment (React + persistent storage API)
- Google Fonts CDN (Crimson Pro, JetBrains Mono)

---

## 7. Timeline & Milestones

| Phase | Deliverable | Status |
|-------|------------|--------|
| v0.1 | Core dashboard: real-time, 3 views, expand slots, day selector | ✅ Done |
| v0.2 | Custom time + add/remove slots + persistent storage | 🔲 Next |
| v0.3 | Completion tracking (check-off daily anchors) | 🔲 Future |
| v0.4 | Custom rotating map + statistics/streaks | 🔲 Future |
