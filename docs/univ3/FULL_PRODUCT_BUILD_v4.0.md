# FULL PRODUCT BUILD — AI Product Builder Playbook v4.0

> **Nguồn**: Quét đầy đủ 9 buổi training "Vibe Coding 101 — Không biết gì cũng làm sản phẩm" (Quang Lucas Nguyen — The1ight) trong thư mục `BUOI HOC` — bao gồm cả nội dung slide dạng ảnh và PDF từng trang; đối chiếu và kế thừa `FULL_PRODUCT_BUILD_v3.0.md`; bổ sung lăng kính RDD và kỷ luật tài liệu từ bài học thực chiến SDD→RDD (Goon's Solo Playbook, 7/2026).
>
> **Mục đích**: File hướng dẫn để AI assistant và solo builder đi từ ý tưởng mơ hồ tới MVP live, có dữ liệu, có kênh phân phối, có vòng lặp học từ thị trường — tạo ra sản phẩm ĐƯỢC VIỆC: đúng nhu cầu thiết thực, không thừa thãi, không xa rời thực tế.
>
> **Cách dùng nhanh**: Đưa file này cho AI, kèm mô tả dự án. Yêu cầu AI xác định dự án đang ở phase nào, thiếu artifact nào, rồi chạy đúng playbook của phase đó.
>
> **Mới trong v4.0**: (1) Lăng kính RDD đặt trên mọi quy trình; (2) Kỷ luật tài liệu & context — artifact là bản đồ, không phải bộ luật; (3) Bổ sung toàn bộ kiến thức 9 buổi mà v3.0 còn thiếu: 6 cỗ máy test MVP, 5W1H, Acceptance Criteria định lượng, 6 khối hệ thống, thang database 4 cấp, 5 Rule Vàng quản lý context, reject playbook, Beachhead/Chasm/TAM-SAM-SOM, Hooked Loop, benchmark LTV/CAC…

---

## MỤC LỤC

0. [Lăng kính RDD — câu hỏi đứng trên mọi quy trình](#0-lăng-kính-rdd)
1. [Nguyên tắc vận hành](#1-nguyên-tắc-vận-hành)
2. [Bản đồ từ ý tưởng đến sản phẩm live](#2-bản-đồ-từ-ý-tưởng-đến-sản-phẩm-live)
3. [Phase 0 — Intake và chẩn đoán trạng thái](#3-phase-0)
4. [Phase 1 — Problem Discovery](#4-phase-1--problem-discovery)
5. [Phase 2 — Solution Design và PRD](#5-phase-2--solution-design-và-prd)
6. [Phase 3 — Design, Aha Moment và Prototype](#6-phase-3)
7. [Phase 4 — System Thinking, Data và Architecture](#7-phase-4)
8. [Phase 5 — Build, Deploy và Security](#8-phase-5--build-deploy-và-security)
9. [Phase 6 — AI Agent Workflow](#9-phase-6--ai-agent-workflow)
10. [Phase 7 — Skills, MCP và Scripts](#10-phase-7--skills-mcp-và-scripts)
11. [Phase 8 — Go-To-Market và Growth](#11-phase-8--go-to-market-và-growth)
12. [Templates và prompt dùng ngay](#12-templates-và-prompt-dùng-ngay)
13. [Final checklist](#13-final-checklist)

---

## 0. Lăng kính RDD

**RDD (Revenue-Driven Development)** không phải methodology — nó là một LĂNG KÍNH. Một câu hỏi dán lên màn hình, hỏi trước MỖI quyết định:

> **"Cái này có dẫn tới revenue / user thật không? Nếu không thì tại sao mình đang làm nó?"**

- SDD hỏi: "spec của cái này là gì?" — TDD hỏi: "test cho cái này là gì?" — **RDD hỏi: "cái này có ai chịu trả tiền không?"**
- Revenue là feedback loop trung thực nhất: spec có thể tự sướng, test có thể xanh giả, nhưng khách hàng trả tiền thì không nói dối.
- Với indie maker, ~70% micro-SaaS kiếm dưới $1.000 MRR — nghĩa là từng dòng code, từng spec, từng feature phải hỏi: *"cái này có kéo mình gần hơn tới đồng doanh thu đầu tiên không?"*
- "Tôi làm cái này vì tôi bực với X" luôn thắng "ra mắt tool Y với feature Z" — cái đầu bắt đầu từ nỗi đau có thật (thứ người ta trả tiền để giải quyết), cái sau bắt đầu từ feature (thứ chỉ dân kỹ thuật thấy sướng).
- Loop tạo giá trị (áp cho mọi phòng ban, mọi agent harness): **Detect → Score → Act → Measure → Learn**. Gắn vòng lặp học hỏi vào tín hiệu revenue, không phải vào tín hiệu "quy trình đã đủ đẹp chưa".

**RDD không thay SDD/TDD — nó đặt cả hai xuống dưới một câu hỏi lớn hơn.** Mọi phase, mọi gate, mọi artifact trong playbook này đều phải qua được lăng kính này trước.

---

## 1. Nguyên tắc vận hành

### 1.0 Motto

> **BUILD THE RIGHT PRODUCT > BUILD THE PRODUCT RIGHT.**
> Giải quyết ĐÚNG vấn đề luôn quan trọng hơn áp dụng đúng kỹ thuật phức tạp. Đừng lãng phí thời gian xây một thứ hoàn hảo mà không ai cần.

> "If I had only one hour to save the world, I would spend fifty-five minutes defining the problem, and only five minutes finding the solution." — Einstein

### 1.1 Luật gốc

0. **RDD trước mọi thứ**. Trước mỗi quyết định: cái này có dẫn tới revenue/user thật không? (xem mục 0)
1. **Problem trước, build sau**. Chưa viết được Problem Statement rõ → không build.
2. **Needs trước, solution sau**. Đừng hỏi user muốn feature gì; hỏi họ đang làm gì, khổ ở đâu, workaround ra sao.
3. **Data trước, opinion sau**. Ý kiến chỉ là giả thuyết cho đến khi có hành vi, số liệu hoặc feedback thật. "Dữ liệu thực tế > 1000 giả thiết trong đầu."
4. **Small trước, big sau**. MVP là phiên bản nhỏ nhất đủ để kiểm chứng giả thuyết quan trọng nhất. "Suy nghĩ LỚN. Bắt đầu NHỎ."
5. **Aha trước, feature sau**. Mỗi feature phải dẫn user tới một khoảnh khắc nhận ra giá trị.
6. **Distribution sớm, scale sau**. "Product không chết vì code dở — mà vì KHÔNG CÓ NGƯỜI DÙNG." Build model là 20%, distribution là 80%.
7. **AI khuếch đại tư duy, không thay thế tư duy**. "Tư duy mù mờ + AI = rác nhanh hơn. AI chỉ làm bạn sai nhanh hơn và tự tin hơn về sai lầm của mình."
8. **Nghĩ chậm trước khi tăng tốc**. Luôn VIẾT RA yêu cầu để tư duy (tự tay viết Problem Statement, 4 risks, 3 cân nhắc) — "1 shot prompt là dành cho trẻ con nghịch ngợm". Luôn dùng AI cho thinking & planning TRƯỚC KHI bắt tay build.
9. **Phản xạ AI-first**. Gặp vấn đề → hỏi AI trước, Google sau. Mỗi ngày, mọi vấn đề, đến khi thành bản năng. "AI là Aristotle của bạn — nhưng Aristotle chỉ giúp được nếu bạn biết hỏi."
10. **Khó không phải là làm thế nào, mà là nhìn thấy nhu cầu đáng để làm.** Low-code + AI đã giải quyết "how"; bottleneck là "what & why".

### 1.2 Định nghĩa chuẩn

| Khái niệm | Định nghĩa dùng trong playbook |
|---|---|
| **Product** | Một business dùng công nghệ để phân phối giải pháp cho một nhu cầu thật theo cách bền vững. Technology = phương tiện/đòn bẩy; Business = trái tim. |
| **MVP** | Minimum Viable Product: phiên bản nhỏ nhất có thể dùng để kiểm chứng một giả thuyết cụ thể — đủ để kiểm tra 4 rủi ro của mô hình kinh doanh. Không phải bản làm ẩu. |
| **Prototype** | Phiên bản "xấu-nhưng-đủ" của MVP, để học nhanh: wireframe, UI, flow click được hoặc app logic tối thiểu. |
| **PRD** | Tài liệu điều phối: giúp người, AI và tool hiểu cùng một context về problem, user, scope, flow, data và success metric. "Không có PRD → Dev/AI đoán → Build sai → Sửa mãi." |
| **GTM** | Cách đưa sản phẩm đến tay đúng người dùng, với đúng thông điệp, qua đúng kênh. |
| **PMF** | Product-Market Fit: user quay lại, trả tiền, giới thiệu hoặc thể hiện hành vi chứng minh sản phẩm giải quyết đúng vấn đề. |
| **Vibe Coding** | (Karpathy, 2/2025) Làm sản phẩm bằng cách diễn đạt ý định bằng ngôn ngữ tự nhiên thay vì viết syntax. KHÔNG phải magic: bạn là đạo diễn, AI là đội sản xuất. "Người 'vibe' thật build được v0.1; người phối hợp có tư duy build được product thật sự." |
| **Interface / Model / API** | ChatGPT/Claude.ai/Gemini là **giao diện (showroom)**; sức mạnh nằm ở **model (động cơ)**: GPT, Claude Sonnet/Opus, Gemini Pro. Đổi model → output khác hẳn. **API = mua thẳng động cơ (trả bằng token)** lắp vào hệ thống riêng — nền tảng build sản phẩm AI + tối ưu chi phí. |

### 1.3 Ba tố chất của sản phẩm số thật sự

| Tố chất | Nghĩa |
|---|---|
| **SELF-FUNDED** | Sản phẩm tự tạo dòng tiền, tự nuôi sống chính nó |
| **NEVER DONE** | Liên tục tiến hoá, không có phiên bản hoàn hảo cuối cùng |
| **CHOSEN BY USERS** | Người dùng tự nguyện chọn vì giá trị cốt lõi, không bị ép |

Thiếu 1 trong 3 → chưa phải sản phẩm số thật sự:
- Thiếu Chosen → "phần mềm độc quyền ép dùng"
- Thiếu Self-funded → "sở thích đắt đỏ / làm từ thiện"
- Thiếu Never Done → "sản phẩm đang chết chờ bị thay thế"

**Ba nguyên tắc khi làm sản phẩm số**: **NHANH** (ra chợ sớm — ưu tiên ship càng nhanh càng tốt) · **HỮU ÍCH** (giải quyết vấn đề thực của user, không phải ảo tưởng của một ai đó) · **LINH HOẠT** (thị trường đổi thì sản phẩm đổi, không đứng yên).

### 1.4 Điểm cân bằng vàng

Sản phẩm = giao của **lợi ích người dùng ∩ lợi ích kinh doanh**; công nghệ chỉ là đòn bẩy. Hai kiểu chết:
- Nghiêng hết về user, không có dòng tiền → **chết vì hết vốn**.
- Nghiêng hết về business, bỏ rơi user → **chết vì không ai dùng**.

### 1.5 Gate quyết định

Mỗi phase phải có output rõ. Thiếu output → AI phải dừng và yêu cầu bổ sung, không nhảy phase.

| Phase | Output bắt buộc | Gate để đi tiếp |
|---|---|---|
| Problem Discovery | Problem Statement + 5 Whys + 4 Risks | Có user cụ thể, need cụ thể, insight có bằng chứng |
| Solution Design | MVP scope + PRD + user stories (có Acceptance Criteria) | MVP kiểm chứng được 1 giả thuyết chính |
| Prototype | Journey + user flow + Aha map + prototype | User chạm tới Aha trong flow ngắn |
| Architecture | L0-L3 flow + ERD + API/data plan | Biết app cần lưu gì, xử lý gì, kết nối gì |
| Build/Deploy | App live + repo + database + env vars | Mở được URL, data không mất, không leak key. **Chưa có database + backend logic = vẫn là Prototype (UI logics), chưa phải functional app** |
| GTM | Lean Canvas + positioning + channel plan | Có early adopter và kênh tiếp cận cụ thể |

### 1.6 Kỷ luật tài liệu & context (bài học SDD → RDD)

Playbook này ép sản xuất nhiều artifact (Problem Statement, PRD, Journey, ERD…). **Artifact là công cụ để nghĩ — là TẤM BẢN ĐỒ, không phải BỘ LUẬT.** Bản đồ mà vẽ chi tiết tới từng viên gạch kèm chú thích năm ngoái ai lát thì thành cuốn từ điển — đang đi lạc mà bắt dò từ điển là tiêu.

1. **Single source of truth duy nhất là CODE BASE.** Có codebase rồi thì specs chỉ mô tả hướng đi, không mô tả lại code. Nuôi 2 nguồn sự thật (code + tầng specs mô tả code) → chúng bất đồng bộ theo thời gian → AI hoang mang và tin nhầm.
2. **Xoá artifact chết, đừng sợ.** Plan/report đã xong việc → xoá. LLM không phân biệt được spec "còn sống" và plan "đã chết tháng trước" — với nó tất cả chỉ là input. Research (Chroma "Context Rot", Stanford/TACL 2024, Salesforce "distractor interference"): mọi model đều tệ đi khi input dài và nhiễu, kể cả khi context window còn xa mới đầy. Hàng chục file outdated/conflict rải trong repo = grep trúng là AI bị kéo lệch, hallucinate, đẻ lỗi.
3. **Giữ bộ docs mỏng.** Với một project code, chỉ cần: `CLAUDE.md`/`AGENTS.md`, `system-architecture.md`, `code-standards.md`, `project-overview-prd.md`. Hết.
4. **Comment ghi WHY, không ghi WHAT.** "What" LLM tự suy được; "why" mới là ý định của người viết.
5. **Khi chuyển phase, chỉ đưa cho AI artifact "còn sống" của phase liên quan** — không ném cả đống artifact cũ (đó là cách tự tạo context rot).
6. **Đừng để quy trình trở thành mục tiêu.** SDD, TDD, ADR, plans — tất cả là công cụ. 135 plans không làm ra một đồng doanh thu nào — đó là ego, không phải business.

---

## 2. Bản đồ từ ý tưởng đến sản phẩm live

```text
0. Intake
   -> Dự án đang ở đâu? Có tài liệu gì? Có user thật chưa?

1. Problem Discovery
   -> 10 vấn đề -> lọc 3 (Nhiều + Quen + Nhanh) -> phân tích 4 risks -> chọn 1
   -> Problem Statement + 5 Whys/5W1H + evidence
   -> Test giả định bằng 1 trong 6 cỗ máy (KHÔNG code) trước khi build

2. Solution Design
   -> Reframe solution (WHO-WHAT-HOW đánh thẳng root cause)
   -> Scope MVP theo 1 use case trọn vẹn
   -> PRD (có Acceptance Criteria đo được)

3. Design & Prototype
   -> Customer Journey -> User Stories -> User Flow -> Aha Moment
   -> Prototype "xấu-nhưng-đủ" để test

4. System & Data
   -> L0 Intent -> L1 Business Flow -> L2 User Flow -> L3 System/Data Flow
   -> ERD + CRUD + integration plan

5. Build & Deploy
   -> UI mockup -> FE logic -> Database (Supabase) -> GitHub -> Vercel live URL

6. Operate with AI Agent
   -> Giao task nhỏ -> Review diff -> Test local -> Commit/push/deploy

7. Systematize
   -> Skill cho quy trình lặp lại
   -> MCP cho hệ thống ngoài
   -> Script cho chuỗi cố định

8. GTM & Growth
   -> Lean Canvas -> Positioning + 3M -> Channel plan -> Metrics -> Iterate đến PMF
```

**Con đường mới của solo builder** (thay cho Idea → Fundraise → Hire → Build → Launch → Support → Scale):

```text
Audience -> Vibe code -> Launch -> Community -> AI agents for automation -> Repeat
```

Chú ý: **Audience đứng TRƯỚC sản phẩm.** Solo builder vs PM tổ chức: không xin phép, quyết trong vài phút, pivot ngay khi thấy cần, tự chịu trách nhiệm 100%. Vòng lặp Prompt → Xem kết quả → Sửa & tinh chỉnh → Lặp lại chính là Agile tốc độ cao: "Vài lần commit = 01 Sprint". "Tốc độ không có nghĩa là bỏ qua bước — tốc độ là làm mỗi bước nhanh hơn, với sự hỗ trợ của AI."

Chuỗi framework kết nối: **Design Thinking** (tìm đúng problem) → **Lean Startup** (validate — "Tinh gọn là cắt bỏ triệt để mọi lãng phí để TỐI ƯU HOÁ TỐC ĐỘ HỌC HỎI") → **Agile** (execution).

---

## 3. Phase 0 — Intake và chẩn đoán trạng thái

### 3.1 Khi user đưa một ý tưởng hoặc dự án

| Trạng thái | Dấu hiệu | Việc cần làm |
|---|---|---|
| **Idea** | Chỉ có ý tưởng, chưa có user rõ | Chạy Problem Discovery |
| **Problem draft** | Có user/problem nhưng chưa validate | Viết lại Problem Statement, 5 Whys, 4 Risks |
| **PRD draft** | Có scope/feature | Kiểm tra MVP, Aha, success metric |
| **Prototype** | Có UI hoặc demo | Kiểm tra user flow, usability, data plan |
| **MVP live** | Có URL, repo, DB | Kiểm tra security, metrics, GTM |
| **Post-launch** | Có user/data | Phân tích retention, CAC/LTV, feedback, pivot/scale |

### 3.2 Câu hỏi intake tối thiểu

1. Ai là user chính? Mô tả bằng vai trò và bối cảnh thật.
2. User đang gặp vấn đề gì, trong tình huống nào?
3. Họ đang xử lý bằng workaround nào?
4. Có bằng chứng nào: phỏng vấn, data, hành vi, tiền đã trả, danh sách chờ?
5. MVP hiện tại là gì? Có URL, prototype, repo hoặc PRD chưa?
6. Success metric quan trọng nhất trong 2-4 tuần tới là gì?
7. Kênh nào có thể tiếp cận early adopters ngay?

### 3.3 Output của Phase 0

```markdown
## Project Diagnostic

- Current stage:
- Existing artifacts:
- Strongest known evidence:
- Biggest unknown:
- Recommended next phase:
- Do-not-build-yet reason, if any:
```

---

## 4. Phase 1 — Problem Discovery

### 4.1 Double Diamond trong thực tế

Double Diamond là kỷ luật tư duy, không phải hình vẽ trang trí. "Lỗi sai chí mạng: cố ý bỏ qua kim cương 1, nhảy bổ vào giải pháp ngay lập tức!"

| Nửa | Mode | Việc làm | Cạm bẫy |
|---|---|---|---|
| Problem Space | Diverge (Discover) | Liệt kê nhiều vấn đề, phỏng vấn, quan sát | Chốt vấn đề quá sớm |
| Problem Space | Converge (Define) | Chọn vấn đề đáng giải quyết → **output = Problem Statement** | Chọn vì thích, không vì evidence |
| Solution Space | Diverge (Develop) | Nghĩ nhiều hướng giải pháp | Bám vào giải pháp đầu tiên |
| Solution Space | Converge (Deliver) | Chọn MVP nhỏ nhất để test | Build quá rộng |

**Divergent**: tạo nhiều lựa chọn, không phán xét, không đúng sai. **Convergent**: đánh giá, so sánh, loại bỏ, chọn dứt khoát. **Cạm bẫy lớn nhất: convergent quá sớm trước khi thấy hết lựa chọn.** "Người thất bại là người convergent quá sớm." Solo builder + AI chạy được cả 2 vòng trong vài giờ — nhưng vẫn phải làm ĐỦ 2 vòng.

### 4.2 Bài tập chọn problem

1. Viết 10 vấn đề bạn từng gặp hoặc hiểu sâu (divergent — không lọc, không phán xét).
2. Lọc còn 3 bằng **bộ lọc ý tưởng 3 câu (Nhiều + Quen + Nhanh)**:
   - **Frequency**: "Vấn đề có xảy ra đủ thường xuyên để user nhớ đến bạn không? (Mỗi ngày > Mỗi tháng)"
   - **Credibility (Skin in the game)**: "Bạn có thấu hiểu 'nỗi đau' này từ chính trải nghiệm cá nhân, hay chỉ đang 'đoán'?" (hoặc tối thiểu: có quyền tiếp cận nhóm user này)
   - **Speed to test**: "Bạn có thể tạo ra một phiên bản test cực nhỏ gọn trong vòng **7 ngày** không?"
3. Với từng vấn đề, phân tích 4 risks — "viết thẳng thắn, đừng tô hồng".
4. Chọn 1 vấn đề có tỉ lệ học nhanh nhất, không phải ý tưởng hoành tráng nhất. Founder-problem fit: **"Nếu bạn không hứng thú với vấn đề này sau 1 tuần, bạn sẽ không build được 9 tuần."**

### 4.3 Bốn loại rủi ro

**Bỏ qua bất kỳ 1 trong 4 → xác suất thất bại nhân đôi.**

| Risk | Câu hỏi gốc | Cách test nhanh |
|---|---|---|
| **Value Risk** | "User có thực sự CẦN và khao khát cái này không?" | Phỏng vấn, landing page, waitlist, pre-order, concierge test |
| **Usability Risk** | "Họ có tự dùng trơn tru mà không cần bạn ngồi cạnh hướng dẫn không?" | Click test, usability test 5 người, screen recording |
| **Feasibility Risk** | "Với kỹ năng, nguồn lực hiện tại, MÌNH có đủ sức làm ra nó không?" | Prototype kỹ thuật, spike, hỏi AI/dev, kiểm tra API/tool |
| **Viability Risk** | "Mô hình này có tự nuôi sống được không? Ai trả tiền?" | Pricing interview, unit economics sơ bộ, willingness to pay |

### 4.4 Sáu cỗ máy test MVP (không cần code)

**"Đừng viết code khi bạn có thể dùng 1 trong 6 cách này để test giả định."** Tất cả thực hiện được dưới 7 ngày:

| Cỗ máy | Cách làm |
|---|---|
| **Landing Page** | Trang giới thiệu + nút đăng ký sớm |
| **Fake Button** | Đặt nút tính năng giả để đo mức độ quan tâm |
| **Video Explainer** | Video giải thích giá trị cốt lõi (cách Dropbox khởi đầu) |
| **Wizard of Oz** | Nhìn như AI/tự động, thực chất bạn làm tay phía sau |
| **Pre-order** | Bán trước một sản phẩm chưa hề tồn tại |
| **Concierge MVP** | Phục vụ thủ công 100% cho số ít khách đầu tiên |

Ví dụ validate ladder (chính khoá học này): Paid Article (test ai trả tiền cho kiến thức) → Bán Syllabus (đo nhu cầu) → Khoá offline 5-10 người (validate nội dung + format) → Scale online.

### 4.5 Problem Statement chuẩn

```text
[User cụ thể] needs to [động từ thể hiện nhu cầu]
because [insight/root cause đã quan sát hoặc validate].
```

Ví dụ tốt: "Nhân viên vận hành kho cần in nhãn hàng loạt nhanh và ít lỗi vì hiện tại họ nhập từng nhãn thủ công, mất nhiều thời gian, dễ sai và làm chậm quy trình nhập hàng."

**Bốn lỗi phổ biến (checklist review tự động):**

| Lỗi | ❌ Sai | ✅ Đúng |
|---|---|---|
| Nhảy vào giải pháp | "Người dùng cần chatbot để trả lời nhanh" | "Người dùng không nhận được phản hồi kịp khi cần hỗ trợ" |
| Mô tả mơ hồ | "Không tiện để dùng" | Nêu rõ cái gì khó dùng, với ai |
| Không rõ đối tượng | Nói chung chung | Có persona và vai trò rõ ràng |
| Cảm tính, thiếu insight | "CEO bảo" | Dựa trên quan sát, số liệu |

### 4.6 5 Whys — quy trình 5 bước

```markdown
## 5 Whys
Vấn đề ban đầu:
Why 1 → Trả lời:
Why 2 → Trả lời:
Why 3 → Trả lời:
Why 4 → Trả lời:
Why 5 → Trả lời:
Root cause:
Solution chosen (đánh thẳng root cause):
How to monitor:
```

Quy trình đầy đủ: (1) Define the problem — kết quả tiêu cực là gì → (2) Hỏi "why" — mặc định cố đủ 5 lần trước khi cho phép dừng sớm (why 1-2 thường vẫn là lỗi bề mặt/lỗi con người) → (3) Chốt root cause → (4) **Tìm giải pháp bảo vệ khỏi root cause trong tương lai** → (5) **Triển khai và monitor hiệu quả**.

Worked examples:
- *Nhân viên gãy ngón chân*: kiện hàng rơi vào chân → nhân viên làm rơi → trượt khỏi tay → kiện vượt giới hạn cân nặng → **cái cân không được hiệu chuẩn, đọc sai trọng lượng** (root cause là lỗi hệ thống, không phải lỗi con người ở why 1-2).
- *Tắc đường khi mưa*: chạy ẩu → muốn về trước khi mưa to → tránh ướt và kẹt → ướt lâu gây bệnh → không đủ tiền mua ô tô và đường không đủ chỗ (5 Whys có thể rẽ sang insight kinh tế-hạ tầng).

### 4.7 5W1H — framework xác định nhu cầu thứ hai

Dùng song song với 5 Whys để quét đủ chiều:

- **WHO**: Ai là user chính? Nhân khẩu học, tâm lý (sở thích, giá trị, hành vi, động lực)? Hiện họ giải quyết vấn đề thế nào? Lưu ý văn hoá/ngôn ngữ? Ai là người ra quyết định / chuyên gia liên quan?
- **WHAT**: Giải quyết vấn đề gì? Chức năng chính nào cần thiết? Giải pháp thay thế hiện có? Rủi ro tiềm ẩn? Ràng buộc (kỹ thuật, pháp lý, chi phí, thời gian)?
- **WHERE**: Dùng trong môi trường nào? Thiết bị nào? Di chuyển hay ngồi yên? Độc lập hay theo nhóm?
- **WHEN**: Khi nào ra mắt? Mốc thời gian, deadline từng giai đoạn?
- **WHY**: Tại sao cần thiết? Giá trị cho user, cho business? Khác biệt gì? USP?
- **HOW**: Nguyên tắc thiết kế chính? Quy trình? Kiểm thử/xác thực ra sao? Đo lường bằng gì?

### 4.8 Câu hỏi phỏng vấn user theo The Mom Test

Hỏi về hành vi quá khứ, không hỏi ý kiến về ý tưởng.

Nên hỏi: Lần gần nhất bạn gặp vấn đề này là khi nào? / Khi đó bạn đã làm gì? / Mất bao lâu, tốn bao nhiêu? / Đã thử giải pháp nào khác? / Vì sao giải pháp hiện tại chưa đủ tốt? / Nếu không được giải quyết, hậu quả là gì?

Tránh hỏi: Bạn có thích app này không? / Có dùng nếu mình build không? / Muốn feature gì? / Có trả tiền không?

Tìm hành vi thật: đã trả tiền, đã tự hack workaround, đã than phiền nhiều lần, đã mất thời gian đáng kể.

---

## 5. Phase 2 — Solution Design và PRD

### 5.1 MVP Mindset: THINK → BUILD → TEST → LEARN

> **"NGHĨ ĐÚNG, XÂY ĐỦ, TEST NHANH, HỌC SỚM."**

1. **THINK**: xác định đúng vấn đề, đúng người dùng, đúng giả định cần validate (Double Diamond ở đây). Bắt đầu vòng Lean luôn từ THINK.
2. **BUILD**: MVP đủ để kiểm tra 4 rủi ro của mô hình kinh doanh — không thiếu, không thừa, vừa đủ để học.
3. **TEST**: đưa ra thật, đo kết quả thật, nghe feedback thật từ user thật — không phải bạn bè nịnh.
4. **LEARN**: giả định đúng → scale; sai → pivot hoặc học tiếp. Không có gì là thất bại nếu học được.

### 5.2 Từ problem sang solution

```text
Tôi muốn giúp [WHO — user nào?]
giải quyết nhu cầu [WHAT — động từ]
bằng cách [HOW — giải pháp ĐÁNH THẲNG vào root cause được chọn]
để họ đạt được [OUTCOME]
mà không còn phải [OLD WORKAROUND].
```

Ràng buộc quan trọng: HOW phải nối trực tiếp với root cause từ 5 Whys — không phải giải pháp chung chung. Nguyên tắc sáng tạo: "Đừng thiết kế lại cái đã có rồi — nó cần phải TỐT HƠN cái cũ."

### 5.3 Scoping MVP

**"PRD không khó, khó là ở scoping MVP — một tính năng nhỏ, nhưng đủ dùng được, đủ để kiểm chứng."** Câu mở đầu mỗi vòng chọn scope: *"Sprint này ăn gì? Vấn đề này cần build MVP gì?"*

**Quy tắc xe đạp** (chống MESS): sau Solution Reframing, phân rã thành nhiều **Use Case** → **chọn đúng 1 Use Case và làm TRỌN VẸN chuỗi user story của nó** (~80% use case đó), thay vì rải mỗi use case một ít story.
- MESS = ô tô không bánh xe — nhiều mảnh, không chạy được. ✗
- MVP = xe đạp — thô nhưng chở người được. ✓

Ví dụ cây phân rã (app in nhãn): Solution "cho nhập hàng loạt số nhãn để in nhanh hơn" → UC1 Scan barcode / **UC2 In hàng loạt qua input hàng loạt (chọn)** / UC3 Mass import Excel → UC2 gồm US1 Input nhãn hàng loạt → US2 Tinh chỉnh nhãn → US3 In.

```markdown
## MVP Test Definition
- Giả thuyết cần kiểm chứng:
- User mục tiêu:
- Hành vi chứng minh giả thuyết đúng:
- Hành vi chứng minh giả thuyết sai:
- Use case được chọn (làm trọn vẹn):
- Feature cố tình không làm:
- Thời gian test:
- Số user test tối thiểu:
```

Rule thực tế: MVP >3 feature chính = quá rộng. Không chỉ ra được giả thuyết cần test = chưa phải MVP. User không tự chạm tới value = mới chỉ là prototype nội bộ.

### 5.4 PRD — 5 cấu phần lõi, mở rộng thành 7 phần

5 cấu phần tối thiểu ("5 câu thần chú" — dùng khi cần PRD nhanh): **1. Problem Statement** (vấn đề là gì?) · **2. Goals & Metrics** (thành công trông thế nào?) · **3. Target User** (ai dùng, hoàn cảnh nào?) · **4. Features + Scope** (build gì, KHÔNG build gì?) · **5. User Stories + Flow** (tương tác thế nào?).

Bản đầy đủ 7 phần:

```markdown
# PRD — [Tên sản phẩm / feature]

## 1. Context & Problem
- Problem Statement:
- Root cause:
- Evidence:
- Current workaround:

## 2. User & Jobs To Be Done
- Primary user:
- Situation:
- Job:
- Pain:
- Desired outcome:

## 3. Goals & Metrics
- Product goal:            (khuyến khích có số, vd "giảm 80% thời gian nhập tay")
- Business goal:
- North Star Metric:
- Input metrics:
- Guardrail metrics:

## 4. MVP Scope
### In scope (1 use case trọn vẹn)
### Out of scope
### Assumptions

## 5. User Stories (mỗi story đủ 4 khối)
### Story N: [tên]
- **User Role**:
- **Goal**:
- **User Flow**: (các bước đánh số)
- **Acceptance Criteria**: (tiêu chí ĐỊNH LƯỢNG, pass/fail được)

## 6. User Flow & Aha Moment
- Entry point:
- Step-by-step flow:
- Aha moment:
- Failure points:

## 7. System, Data & Risks
- Data entities:
- Integrations:
- Permissions:
- Risks:
- Open questions:

## 8. UI/UX Theme (tuỳ chọn — giúp tool sinh UI nhất quán)
- Color Palette: Primary #… / Secondary #… / Accent #…
- Brand Personality: 3-5 tính từ (vd: Professional, Efficient, Minimalist)
```

**Acceptance Criteria là thứ giúp AI build đúng và giúp test sau build.** Mẫu AC chuẩn (số hoá, pass/fail): "Hỗ trợ upload tối đa 10MB/file" · "Sinh ít nhất 5 câu hỏi mỗi bài giảng" · "Câu hỏi 4 phương án: 1 đúng/3 sai" · "Support tối thiểu 30 product codes/batch" · "Validate 100% codes với database" · "File naming `[ProductCode]_[Language].lb`".

Ghi chú: thị trường còn có SRS/BRD (kiểu Atlassian có Priority Must-Have/Should-Have) — playbook chọn PRD gọn vì mục tiêu là nói chuyện với AI; có thể mượn cột Priority cho user stories.

### 5.5 Definition of Ready

Trước khi đưa PRD cho AI build, phải trả lời được:

- User là ai, không nói chung chung.
- Need là ĐỘNG TỪ, không phải tên feature.
- MVP test giả thuyết nào.
- User flow có điểm bắt đầu và kết thúc.
- Aha moment nằm ở bước nào.
- Success metric đo được bằng số.
- Mỗi user story có Acceptance Criteria pass/fail được.
- Có danh sách out-of-scope.
- Có data cần lưu và quyền truy cập.

---

## 6. Phase 3 — Design, Aha Moment và Prototype

### 6.1 Design tốt = "dắt" mà user không nhận ra

> **"Design tốt là dắt được người dùng đi từ chỗ đang đau đến chỗ hết đau — mà họ KHÔNG nhận ra là mình đang được/bị dắt."**

- Đẹp ≠ tốt: đẹp về thẩm mỹ vẫn có thể fail về Usability.
- Design bắt đầu từ nỗi đau (của cả User LẪN Business), không bắt đầu từ màu/font/style.
- Design Thinking là **vòng xoáy, không phải đường thẳng** — mỗi vòng lặp là một lần hiểu nỗi đau sâu hơn. **Điểm neo duy nhất: khi rối, quay về Problem Space để chỉnh hướng.**

Ba tầng trải nghiệm (3 lớp lồng nhau, không phải 3 nghề — UI ⊂ UX ⊂ CX):

| Tầng | Nghĩa |
|---|---|
| **UI** | Cái user **nhìn thấy** — màu, nút, layout của 1 màn hình |
| **UX** | Cái user **cảm thấy** khi đi qua nhiều màn hình để đạt outcome |
| **CX** | Cái user **nhớ lại** sau khi rời sản phẩm — cả mối quan hệ theo thời gian |

**Dắt lộ liễu vs Dắt khéo** (anti-pattern checklist):

| ❌ Dắt lộ liễu (dark pattern) | ✅ Dắt khéo |
|---|---|
| Popup ép đăng ký ngay khi vào | Mỗi bước user tự thấy "ồ, cái này giúp mình rồi" |
| Checkbox mờ auto-subscribe | **Value xuất hiện TRƯỚC khi yêu cầu cam kết** |
| Countdown giả tạo áp lực | Flow dẫn tới Aha tự nhiên |
| Nút "Từ chối" bé/mờ, "Đồng ý" to/nổi | User tự đi tiếp vì muốn |
| → User tỉnh ra, thấy bị lừa, bỏ đi | → Tin tưởng → dùng tiếp → giới thiệu |

### 6.2 Aha Ladder

```text
Problem (đang khổ với vấn đề cụ thể)
-> Aha 1: "Ồ, cái này hiểu mình."      (đúng ngôn ngữ, đúng bối cảnh)
-> Aha 2: "Ồ, nó làm được thật."       (tự tay làm, thấy kết quả thật)
-> Aha 3: "Mình không muốn quay lại cách cũ."  (point of no return, thói quen mới)
-> Adoption: vào vòng lặp giá trị — NƠI RETENTION BẮT ĐẦU.
```

- **Không có Aha = Không có Story.** Không xác định được Aha của một story → story đó có thể chưa cần làm.
- **FREQUENCY matters**: Aha cài trong nhu cầu có tần suất lặp cao → user "nghiện một cách vô thức", quay lại khi gặp vấn đề lần nữa.
- Ví dụ kinh điển: Notion — kéo-thả khối đầu tiên → "không phải Word"; Figma — mở link thấy người khác chỉnh cùng lúc → "hết gửi file"; ChatGPT — câu trả lời đầu tiên đúng ngữ cảnh → "không phải Google".
- Lưu ý chiến lược: design tốt còn phụ thuộc mô hình kinh doanh (case Rophim vs Netflix: đối thủ không làm được vì ràng buộc bản quyền hoặc vì "kiếm tiền vừa đủ" nên không đầu tư trải nghiệm).

### 6.3 Ba mức zoom — phễu Journey → Story → Flow → Aha

Mỗi tầng zoom là một lần thu hẹp, đến khi chỉ đúng 1 điểm nơi Aha xảy ra:

| Đặc điểm | Customer Journey (zoom xa) | User Story (zoom vừa) | User Flow (zoom gần) |
|---|---|---|---|
| Trọng tâm | Cảm xúc & trải nghiệm tổng thể | Nhu cầu & giá trị tính năng | Logic & các bước thao tác |
| Góc nhìn | Khách hàng (ngoài hệ thống) — cả TRƯỚC khi tiếp cận sản phẩm | Vai trò người dùng cụ thể | Hệ thống (trong sản phẩm) |
| Câu hỏi chính | Họ cảm thấy thế nào? | Họ muốn làm gì và tại sao? | Họ đi đâu tiếp theo? |
| Định dạng | Map | Câu ngắn "As X, I want Y, so that Z" | Flowchart |

### 6.4 Customer Journey template + Rule vàng

```markdown
## Customer Journey
| Stage | User context | Emotion | Goal | Touchpoint | Aha | Risk |
|---|---|---|---|---|---|---|
| Awareness | | | | | | |
| First Try | | | | | | |
| Onboarding | | | | | | |
| Repeat Use | | | | | | |
| Referral | | | | | | |
```

Với MỖI giai đoạn hỏi: Aha là gì? Feature nào tạo Aha? Nếu Aha không xảy ra thì sao? **Rule vàng: không nghĩ ra Aha cho một giai đoạn = chỗ MVP đang yếu nhất.**

Khái niệm "**điểm rơi nguy hiểm**": drop-off ngay TRƯỚC Aha 1 (vd Notion: blank page lúc thử lần đầu — choáng, không biết bắt đầu). Ghi rõ vào cột Risk.

### 6.5 User Flow + audit số bước tới Aha

> **"Càng ít bước trước Aha moment càng tốt. Mỗi bước thừa là một cơ hội user bỏ đi."**

```markdown
## User Flow — [Story name]
Entry point:
Steps:
1. User...
2. System...
Aha happens at step:
Possible drop-off:
How to reduce steps before Aha:
```

Quy trình audit flow 4 bước (dùng cho mọi sản phẩm): (1) đọc story + flow, hiểu mục tiêu và Aha kỳ vọng → (2) xác định **bước thừa** — bước không đóng góp vào việc dẫn tới Aha, có thể gộp/bỏ → (3) vẽ lại flow giảm số bước, đảm bảo Aha vẫn còn và xuất hiện SỚM HƠN → (4) reflection: Aha có chuyển vị trí không, mạnh hơn hay yếu hơn?

Worked example Grab: 3 nỗi đau taxi (không biết bao giờ xe đến / không biết giá trước / phải đứng vẫy xe) → Aha một câu đo được: **"Biết chính xác giá và thời gian xe đến ngay khi nhấn nút."**

### 6.6 Prototype strategy

> **Prototype = phiên bản "xấu-nhưng-đủ" của MVP. Cân nặng của prototype tỉ lệ nghịch với tốc độ học: càng đẹp → càng chậm → càng ít vòng lặp → càng ít học. Hoàn thiện quan trọng hơn hoàn hảo.**

| Câu hỏi cần học | Prototype phù hợp |
|---|---|
| User có hiểu concept không? | Sketch, wireframe, static UI |
| **Aha moment có đúng vị trí không?** | **UI Only (AI gen, chưa có logic)** |
| Flow có dễ dùng không? | Clickable prototype |
| Logic có chạy được không? | Functional UI (Logic Integrated) |
| Data có cần lưu thật không? | Backend/database integrated MVP |

**Quy tắc học tool prototype** (Lovable, v0, Figma Make, Canva Code, Bolt, Claude Artifacts, Google AI Studio — đều dễ dùng cho non-tech):
- Dùng tối thiểu **2 tool** để so sánh — "1 tool = dính vào 1 tool; so sánh là cách duy nhất hiểu tool landscape".
- Mỗi tool chỉ prompt **1 màn hình** — đừng cố làm cả app.
- **Sửa prompt tối thiểu 3 lần** rồi mới đánh giá tool; ghi lại prompt cuối.
- Tiêu chí đánh giá: "mình có DẮT được nó không?"
- "Tool chỉ hiển thị mô phỏng suy nghĩ con người, không thay thế sáng tạo nguyên bản của người làm sản phẩm."

---

## 7. Phase 4 — System Thinking, Data và Architecture

### 7.1 Bốn tầng nhìn sản phẩm (iceberg)

"Above the surface: bình thản. Below the surface: đạp nước điên cuồng." — app đẹp trên mặt nước, hệ thống bên dưới vận hành dữ dội.

| Tầng | Tên | Trả lời | Output |
|---|---|---|---|
| **L0** | Intent & Outcome | Vì sao, cho ai, kết quả gì? | Problem Statement |
| **L1** | Business Flow | Ai làm gì theo trình tự nào? | BPMN / swimlane |
| **L2** | User Flow | User bấm đâu, thấy gì? | User flow |
| **L3** | System & Data | Hệ thống chạy và lưu gì? | Architecture + ERD |

**Business Flow (L1) tốt phải có**: (a) happy path; (b) **timer/timeout** (15 phút chưa có hàng thì sao?); (c) **hành vi phản ứng của actor** (khách hỏi "Where is my pizza?" → nhân viên "Calm Customer"); (d) luồng tiền/biên nhận tách khỏi luồng hàng.

### 7.2 Giải phẫu hệ thống — 6 khối + 2 cầu nối

Một app chạy được là chuỗi 6 khối nối nhau:

| Khối | Là gì |
|---|---|
| **Client** | Người dùng cuối + thiết bị của họ (laptop/điện thoại/tablet) — client-side |
| **Front End** | Phần mắt thấy – tay chạm; HTML/CSS/JavaScript (React, Vue…) |
| **Back End** | Bộ não logic đứng sau giao diện: nhận từ FE → xử lý → trả kết quả; gọi API, tương tác DB |
| **Server** | Máy tính (vật lý/ảo) chạy backend, lưu code — AWS, Vercel, local |
| **Database** | Nơi lưu dữ liệu lâu dài; backend đọc/ghi/cập nhật |
| **Application (BaaS)** | Dịch vụ backend làm sẵn (Supabase/Firebase): Auth, Database, API/Server Logic, Storage, Trigger/Event Hooks, Analytics/Logs, Row Level Security |

Hai cầu nối: **API** = pull — "hệ thống A chủ động gửi request lấy thông tin từ B" (fetch data, create record, update status). **Webhook** = push — "hệ thống B tự động gửi dữ liệu đến A khi có sự kiện" (payment success, form submitted, new message).

### 7.3 Blackbox thinking

```text
Input -> Processing -> Output
```

Khi không hiểu kỹ thuật, mô tả bằng ngôn ngữ này: Input user đưa vào là gì? / Hệ thống xử lý gì? / Output nhận lại là gì? / Dữ liệu nào cần lưu? / Dữ liệu nào gửi sang hệ thống khác? / Điều gì xảy ra khi lỗi?

Mental model từ sản phẩm thực (để auth/token/session không còn là ma thuật):
- Đằng sau nút "Login with Facebook": browser redirect → authorization server hiện permission form → user đồng ý → app nhận **authorization code** → đổi lấy **access token** → dùng token truy cập resource; từ chối → "resource not available".
- Đằng sau app đặt xe: đăng ký → verify với DB → **session key** → mỗi thao tác là 1 vòng request/response (tính fare, tìm driver) → logout = destroy session.

### 7.4 CRUD ↔ HTTP Methods

| CRUD | HTTP | Nghĩa |
|---|---|---|
| **Create** | POST | Tạo record mới |
| **Read** | GET | Xem record |
| **Update** | PUT/PATCH | Sửa record |
| **Delete** | DELETE | Xoá record |

Nếu PRD không chỉ ra CRUD cho từng entity, AI rất dễ thiết kế database sai. Biết mapping này → đọc được network tab/log và viết API spec cho AI.

### 7.5 Thang database 4 cấp (chọn theo ngưỡng, không chọn theo mốt)

| Cấp | Tool | Ưu | Nhược / ngưỡng |
|---|---|---|---|
| 🥚 Trứng | Google Sheet | Dễ nhập, dễ sửa | Dễ mất access & bị hack; chậm sau ~10.000 records |
| 🐛 Sâu | Airtable | Visual đẹp | Khó scale: 1.000 record free, trả phí ~100.000 |
| 🛡 Nhộng | Supabase 1 bảng | Robust, secure, scalable — hàng tỷ record | Khó học hơn |
| 🦋 Bướm | Supabase relational | Chuẩn cho real development | Khó học và nhập liệu nhất |

Rule: bắt đầu ở cấp thấp nhất đủ cho bài test MVP; nâng cấp khi chạm ngưỡng record/bảo mật/quan hệ dữ liệu.

### 7.6 ERD — 3 mức

**Conceptual** (chỉ entity + quan hệ — cho thảo luận nghiệp vụ) → **Logical** (thêm thuộc tính + cardinality 1-N/N-M) → **Physical** (bảng thật với field, kiểu dữ liệu — cái để sinh SQL). Prompt cho AI phải nêu rõ cần mức nào.

```markdown
## Data Model
### Entities
| Entity | Purpose | Key fields | Owner |
|---|---|---|---|

### Relationships
- user has many ...

### Permissions
| Entity | Who can create | Who can read | Who can update | Who can delete |
|---|---|---|---|---|
```

### 7.7 Prompt tạo L1-L3 (actors-first, 2 bước)

```text
Dựa trên user stories sau:
[paste user stories từ PRD]

Hãy làm theo thứ tự:
1. Liệt kê các ACTOR bạn xác định được từ user stories trên. (Dừng cho tôi review.)
2. Vẽ BPMN swimlane bằng Mermaid cho flow chính: happy path + 2 edge case
   quan trọng nhất (timeout, hành vi phản ứng của actor).
3. Viết L2 user flow cho MVP.
4. Đề xuất L3 system/data flow: entities, CRUD, API/webhook cần có.
```

### 7.8 Bài thực hành chuẩn + Gate

Chuỗi 3 bước: (1) Nhờ AI vẽ L3 cho sản phẩm của bạn → (2) Từ L3, yêu cầu AI sinh ERD cho database → (3) Kết nối vào Supabase.

**Gate cứng**: *"Nếu không có database & backend logic, app của bạn chỉ dừng ở level Prototype (UI logics), chưa phải một functional app thực thụ."*

---

## 8. Phase 5 — Build, Deploy và Security

### 8.1 Flow khuyến nghị + nguyên tắc tách bước

```text
PRD -> UI mockup (Stitch) -> FE logic (AI Studio) -> ERD -> SQL -> Supabase
    -> FE connects DB -> GitHub -> Vercel -> User test
```

**Tách UI khỏi logic — 2 tool, 2 bước**: Stitch (hoặc tương đương) = **UI only** — design tĩnh để NHÌN THẤY sản phẩm trước. AI Studio (hoặc tương đương) = **UX + FE logic** — gen code chạy được từ PRD + design reference. Lý do: "Tách 2 bước → kiểm soát tốt hơn, sửa từng phần dễ hơn. Gộp 1 bước → AI đoán mò, rất khó sửa từng màn hình nhỏ." Công thức: `PRD + Stitch design → AI Studio → code chạy được`.

**Ma trận phân vai** — "Bạn là nhạc trưởng, AI + Tool là nhạc công. Biết ai làm gì là kỹ năng quan trọng nhất của product builder hiện đại":

| Vai | Việc |
|---|---|
| 👤 **Bạn** | Viết PRD rõ ràng; review & chỉnh design; connect keys đúng chỗ; chạy checklist bảo mật |
| 🤖 **AI** | Gen UI từ PRD; gen ERD từ requirements; gen SQL CREATE TABLE; gen code FE logic |
| 🛠️ **Tool** | Supabase — chứa data; GitHub — chứa code; Vercel — chạy app; `.env` — bảo vệ key |

### 8.2 Tool role

| Việc | Tool thường dùng | Output |
|---|---|---|
| Think (brainstorm, PRD, 4 risks) | AI Chat: ChatGPT, Claude, Gemini | Artifact tư duy |
| UI mockup | Stitch, v0, Figma AI/Make, Lovable | Design/reference |
| FE logic | AI Studio, Lovable, Bolt, IDE agent | App chạy được |
| Database | Supabase, Airtable, Google Sheet (theo thang 4 cấp §7.5) | Data lưu thật |
| Code storage | GitHub | Repo có lịch sử |
| Deploy | Vercel | URL public |
| Automation | Make, scripts, MCP | Workflow tự động |

### 8.3 Database: prompt chain có human-review ở giữa

Không gộp 1 prompt lớn. Chain 2 bước, review giữa mỗi bước:

1. `"Từ PRD này, vẽ ERD cho mình"` → AI suy ra entity → **bạn review, sửa, chốt ERD** (chưa chốt thì không đi tiếp).
2. `"Từ ERD này, viết SQL CREATE TABLE"` → review SQL → paste vào Supabase.

Nguyên lý: "PRD đủ để gen ERD; ERD là hình vẽ, SQL mới chạy được."

**Supabase** = Postgres + Auth + Storage + API trong 1 dashboard; free tier đủ cho MVP, không cần cài gì trên máy. Thao tác: **SQL Editor** → paste SQL → **Run** → verify bảng trong **Table Editor**. Kết nối FE cần đúng 2 giá trị tại **Settings → API**: **Project URL** + **Anon Key**.

Checklist Supabase MVP:
- Project đã tạo; có ERD trước khi tạo bảng; SQL được review trước khi chạy.
- Bảng có primary key; có `created_at`/`updated_at` nếu cần tracking.
- RLS được bật cho bảng public-sensitive — **đừng mặc định RLS đã đúng chỉ vì dùng Supabase**.
- App dùng anon key; KHÔNG dùng service role key ở frontend.
- Test insert/read/update/delete tối thiểu.

### 8.4 Git & GitHub cho non-tech

4 khái niệm cốt lõi: **Repo** = thư mục được Git theo dõi · **Commit** = ảnh chụp tại 1 thời điểm · **Branch** = nhánh song song (như đa vũ trụ Marvel) · **Merge** = gộp nhánh về main. Analogy: "Git = Google Docs history cho code — mỗi save = 1 version, tua ngược bất cứ lúc nào." GitHub = Git trên mây: backup, share, collab, và **làm nguồn cho deploy**.

Mức tối thiểu cần biết: tạo repo, commit & push (qua tool cũng được). **Cảnh báo: đừng chỉ rely vào version history của web tool — phải có repo GitHub riêng.** Flow không cần CLI: download code từ tool → tạo repo qua web UI → upload (drag & drop / GitHub Desktop) → verify.

Checklist GitHub:
- Repo đúng project, **không upload nhầm folder cha**.
- Có `.gitignore`; `.env` nằm trong `.gitignore`; không commit `node_modules`.
- Không commit file chứa secret/key/token.
- Commit message mô tả thay đổi rõ.

### 8.5 Vercel & Deploy

Analogy: Code = bản thiết kế nhà · Host = mảnh đất dựng nhà thật · URL công khai = địa chỉ nhà.

- Cơ chế: **connect GitHub repo 1 lần duy nhất** → từ đó mỗi push, Vercel tự **Pull → Build → Deploy** ("Push to deploy").
- **Preview Deployment**: mỗi branch = 1 URL riêng. Main → production URL; feature branch → preview URL — test feature an toàn trước khi merge.
- URL mặc định `your-app.vercel.app`; custom domain ~2 phút setup.

Checklist Vercel: repo đã connect; build command + framework đúng; **env vars đã set trong dashboard**; production URL mở được trên điện thoại; sau deploy test lại flow chính với data thật.

### 8.6 Security tối thiểu — "Key = tiền"

Chuyện thật: một dev leak AWS key lên GitHub public → **bot quét GitHub 24/7** → key bị dùng chạy crypto → **charge $50.000 trong 1 đêm**.

| Loại key | Analogy | Đưa vào frontend? | Ghi chú |
|---|---|---:|---|
| Supabase anon key | 🔑 Chìa nhà | Có, nếu RLS đúng | Public-safe tương đối |
| Supabase service role key | 🔐 Chìa két sắt | **KHÔNG** | Quyền admin full DB — chỉ sống ở dashboard Supabase |
| API key trả phí | 🔐 | Không | Đưa vào env/server/proxy |
| OAuth secret | 🔐 | Không | Không commit, không paste bừa vào chat |

Quản lý key: ❌ `const KEY = "abc123"` (push = lộ ngay cho toàn thế giới) → ✅ `const KEY = process.env.KEY` (key sống ngoài code). Hai nơi đặt: **Local = `.env` được `.gitignore` che; Production = Vercel Dashboard → Environment Variables**. `.gitignore` là **chốt chặn cuối cùng**.

**Checklist trước khi push GitHub** ("làm đúng checklist này = tốt hơn 80% dev/vibe coder mới"):
- [ ] Đã có `.gitignore` trong project?
- [ ] `.env` nằm trong `.gitignore` chưa?
- [ ] Không có key nào hardcode trong code, trên repo?
- [ ] Service role key chỉ ở dashboard Supabase, không ở đâu khác?
- [ ] Đã set Environment Variables trên Vercel Dashboard?

Nếu lỡ commit secret: (1) Revoke key ngay trong dashboard → (2) Tạo key mới → (3) Xoá khỏi code → (4) Kiểm tra git history nếu repo public → (5) Set env vars lại.

**Checklist Sản Phẩm Sẵn Sàng Public** — tick hết 5 ô = MVP thật:
- [ ] App có URL Vercel live, mở được từ điện thoại
- [ ] DB Supabase có bảng đúng ERD, có data thật
- [ ] GitHub repo clean, không leak key nào
- [ ] `.gitignore` đúng, `.env` không bị push
- [ ] Key đã ở Vercel Environment Variables

---

## 9. Phase 6 — AI Agent Workflow

### 9.1 Tool vs Agent — và 3 cấp độ dùng AI

"AI is the first technology in our history that can create ideas of its own. It's not a tool but rather an agent." (Harari, *Nexus*)

| | TOOL | AGENT |
|---|---|---|
| Hành vi | Bảo gì làm nấy, không tự tư duy (búa, Excel) | Hiểu ngữ cảnh, phản biện, đề xuất |
| Đầu ra | Phụ thuộc 100% nỗ lực của bạn | Tự tạo ý tưởng, giao tiếp bằng ngôn ngữ người |

**Luật: đối xử với AI như công cụ → nhận kết quả của công cụ. Đối xử như đồng đội → nhận kết quả của chuyên gia.**

| Cấp | Cách dùng | Khi nào đủ |
|---|---|---|
| 1 — Hỏi đáp (Q&A) | Như Google thông minh — đa số người dùng KẸT ở đây | Học khái niệm |
| 2 — Cộng tác | Brainstorm, review, phản biện 2 chiều | Discovery, PRD, design |
| 3 — Ủy quyền | Giao task để AI đọc/sửa file/chạy lệnh, tự plan và thực thi | Build, debug, refactor, deploy |

Mục tiêu của solo builder: dịch chuyển từ cấp 1 lên cấp 2 & 3. Ranh giới cứng: **AI không chọn hướng đi cuối cùng — judgment và vision là của bạn.**

### 9.2 Giải phẫu Agent: Model / Agent / IDE

- **Model (LLM) = Não**: Claude/GPT/Gemini — bộ não thuần, chỉ đọc + viết text. Giới hạn: knowledge cutoff, trả lời chung chung khi thiếu ngữ cảnh, mất trí nhớ giữa session, hallucinate.
- **Agent = Não + tay chân + vòng lặp**: Model + quyền dùng tool (đọc/sửa file, chạy terminal, mở browser) + vòng lặp tự động. Mỗi khung chat là 1 agent; chọn model trong chat = chọn não cho agent đó.
- **IDE = Cơ thể/host**: cái vỏ cung cấp tay chân — không tự thông minh. "IDE chỉ là cái vỏ đèn; sức mạnh nằm ở vị thần đèn (AI model) bên trong."

4 thành phần của agent: **Intelligence** (não) · **Tools** (web search, đọc file, MCP, bash) · **Memory** (ngắn hạn/dài hạn) · **Knowledge** (dữ liệu ngữ cảnh dự án).

6 việc IDE agent làm được mà web chat không thể: đọc & sửa file trực tiếp; chạy terminal (tự chạy lệnh → đọc lỗi → tự sửa theo vòng lặp); mở browser kiểm tra UI; tự commit git + viết message; truy cập internet đọc docs; điều khiển bằng giọng nói.

### 9.3 Khi nào rời web tool sang IDE

Chuyển sang IDE khi gặp BẤT KỲ dấu hiệu nào:
1. Chat dài → agent "lú", lặp lỗi cũ, quên những gì đã sửa.
2. Không biết code nằm file/folder nào — không debug được.
3. Thêm feature phức tạp phải paste lại context từ đầu.
4. Muốn đổi/sắp xếp lại requirement mà web interface không cho làm.

Ẩn dụ: **"Dòm khe cửa vs. Đứng trong bếp"** — web tool = đưa mẩu giấy cho đầu bếp qua khe cửa, chỉ chờ món ra; IDE + agent = bước thẳng vào bếp, chỉ vào nồi "thêm muối chỗ này, bớt lửa nồi kia". Đầu bếp vẫn là agent, bạn vẫn không tự nấu — nhưng bạn thấy bếp, chỉ đúng chỗ, sửa ngay khi sai.

**Vòng lặp Git nối web tool và IDE**: MVP build trên web → deploy Vercel → `git clone/pull` về máy → agent local sửa (đọc toàn bộ codebase như Senior Dev) → `git push` → Vercel tự cập nhật live.

Clone repo 4 bước: copy HTTPS URL (nút Code) → `git clone <url>` → Open Folder **đúng thư mục vừa clone — KHÔNG mở folder cha** → verify file tree thấy `src/`, `package.json`. **Luật: 1 project = 1 folder root = 1 cửa sổ IDE.**

Giao diện IDE 4 vùng: File Tree (trái) · Editor (giữa — diff: **xanh = thêm, đỏ = xoá**) · Agent Panel (phải — task, plan, accept/reject) · Terminal (dưới — lỗi build hiện ở đây).

IDE vs CLI: IDE (Antigravity…) trực quan, hợp người mới + task UI. CLI (Claude Code, Codex CLI) mạnh hơn cho task lớn nhiều file. Chiến lược chi phí (tham khảo, giá đổi nhanh): FREE → dùng IDE có free quota; ~20 USD → ưu tiên trả cho **planning** (Claude); execution tiết kiệm → Cursor; ngân sách lớn → gói Max cho execution nặng.

### 9.4 Workflow với IDE agent — "Captain quyết"

> "Bạn không còn làm tay theo lời AI — bạn bảo AI thao tác và duyệt kết quả. Agent thực thi, bạn review diff, accept/reject có chủ đích. **Đừng bao giờ duyệt mù quáng.**"

```text
1. Chỉ rõ mục tiêu
2. Chỉ rõ file hoặc khu vực liên quan
3. Bắt AI lập plan ngắn (planning mode) — approve plan rồi mới cho execute
4. Cho AI sửa
5. Review diff
6. Chạy test/build — bắt AI đóng vai QA tự phát hiện lỗi
7. Sửa lỗi nếu có
8. Commit
9. Push/deploy
10. Test URL live
```

Tiêu chí hoàn thành: "Không cần feature hoàn hảo — quan trọng là hoàn thành 1 vòng: giao việc → review → commit → push → live."

### 9.5 Quy tắc giao task + Reject playbook

Nên: một chat cho một mục tiêu · task nhỏ, output rõ · chỉ định file nếu biết · bắt AI giải thích trade-off trước khi sửa lớn · review diff trước khi accept · mở nhiều chat song song cho các task độc lập · lưu PRD vào `docs/` trong repo để agent đọc được.

Không nên: giao "làm app tốt hơn" không có metric · cho AI sửa toàn repo khi chỉ cần sửa 1 màn hình · accept diff khi chưa hiểu thay đổi nghiệp vụ · thêm dependency mới mà không hỏi lý do · chat quá dài rồi cố vá bằng nhiều context hơn.

**Reject cũng là skill — 4 trường hợp reject:**
1. Agent đề xuất sửa 10 file → reject, yêu cầu chỉ sửa 1.
2. Agent đổi cả logic nghiệp vụ khi chỉ cần sửa UI → reject.
3. Diff có code lạ không hiểu → reject, hỏi giải thích trước.
4. Agent thêm dependency không cần thiết → reject.

Cách reject đúng: đừng chỉ bấm Reject — giải thích ngắn tại sao. Ví dụ: *"Reject — chỉ sửa file Home.tsx thôi, đừng đụng vào các component khác."* **Reject có hướng dẫn = kết quả tốt hơn ở lần sau.**

### 9.6 Context & Token Management

**Context window = "RAM của AI"** — giới hạn lượng text AI nhớ trong 1 phiên. Mọi thứ đều tốn token: tin nhắn, file agent đọc, kết quả tool, CLAUDE.md, lịch sử chat. Token = bộ nhớ + TIỀN (~0.75 từ EN/token; tiếng Việt tốn nhiều token hơn).

Ẩn dụ cốc nước: Context = cái cốc, token = nước. Cốc đầy → thông tin cũ tràn ra → agent quên đầu chat → lặp lỗi, "tưởng tượng" code không có (hallucinate rất tự tin).

**5 Rule Vàng quản lý context:**
1. **CLAUDE.md/AGENTS.md ngắn gọn**: 5-15 bullet, đừng 500 dòng — mọi agent đọc nó MỖI lần vào.
2. **1 chat = 1 mục đích**: xong task → `/clear` hoặc chat mới. Đừng gộp nhiều task trong 1 thread.
3. **Chỉ đích danh file**: "Sửa `src/pages/Home.tsx`" thay vì "sửa trang chủ". Đừng bắt agent đọc cả repo.
4. **Chia task nhỏ**: 1 task nhỏ → agent focus → kết quả tốt hơn.
5. **Thấy lặp sai → Reset ngay**: đừng cố "giải thích lại" trong chat cũ — giải thích = thêm token = cốc càng đầy. Tóm tắt trạng thái → mang sang chat MỚI → giao task nhỏ hơn.

**Context Management > Prompt Management**: prompt chỉ là một cách nén context; nhiều lượt chat chất lượng > 1 prompt hoàn hảo. Kỹ thuật **meta-prompting**: chat để nạp context cho AI, rồi nhờ chính AI viết prompt hoàn chỉnh đem sang chat/AI khác. Fix nền: dùng System Instructions (briefing trước khi làm việc) để giữ role/định dạng không trôi.

### 9.7 CREATE prompt framework (Dave Birss)

Đối xử AI như actor, brief AI như đạo diễn brief diễn viên:

```text
C — Character: AI đóng vai gì? ("product strategist 10 năm kinh nghiệm")
R — Request: Nhiệm vụ cụ thể là gì?
E — Examples: Output mẫu hoặc ví dụ tốt/xấu?
A — Adjustments: Ràng buộc, giới hạn? ("không dùng jargon")
T — Type of output: Bảng, checklist, markdown, code?
E — Extras: Ngôn ngữ, tone, context bổ sung?
```

Mẫu số chung mọi framework prompting: **Who** (vai trò) + **What** (đầu bài) + **Why** (context) + **How** (hình dung output mẫu). Shortcut khi không nhớ framework: tự hỏi **"Mình đã cho AI đủ context chưa?"** Vòng lặp iteration: Viết prompt → Chạy & đọc kỹ output → Sửa prompt dựa trên output → Lặp lại. "Prompt giỏi < chỉnh sửa nhiều lần."

### 9.8 Điểm mù — Known/Unknown, Dunning-Kruger và 3 câu hỏi

> "Nguy hiểm nhất không phải là không biết. Mà là TƯỞNG mình biết."

Ma trận Rumsfeld áp cho AI:

| Ô | Nghĩa | Hành động |
|---|---|---|
| Known Knowns | Biết mình biết | OK — tự verify được |
| Known Unknowns | Biết mình chưa biết | HỎI AI — vùng AI mạnh nhất |
| Unknown Knowns | Chưa biết mình đã biết | AI GIÚP khai quật kinh nghiệm |
| **Unknown Unknowns** | Chưa biết mình chưa biết | **DỄ BỊ LỪA** — vùng nguy hiểm nhất |

**Bẫy Dunning-Kruger × AI**: người biết ít → tự tin cao; AI thì **luôn tự tin 100% — ngay cả khi đang bịa**. Công thức: *"Sự thiếu hiểu biết của bạn + sự tự tin tuyệt đối của AI = công thức của thảm hoạ."* Tự tin của AI ≠ độ đúng.

**3 câu hỏi kéo Unknown Unknowns ra ánh sáng** — "cứu bạn khỏi 80% tai nạn khi dùng AI", hỏi trước khi chốt mọi output quan trọng:
1. "Cái này có assumption gì?"
2. "Cái này fail ở đâu?"
3. "Có gì mà mình chưa nghĩ tới không?"

### 9.9 Test & verify — đừng tin đèn xanh của chính agent

- TDD có "second act" nhờ AI: test là feedback loop để AI tự bắt lỗi, là "định nghĩa của done" mà agent không tự viết lại được.
- Nhưng TDD không phải thuốc tiên: viết test trước khi hiểu vấn đề = khoá design quá sớm; một spec test sai giờ được implement với TỐC ĐỘ AGENT — giả định sai bị nhân bản hàng loạt trước khi ai kịp nhận ra.
- Rule: **viết test cho cái đáng test**, không phải test để có cảm giác an toàn giả. Và **để một agent testing độc lập verify — đừng chỉ tin unit test do chính agent viết code tự nhuộm xanh.**
- Cả specs lẫn tests đều là tầng trung gian giữa ý định và code thật — càng nhiều tầng trung gian, càng nhiều chỗ để sự thật bị lệch. Giữ chúng mỏng.

---

## 10. Phase 7 — Skills, MCP và Scripts

### 10.1 Khung tư duy 3 câu hỏi (hỏi trước MỖI task mới)

| Câu hỏi | Công cụ |
|---|---|
| "Có quy trình lặp lại không?" — nếu đang giải thích cách làm **lần thứ 2** cho AI, đó là tín hiệu | **Skill** |
| "Cần AI chạm vào hệ thống ngoài?" (Gmail, DB, design tool, GitHub) | **MCP** |
| "Chuỗi cố định, không cần AI tự quyết?" | **Script** |

3 công cụ độc lập — dùng riêng hoặc kết hợp, không cái nào "trên" cái nào. Gọn: **Skills = SOP cho AI** (viết 1 lần, AI tự gọi đúng lúc) · **MCP = tay chân cho AI** (chạm ra thế giới thật) · **Script = automation bình dân** (non-tech cũng làm được).

> "Người thắng trong thời đại AI không phải người biết nhiều prompt nhất — là người biết **đóng gói tri thức**, **nối công cụ**, và **biến công việc lặp lại thành hệ thống**."

### 10.2 Skill

Skill = thư mục hướng dẫn đóng gói cho 1 loại việc lặp lại. Viết 1 lần, AI tự gọi khi cần. "Skill biến AI từ 'thợ làm tốt chỉ khi được hướng dẫn kỹ' thành 'đồng đội biết tự mở quy trình và làm tốt'."

```text
skill-name/
  SKILL.md      ← BẮT BUỘC: frontmatter + hướng dẫn
  scripts/      ← code phụ trợ (optional)
  references/   ← tài liệu mẫu, template (optional)
  assets/       ← ảnh, file mẫu (optional)
```

**3 thành phần nội dung**: **WHEN** (trigger — khi nào AI nên dùng; càng rõ AI càng tự load đúng lúc) · **HOW** (các bước + template — chính là SOP) · **OUTPUT** (đầu ra mong muốn: format, tên file, cấu trúc — AI biết "làm xong trông như thế nào").

**Anatomy SKILL.md** = YAML frontmatter (`name` ngắn + `description` — QUAN TRỌNG NHẤT, agent chỉ dựa vào đây để quyết định load; liệt kê trigger cả Anh lẫn Việt và cụm hội thoại tự nhiên) + body Markdown (step-by-step, ví dụ Input/Output, edge cases). Ví dụ frontmatter chuẩn:

```yaml
---
name: prd-architect
description: Use when writing a PRD, product spec, or system architecture document.
  Triggers on: PRD, product requirement, viết PRD, tạo PRD, system design,
  "I have an idea for", "help me spec out", "write requirements for".
---
```

**Progressive Disclosure — 3 tầng token** (analogy thư viện: nhìn gáy sách, mở sách khi cần):
1. **Discovery**: AI chỉ đọc name + description (~100 tokens).
2. **Activation**: đọc full SKILL.md khi quyết định dùng (<5.000 tokens → giữ SKILL.md dưới ~5k tokens, đẩy tài liệu nặng xuống `references/`).
3. **Execution**: load `scripts/`/`references/` CHỈ khi cần.

**Skill xịn = 3 chữ S** — "thiếu 1 trong 3, skill chưa xịn":
- **Self-trigger**: description đủ rõ để AI tự load đúng lúc — viết như viết cho người chưa biết gì về skill.
- **Self-contained**: copy sang repo trắng vẫn chạy — không phụ thuộc path cứng, biến môi trường ngầm.
- **Self-verify**: có bước kiểm tra thành công cuối skill — AI tự báo "làm xong và đúng" thay vì bạn check tay.

**3 con đường tạo skill**: (1) **skill-creator chính hãng** (Claude Code/Codex/Cursor đều có) — mặc định nên dùng, rủi ro gần như không; "đừng prompt tay viết skill khi đã có skill-creator". (2) Tự prompt agent viết — khi cần kiểm soát hoàn toàn; rủi ro sai spec/thiếu trigger. (3) Import từ cộng đồng — khi cần expertise cao; rủi ro mã độc + prompt injection.

**An toàn skill import — checklist 5 câu** ("skill ngoài mạng không khác gì code ngoài mạng — review như đồ ăn cho máy"): (1) Skill đọc/ghi file gì? (2) Có chạy lệnh shell không, lệnh gì? (3) Có gọi network/API ngoài không? (4) Tác giả là ai, repo có active không? (5) Có hợp workflow của mình không? — 5 rủi ro: mã độc trong script; prompt injection (bảo AI đọc/gửi file nhạy cảm); lỗi thời; tone lệch brand; lệnh nguy hiểm (`rm -rf`, force push).

**Vị trí lưu skill** — mỗi tool quét folder riêng lúc khởi động; "đặt sai folder = skill vô hình, dù viết hay đến đâu":

| Tool | Global (mọi project) | Repo (chỉ project này) |
|---|---|---|
| Claude Code | `~/.claude/skills/X/` | `./.claude/skills/X/` |
| Codex | `~/.codex/skills/X/` | `./.agents/skills/X/` |
| Gemini CLI | `~/.gemini/skills/X/` | `./.gemini/skills/X/` |
| Antigravity | `~/.gemini/antigravity/skills/X/` | `./.agent/skills/X/` |
| Cursor | `~/.cursor/skills/X/` | `./.cursor/skills/X/` |

Rule: **skill cá nhân → Global; skill team → Repo** (commit git, ai clone là có).

### 10.3 MCP

> "Skill dạy AI làm việc theo quy trình. MCP cho AI tay chân để chạm vào hệ thống."

**MCP (Model Context Protocol)** = chuẩn chung để AI gọi tool và data từ hệ thống ngoài — Anthropic thiết kế, nay là chuẩn mở toàn ngành. Analogy: API truyền thống = ổ điện riêng, mỗi service một loại phích; MCP = ổ cắm chuẩn hoá — cắm 1 lần, gọi nhiều dịch vụ cùng một kiểu. **MCP không thay API** — nó bọc trên API/DB/browser thành lớp trừu tượng cho agent.

Kiến trúc Host–Client–Server; điểm cốt lõi: AI **tự discover** tool nào có sẵn và **tự chọn** tool đúng cho từng task — khác biệt lớn nhất so với script.

Dùng MCP khi AI cần: query database · đọc/ghi GitHub issue/repo · đọc tài liệu Notion/Drive · thao tác design/browser · gọi tool nhiều bước và tự chọn tool.

**Đừng hype MCP** — 3 sai lầm: tưởng MCP thay hết backend; tưởng tool nào cũng có MCP server xịn; tưởng có MCP là bỏ script. Thực tế: nhiều tool chưa có MCP → script vẫn là plan B; MCP giảm ma sát chứ không xoá độ phức tạp.

**Cài MCP: nhờ AI thay vì làm tay** — "Việc gì AI làm được, đừng tự làm." Làm tay = 8 bước 15-30 phút mò mẫm; nhờ AI = 3 bước: prompt `"Cài MCP [tên] cho project X"` → AI hỏi key, paste vào → AI tự verify báo "tool sẵn sàng".

Checklist an toàn trước khi cài: nguồn tin cậy? cần key/token nào? quyền truy cập có quá rộng? có ghi log/gửi dữ liệu ra ngoài? có cách revoke key?

### 10.4 Script

Dùng script khi workflow cố định: convert file, import/export data, generate report, upload source, batch job.

**Script vs MCP:**

| Tiêu chí | Script | MCP |
|---|---|---|
| Phạm vi | 1 task = 1 script cố định | 1 server = nhiều tool, AI tự chọn |
| Setup | Viết code mỗi task | Cài 1 lần dùng mãi |
| Khi API đổi | Bạn sửa code | Maintainer server sửa, bạn update |
| AI tự quyết? | Không — chuỗi cố định | Có |

**Rule of thumb: "Cần AI tự quyết = MCP. Lặp cố định = Script."** (UX người dùng trông giống nhau — khác biệt nằm bên dưới.)

Mindset: automation không còn là độc quyền của dev — non-tech chỉ cần MÔ TẢ task, AI viết script + chạy hộ + lưu log; lần sau 1 lệnh = xong.

Prompt tạo script:

```text
Bạn là automation engineer. Tôi cần tự động hoá task sau: [mô tả]
Hãy: 1. Hỏi lại nếu thiếu input. 2. Đề xuất script đơn giản nhất.
3. Giải thích cách chạy. 4. Thêm bước kiểm tra thành công.
5. Không xoá/sửa file gốc nếu chưa có backup.
```

---

## 11. Phase 8 — Go-To-Market và Growth

### 11.1 GTM không phải việc sau cùng

GTM bắt đầu ngay khi chọn problem: User ở đâu? Họ tin ai? Đang dùng kênh nào? Trigger nào khiến họ tìm giải pháp? Nhận value theo nhịp nào? Ai trả tiền?

Khung tổng 4P: **Product** (bán gì, cho ai) · **Place** (kênh phân phối) · **Pricing** (giá bao nhiêu) · **Promotion** (thông điệp gì). 4 bước DO bên dưới (11.5→11.8) map đúng 4P.

### 11.2 Bốn giai đoạn fit

| Giai đoạn | Mục tiêu | Dấu hiệu |
|---|---|---|
| 0→1 Problem-Solution Fit | Xác minh vấn đề tồn tại | User nói bằng hành vi: "Tôi thật sự cần cái này" |
| 1→2 Product-Market Fit | Sản phẩm giải quyết hiệu quả | Quay lại, trả tiền, giới thiệu |
| 2→3 Channel-Model Fit | Kênh và giá hiệu quả | CAC giảm, LTV tăng, **ratio >3x** |
| 3→∞ Scale | Tăng trưởng ổn định | Retention + Profit + Viral loop |

Ba loại việc product (phân tách rõ): **Feature Delivery** (có giả thuyết feature cần ship để test) · **Growth Strategy** (PMF có tín hiệu, cần tăng trưởng) · **Redefine MVP** (MVP cũ không dùng được, pivot).

### 11.3 Thâm nhập thị trường: Diffusion, Chasm, Beachhead

**Law of Diffusion of Innovation**: Innovators 2,5% → Early Adopters 13,5% → Early Majority 34% → Late Majority 34% → Laggards 16%. **Tipping point** ~16% (sau khi chiếm early adopters): trước đó tăng trưởng cực chậm dù nỗ lực nhiều; sau đó có đà.

**Crossing the Chasm**: vực thẳm nằm giữa Early Adopters (visionaries — muốn CÁI MỚI) và Early Majority (pragmatists — muốn GIẢI PHÁP ĐÃ CHỨNG MINH). Phần lớn sản phẩm chết tại đây. Hệ quả: MVP/GTM giai đoạn đầu chỉ nhắm early adopters, không viết message cho mainstream.

**Beachhead Strategy (đầu cầu)**: tập trung TOÀN BỘ tài nguyên vào MỘT phân khúc nhỏ — nơi ít cạnh tranh hoặc bị công ty lớn bỏ qua; đứng vững rồi mới đánh thị trường liền kề. Ví dụ: vào ngành thời trang — sai: may đồ mọi kích cỡ mọi lứa tuổi; đúng: chỉ tập trung quần áo trẻ em.

**Market Sizing**: TAM (toàn bộ thị trường tiềm năng) → SAM (phần thực sự phục vụ/tiếp cận được) → SOM (thị phần chiếm được thực tế). Dùng khi đánh giá cơ hội và nói chuyện nhà đầu tư.

### 11.4 Hiểu khách hàng: Segmentation → Persona

Segmentation 4 trục: **Geographics** (nơi ở, ngôn ngữ, khí hậu) · **Demographics** (tuổi, giới, thu nhập, nghề, life stage) · **Psychographics** (lifestyle, AIO: Activity-Interest-Opinion, values, attitudes) · **Behavioral** (benefits sought, usage, intent, occasion, buyer stage, engagement).

Persona template: Bio + demographic + Needs + Pain points + Ideal experience + Quotes nguyên văn + data khảo sát.

### 11.5 Bước 1 — Lean Model Canvas

Thứ tự điền 9 ô (kèm 3 ô con):

```markdown
## Lean Model Canvas
1. Problems:                (+ Existing Alternatives — user đang dùng gì thay thế?)
2. Customer Segments:       (+ Early Adopters — ai là nhóm đầu tiên?)
3. Unique Value Proposition: (+ High-Level Concept — dạng "X for Y")
4. Solutions:
5. Channels:
6. Revenue Streams:
7. Cost Structure:
8. Key Metrics:
9. Unfair Advantage:        (barrier về cost? channel? patent? resource?)
```

Ví dụ mẫu — Lean Canvas of Google: Problems: kết quả tìm kiếm không liên quan / Alternatives: AltaVista, Yahoo / UVP: tìm đúng thứ cần + fast search / High-level concept: fast web search based on relevancy / Unfair advantage: PageRank / Segments: all web users / Early adopters: Stanford students / Key metrics: số search, % kết thúc ở trang đầu / Channels: user references / Revenue: investment, advertising.

### 11.6 Bước 2 — Thông điệp: Positioning + 3M

**Strategic sweet spot** = Customers' needs ∩ Company's capabilities, nằm NGOÀI Competitors' offerings, đặt trong Context (công nghệ, ngành, quy định).

```text
For [target customer]
who [Problem Statement — kế thừa từ Phase 1],
[product name] is a [category]
that [key benefit].
Unlike [alternative],
our product [differentiation].
```

**3M Model** — theo đúng thứ tự: **M1 Market** (nhóm cụ thể, đau thật, tiếp cận được) → **M2 Message** (lời hứa giá trị đánh đúng insight) → **M3 Medium** (kênh đưa message tới market hiệu quả nhất).

### 11.7 Bước 3 — Chọn kênh: 4 model GTM

| Model | Phù hợp khi | Ví dụ |
|---|---|---|
| **Product-led** | User tự onboard, value đến nhanh, có viral loop | Notion AI, Perplexity |
| **Sales-led** | Deal lớn, B2B, cần trust và custom workflow | Jasper Enterprise |
| **Marketing-led** | Tạo demand qua content, ads, brand, SEO | Copy.ai, Midjourney |
| **Community-led** | Niềm tin, học hỏi, truyền miệng quan trọng | Luma (share video → tò mò → tải thử → viral) |

Map Customer Journey 5×5 để chọn touchpoint: cột Awareness/Consideration/Decision/Retention/Loyalty × hàng Customer Action / Touchpoints / Emotion / Business Goal / KPIs. "Sản phẩm là cách bạn giải quyết VÀ distribute giải pháp cho vấn đề của người dùng."

### 11.8 Bước 4 — Thu hút và giữ user thật

1. **Nói chuyện với user thật, NOT AI.** "Go and validate your idea with actual customer. Stop thinking and not doing." Hỏi theo The Mom Test, lấy real feedback.
2. Đo bằng hành vi, không chỉ lời khen. "Dữ liệu thực tế > 1000 giả thiết trong đầu. Tri thức tốt nhất là học từ thị trường."
3. Test kênh phân phối như test feature. Ghi lại objections, trigger, language của user.

**Hooked Loop** (adoption gây nghiện — ví dụ Duolingo): Internal trigger (nhu cầu nội tại) + External trigger (notification nhắc) → **Action** (bài học ngắn, dễ) → **Variable Reward** (achievement, leaderboard — phần thưởng biến thiên) → **Investment** (user bỏ công/điểm → tăng khả năng quay lại) → lặp.

**Funnel + chi phí 2 nửa**: Acquisition → Activation ("The initial Aha!") → Engagement ("Consistent Aha!s") → Loyalty → LTV. Nửa đầu là **CAC** (Customer Acquisition Cost: product dev → marketing → sales → onboarding); nửa sau là **CRC** (Customer Retention Cost: adoption → retention → loyalty → expansion). Tối ưu LTV = quản cả hai.

### 11.9 Unit economics

```text
LTV = ARPU x Gross Margin x Customer Lifetime
CAC = (Sales cost + Marketing cost) / New customers
```

| LTV/CAC | Vùng | Hành động |
|---|---|---|
| < 1x | "Triangle of Unprofitable Death" — mỗi khách là một khoản lỗ | Giảm chi marketing, tối ưu conversion |
| 1–3x | "Wedge of Malaise" — có tiềm năng, chưa scale được | Cải thiện retention hoặc pricing |
| > 3x | "Sliver of Hope" — cỗ máy khoẻ | Có thể tăng chi acquisition để scale |
| Payback > 12 tháng | Thu hồi vốn quá lâu | Điều chỉnh giá hoặc kênh phân phối |

Benchmark thời gian đạt LTV ≥ 3×CAC:

| Loại sản phẩm | Thời gian kỳ vọng | Điều kiện |
|---|---|---|
| Consumer AI / B2C SaaS (app, plugin, course) | 6–9 tháng sau launch | Sau 2–3 vòng iteration lớn |
| SMB SaaS / automation / edtech nhỏ | 9–12 tháng | Khi có 200–500 khách trả tiền |
| Enterprise / B2B AI platform | 12–24 tháng | Sau 3–5 deal lớn & renewals đầu |
| Community-led / personal brand | 6 tháng nếu có trust sẵn | Khi community tự lan toả |

### 11.10 AI product economics — margin cliff

> "AI làm giảm cost để BUILD product, nhưng không tự động giảm cost để ACQUIRE hoặc SERVE customer."

- Traditional SaaS: revenue scales faster than serving cost — **usage creates leverage**.
- AI product + flat subscription: compute cost (token/inference) tăng theo usage → **margin cliff** — power users trở nên đắt đỏ. **Usage is value, but usage is also cost.**
- Vấn đề thật: vừa phải cho user cảm thấy phép màu, vừa không để free tier đốt cháy business.

Checklist: mỗi user dùng bao nhiêu token/API/compute? Free tier có đốt chi phí không? Usage có tương quan với willingness to pay không? Có giới hạn usage/credit/plan phù hợp không?

### 11.11 Revenue model

> "Revenue model phải khớp với cách user NHẬN VALUE, không phải khớp với mong muốn thu tiền của founder. Đừng hỏi 'thu subscription được không?' — hãy hỏi: user nhận value theo NHỊP nào?"

| Model | Khi dùng |
|---|---|
| Subscription | Value lặp lại đều theo tháng; hợp khi retention cao & usage ổn định |
| Usage-based | Trả theo credit/token/API call; hợp AI vì cost cũng tăng theo usage |
| Commission | Sản phẩm tạo giao dịch nhiều bên, lấy %; cần network đủ mạnh để có volume |
| Data monetization | Bán report/API/benchmark; CHỈ làm khi dữ liệu sạch và có consent |
| Outcome/Enterprise | B2B, ROI rõ, workflow quan trọng; kiếm nhiều hơn nhưng sales cycle khó hơn |

### 11.12 Moat

> "Moat là thứ khiến bạn vẫn sống sót khi người khác bắt chước bạn."

| Moat | Ví dụ |
|---|---|
| Technology | Thuật toán, model, workflow kỹ thuật khó copy |
| Data | Dữ liệu độc quyền, càng dùng càng tốt |
| Brand | Niềm tin và cảm xúc với thương hiệu |
| Network | Càng nhiều người dùng, value càng tăng |
| Distribution | Kênh phân phối, cộng đồng, thói quen người dùng khó thay thế |

---

## 12. Templates và prompt dùng ngay

### 12.1 Prompt chẩn đoán dự án

```text
Bạn là senior product strategist và AI product builder.
Dựa trên playbook này và thông tin dự án dưới đây, hãy:
1. Xác định dự án đang ở phase nào.
2. Liệt kê artifact đã có và artifact còn thiếu.
3. Chỉ ra 5 rủi ro lớn nhất.
4. Đề xuất next step trong 7 ngày.
5. Không đề xuất build thêm nếu Problem Statement/MVP hypothesis chưa rõ.
6. Với mỗi đề xuất, trả lời: "cái này có kéo dự án gần hơn tới user thật/doanh thu không?"

Thông tin dự án:
[paste]
```

### 12.2 Prompt phân tích problem

```text
Bạn là product discovery coach (experienced Product Manager).
Tôi đang xem xét vấn đề sau: [mô tả]

Hãy:
1. Viết lại Problem Statement theo format [User] needs to [Need] because [Insight].
   Check 4 lỗi phổ biến: nhảy vào giải pháp / mơ hồ / không rõ đối tượng / cảm tính.
2. Phân tích user need bằng 5 Whys (cố đủ 5 lần) VÀ 5W1H.
3. Phân tích 4 risks: Value, Usability, Feasibility, Viability.
4. Đề xuất 5 cách validate trong 7 ngày bằng 6 cỗ máy test (KHÔNG cần build).
5. Chỉ ra assumption ẩn và câu hỏi cần hỏi user thật (theo The Mom Test).

Trả lời bằng tiếng Việt, dạng bảng và checklist.
```

### 12.3 Prompt viết PRD

```text
Bạn là PRD architect.
Dựa trên Problem Statement và context dưới đây, hãy viết PRD MVP.

Yêu cầu:
- MVP chỉ tập trung kiểm chứng 1 giả thuyết chính, scope theo 1 use case trọn vẹn.
- Có scope IN/OUT rõ.
- Mỗi user story đủ 4 khối: User Role / Goal / User Flow (bước đánh số) /
  Acceptance Criteria ĐỊNH LƯỢNG (pass/fail được, có số).
- Có user flow từng bước + Aha moment.
- Có success metrics đo bằng số.
- Có data entities, risks, open questions.
- (Tuỳ chọn) UI/UX Theme: color palette hex + 3-5 tính từ brand personality.

Context:
[paste]
```

### 12.4 Prompt tạo prototype brief

```text
Bạn là product designer.
Dựa trên PRD sau, hãy tạo prototype brief gồm:
1. Customer Journey 5 stages (kèm emotion và "điểm rơi nguy hiểm").
2. Aha Moment Ladder (Aha 1/2/3 + Adoption).
3. User Flow cho MVP — chỉ rõ Aha ở bước nào.
4. Danh sách màn hình + nội dung từng màn hình.
5. Audit: những bước thừa cần gộp/bỏ để user chạm Aha sớm hơn.
6. Rule vàng: giai đoạn nào không nghĩ ra Aha = chỗ MVP yếu nhất — chỉ ra.

PRD:
[paste]
```

### 12.5 Prompt tạo ERD và SQL (chain có review)

```text
BƯỚC 1 (chờ tôi chốt rồi mới sang bước 2):
"Từ PRD này, xác định entities và vẽ ERD (mức Logical: thuộc tính + cardinality)
bằng Mermaid. Nêu các field nhạy cảm không nên expose ra frontend."

BƯỚC 2 (sau khi tôi chốt ERD):
"Từ ERD đã chốt, viết SQL CREATE TABLE (mức Physical) cho Supabase/Postgres.
Kèm: bảng CRUD permissions, RLS policy cần có ở mức MVP."

PRD/User flow:
[paste]
```

### 12.6 Prompt giao task cho AI agent trong IDE

```text
Bạn là coding agent trong repo này.

Mục tiêu: [mô tả rất cụ thể]

Phạm vi:
- Chỉ sửa các file liên quan tới: [file/folder — đích danh]
- Không thay đổi: [file/folder/logic]

Trước khi sửa (planning mode):
1. Đọc các file cần thiết.
2. Tóm tắt hiểu biết của bạn.
3. Đề xuất plan ngắn.
4. Chờ tôi xác nhận nếu thay đổi ảnh hưởng nhiều file hoặc thêm dependency.

Sau khi sửa:
1. Chạy command kiểm tra phù hợp.
2. Đóng vai QA độc lập: tự tìm lỗi trong chính thay đổi của bạn.
3. Tóm tắt diff. Nêu rủi ro còn lại.
```

### 12.7 Prompt review trước launch

```text
Bạn là launch reviewer.
Hãy review MVP theo checklist:
1. Problem và MVP hypothesis có rõ không?
2. User flow có chạm Aha nhanh không? Có bước thừa trước Aha không?
3. Có dark pattern "dắt lộ liễu" nào không (popup ép, checkbox mờ, countdown giả)?
4. App có URL live và test được không? Data có lưu thật không?
5. Chạy checklist Sẵn Sàng Public 5 ô (URL live / DB đúng ERD / repo sạch /
   .gitignore + .env / key ở env vars).
6. Có success metric và tracking tối thiểu không?
7. Có GTM channel cho 10-50 user đầu tiên (early adopters/beachhead) không?

Output: Go / No-go · Blockers · Fix before launch · Can launch with risk ·
Post-launch measurement plan
```

### 12.8 Prompt cài MCP / viết script

```text
MCP:  "Cài MCP [tên server] cho project này. Hỏi tôi key nếu cần,
       tự verify và báo khi tool sẵn sàng."

Script: xem prompt tạo script §10.4 (luôn có bước self-verify + không xoá file gốc).
```

---

## 13. Final checklist

### 13.1 Trước khi build

- [ ] Đã thử test giả định bằng 1 trong 6 cỗ máy (không code) chưa?
- [ ] Có user cụ thể + Problem Statement rõ (qua 4 lỗi check).
- [ ] Có 5 Whys/5W1H → root cause.
- [ ] Có phân tích 4 risks (bỏ 1 = xác suất fail nhân đôi).
- [ ] Có bằng chứng hoặc plan validate trong 7 ngày.
- [ ] Có MVP hypothesis + scope theo 1 use case trọn vẹn (xe đạp, không phải ô tô thiếu bánh).
- [ ] Có Aha Moment + success metric đo bằng số.
- [ ] RDD check: cái sắp build có kéo mình gần hơn tới user thật/doanh thu đầu tiên không?

### 13.2 Trước khi deploy

- [ ] App chạy local; flow chính hoàn thành được.
- [ ] Data lưu thật nếu MVP cần data (chưa có DB + BE logic = vẫn là prototype).
- [ ] Checklist trước khi push GitHub (5 câu §8.6) — pass hết.
- [ ] Checklist Sẵn Sàng Public (5 ô §8.6) — pass hết.

### 13.3 Trước khi launch

- [ ] Biết 10-50 user đầu tiên ở đâu (early adopters — beachhead segment).
- [ ] Có message ngắn gọn (positioning statement) + CTA rõ.
- [ ] Có tracking tối thiểu + cách nhận feedback.
- [ ] Có plan sửa lỗi sau launch + tiêu chí pivot/continue.

### 13.4 Sau launch 7 ngày

```markdown
## 7-Day Learning Review
- Users reached / tried / activated:
- Aha completion rate:
- Retention signal:
- Top 5 feedback:
- Biggest drop-off:
- Unexpected behavior:
- Unit economics sơ bộ (nếu có tiền vào):
- Decision: Continue / Iterate / Pivot / Stop
- Next 7-day experiment:
```

### 13.5 Vệ sinh tài liệu sau mỗi milestone (bắt buộc)

- [ ] Xoá plan/artifact đã chết (đã xong việc, không còn phản ánh hiện tại).
- [ ] Specs còn lại có mâu thuẫn nhau không? Có mô tả lại code (nguồn sự thật thứ 2)?
- [ ] Docs sống chỉ còn: CLAUDE.md/AGENTS.md, system-architecture, code-standards, PRD overview.
- [ ] Comment trong code ghi WHY, không ghi WHAT.

---

## Appendix — Cách AI nên phản hồi khi dùng playbook này

Khi user yêu cầu "giúp tôi build sản phẩm", AI không nhảy ngay vào code. Phản hồi theo format:

```markdown
Mình sẽ xử lý theo playbook v4.

## Chẩn đoán nhanh
- Phase hiện tại:
- Artifact đã có:
- Artifact thiếu:
- Rủi ro lớn nhất:
- RDD check: việc sắp làm có dẫn tới user thật/doanh thu không?

## Việc cần làm ngay
1.
2.
3.

## Câu hỏi cần bạn trả lời
1.
2.
3.

## Output mình sẽ tạo
-
```

Nếu user đã có đủ PRD và yêu cầu build → chuyển sang build. Nếu chưa đủ → tạo artifact còn thiếu trước. Trước khi chốt mọi output quan trọng, tự chạy 3 câu: "Cái này có assumption gì? Fail ở đâu? Có gì mình chưa nghĩ tới?"

---

*v4.0 = v3.0 (khung vận hành) + toàn bộ kiến thức 9 buổi được quét lại đầy đủ (mỗi buổi 1 agent riêng, bao gồm nội dung slide dạng ảnh) + lăng kính RDD và kỷ luật tài liệu/context từ bài học SDD→RDD. Nguyên tắc biên soạn: đầy đủ kiến thức nhưng không phình quy trình — artifact là bản đồ, không phải bộ luật.*
