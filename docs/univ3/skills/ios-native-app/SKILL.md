---
name: ios-native-app
description: >-
  Kích hoạt khi muốn biến 1 web/dự án thành app iOS NATIVE (SwiftUI) cài lên iPhone thật, hoặc
  ký/build lại app đã có. User nói "build iOS app", "làm app iOS cho dự án này", "đưa app lên iPhone",
  "ký lại app", "re-sign app", "app hết hạn build lại". LUÔN native — KHÔNG bọc web/WKWebView.
  Ký lại chạy 1 lệnh (resign.sh, đọc registry ~/.claude/ios-apps-registry.json). Team/registry ở local, KHÔNG trong skill.
---

# ios-native-app — biến dự án thành app iOS native + ký lại 1 lệnh

## Khi nào dùng
- "Build iOS app" cho dự án ĐANG mở → dựng app SwiftUI native gọi API của dự án đó.
- "Ký lại app" → build + cài lại (1 lệnh cho toàn bộ app). Máy này ký bằng tài khoản Apple Developer
  **CÁ NHÂN (Individual, 99$/năm) của Hữu Anh** — Team ID `GYNRKXCZPQ` (Huu Anh Nguyen), KHÔNG phải
  team/doanh nghiệp; chữ ký sống tới **2027-09-01** → 1 năm ký lại 1 lần. Xem mục "Acc CÁ NHÂN" dưới.
- KHÔNG dùng để bọc web. LUÔN native.

## Nguyên tắc bất di bất dịch
1. **Native (SwiftUI), NEVER bọc web.** 2. **Tên app = tên dự án**; chức năng lớn = 1 **mục** trang chủ.
3. Backend cho app = **Worker riêng, tách deploy, CHUNG database** với web (token Bearer, không cookie).
   App dùng `URLSession`, token lưu UserDefaults/Keychain, mỗi request gắn header `Authorization: Bearer <token>`
   (Worker ký HMAC); port logic từ web sang Worker, cùng bảng D1 → dữ liệu khớp hai chiều.
4. **LUÔN có icon** (1024, bỏ alpha). 5. Verify thật: `BUILD SUCCEEDED` + `App installed` rồi mới báo xong.

## Yêu cầu 1 lần (setup rồi thì bỏ qua)
- Xcode đầy đủ: `brew install xcodes aria2 xcodegen` → `xcodes install --latest` (user gõ Apple ID+2FA) → `sudo xcode-select -s /Applications/Xcode-<ver>.app && sudo xcodebuild -license accept && sudo xcodebuild -runFirstLaunch`.
  - ⚠️ KHÔNG có `brew install xcode` — chỉ `xcodes` tải được (~15GB). Apple bắt nhập Apple ID + mật khẩu + 2FA + mật khẩu Mac → **user tự gõ trong Terminal**, agent không gõ thay được.
  - 3 lệnh `sudo` ở trên gộp vào 1 file `.sh` đưa user chạy một lần (máy không NOPASSWD).
  - Runtime simulator (`xcodebuild -downloadPlatform iOS`, ~7–10GB) chỉ cần khi chạy máy ảo; build lên **iPhone thật thì KHÔNG cần** (SDK device nằm sẵn trong Xcode).
- Apple ID đã thêm trong Xcode (Settings → Accounts). iPhone bật **Developer Mode**.

## Setup MỘT-LẦN (làm 1 lần, cấm hỏi lại)
> Xong 2 mục dưới thì về sau build app mới CHỈ còn: code SwiftUI + chạy `deploy.sh` của dự án (hoặc `resign.sh` nếu app đã có trong registry). Không login lại, không bấm dashboard.

**(a) Cloudflare API token persistent — DÙNG CHUNG mọi app trong account, KHÔNG phải mỗi app 1 token.**
Không có token này thì mỗi `wrangler deploy`/`secret put`/`pages deploy` phải login browser tay (OAuth mặc định THIẾU scope Workers). Cloudflare KHÔNG cho tạo token account-scope bằng OAuth có sẵn → **user tạo tay 1 lần** ở dashboard:
`Cloudflare dashboard → My Profile → API Tokens → Create Token → Create Custom Token`, scope (Permissions):
`Account · Workers Scripts:Edit` + `Account · Cloudflare Pages:Edit` + `Account · D1:Edit` + `Account · Workers R2 Storage:Edit` + `Account · Account Settings:Read`.
Rồi lưu vĩnh viễn: thêm `export CLOUDFLARE_API_TOKEN=...` vào `~/.zshrc` → từ đó MỌI lệnh wrangler chạy headless.

**(b) iPhone Developer Mode + trust cert = 1 lần / MÁY (không phải 1 lần / app).**
Bật Developer Mode (Cài đặt → Quyền riêng tư & Bảo mật → Developer Mode → bật + restart) · Tin cậy cert (Cài đặt → Cài đặt chung → VPN & Quản lý thiết bị → tin cậy cert Apple Development). Máy đã làm xong thì **CẤM hướng dẫn lại** 3 bước này.

## Cách chạy — KÝ LẠI (tự động, app đã có trong registry)
```bash
bash ~/.claude/skills/ios-native-app/resign.sh          # ký lại TẤT CẢ app
bash ~/.claude/skills/ios-native-app/resign.sh <name>   # 1 app
```
ĐK cài không dây: Mac bật · iPhone **cùng WiFi** (KHÔNG cần cáp) · máy **đã nạp DDI** (`ddiServicesAvailable = true`
trong `devicectl device info lockState`) — máy khoá mà chưa nạp DDI thì CÀI cũng trượt, xem §Kiểm app đang cài · chứng chỉ .p12 đã nạp keychain +
4 hồ sơ đã ở `~/Library/MobileDevice/Provisioning Profiles/`.
Sau lần cắm cáp ĐẦU TIÊN thiết bị tự pair không dây — kiểm chứng:
`xcrun devicectl list devices --json-output /tmp/dev.json` → `transport = "localNetwork"` ⇒ đã wireless.

## Kiểm app đang cài trên iPhone thật (qua WiFi)
Ranh giới ĐO THẬT 09/09/2026 (iPhone 14 Pro `HK-14pr256`, UDID CoreDevice `4F378E23-0446-5CDD-A6F6-CCCC8134248B`):

| Lệnh | Máy đang KHOÁ | Vì sao |
|---|---|---|
| `devicectl list devices` | ✅ chạy | chỉ hỏi tunnel; `transportType = localNetwork` ⇒ đã pair không dây |
| `devicectl device info lockState --device <UDID>` | ✅ chạy | trả `passcodeRequired` / `unlockedSinceBoot` |
| `devicectl device install app` | ⚠️ chỉ khi `ddiServicesAvailable = true` | máy khoá mà DDI chưa nạp → `12040` y như liệt kê app (đo 06/10/2026, xem dưới) |
| `devicectl device info apps` | ❌ trượt | phải mount DDI, mà DDI đòi máy đã mở khoá |

Lỗi nguyên văn khi khoá: `CoreDeviceError 12040` → `kAMDMobileImageMounterDeviceLocked: The device is locked.`

**Ca đo 06/10/2026 (W43, cài app ChicHub MVP):** `devicectl device install app` trả `12040` **BỐN lần liền** khi
`devicectl device info lockState` cho `ddiServicesAvailable = false` + `passcodeRequired = true`; máy vừa mở
(`ddiServicesAvailable = true`) thì cài ăn ngay, `rc=0`. → Bảng cũ ghi "install chạy được khi máy khoá" là SAI:
chỉ đúng khi DDI đã nạp sẵn từ lần mở khoá trước. **Trước khi cài, đọc `ddiServicesAvailable`:**
- `true` → cài luôn.
- `false` → chạy **vòng thử lại NỀN có hạn giờ** (vd mỗi 60 giây đọc lại `lockState`, tối đa 2 giờ; thấy `true` thì cài,
  hết giờ thì ghi "chưa cài được — máy chưa mở" vào báo cáo). **KHÔNG nhắn chủ máy bảo mở khoá** — họ cầm máy lên là tự nạp DDI.
  Vòng nền phải tự tắt khi xong/hết giờ, khai PID trong báo cáo.
**Lặp lại 6 lần chỉ ăn với `CoreDeviceError 4000`** (bắt tay tunnel chập chờn). Với `12040` đã đo 6/6 lượt trượt —
lặp dồn dập là phí thời gian — KHÔNG nhắn founder mở khoá; cho vòng thử lại nền có hạn giờ chờ máy được mở.
Máy vừa mở + màn sáng → ăn ngay lần đầu:
```bash
xcrun devicectl device info apps --device <UDID> --include-all-apps --json-output /tmp/apps.json
# --include-all-apps: THIẾU cờ này là mất app hệ thống + app cài kiểu developer. Đo thật: 340 app.
python3 -c "import json;[print(a['bundleIdentifier'],a.get('name'),a.get('version')) for a in json.load(open('/tmp/apps.json'))['result']['apps']]"
```
Đường DỰ PHÒNG khi không mở khoá được — `ideviceinstaller` đi qua lockdownd, KHÔNG cần DDI
(`brew install ideviceinstaller`; cú pháp đúng là `list --all`, `-l` báo `invalid option`):
```bash
idevice_id -n                                     # RỖNG = đường này vô dụng, đừng thử tiếp
ideviceinstaller -n -u <UDID-PHẦN-CỨNG> list --all
```
⚠️ **Hai đường ĐỘC LẬP**: `devicectl` = CoreDevice tunnel, `ideviceinstaller` = usbmuxd. Đo thật: devicectl thấy máy
qua `localNetwork` trong khi `idevice_id -n` rỗng → `No device found`. devicectl thấy KHÔNG suy ra được usbmuxd thấy.

## Ký lại IPA mà ĐỔI bundle id = iOS coi là APP MỚI, cài CẠNH bản cũ chứ không đè
Đo trên iPhone founder: cùng lúc tồn tại **hai icon đều tên "Stremio"** — `com.stremio.pal` (2.0.7, bundle gốc)
và `fun.jst4.stremio` (2.0.7, bản ký lại đổi tiền tố sang `fun.` cho khớp hồ sơ wildcard; khai ở
`~/.claude/ios-apps/resign-map.json`, team `Q27B6K3LNC`) — cạnh đó còn `com.sotremmio.app.native2`
("SờTremMio" 0.3.0, build từ dự án `stremiox`).
→ Muốn ĐÈ bản cũ thì **giữ nguyên bundle id**. Đổi bundle id (kể cả chỉ đổi tiền tố cho khớp hồ sơ) thì phải **tự gỡ bản cũ**,
không thì máy có 2 app trùng tên, người dùng mở nhầm bản cũ rồi báo "sửa mà chẳng thấy đổi gì".

## Bộ ký hiện hành
Bộ gốc: `/Users/buddhy/PycharmProjects/DOC-tool/appdev/BO-KY-CHO-THANH/` (kèm `HUONG-DAN.md`).

| Mục | Giá trị |
|---|---|
| Team ID | `GYNRKXCZPQ` (Huu Anh Nguyen) — acc Apple Developer **CÁ NHÂN (Individual) 99$**, KHÔNG phải team/doanh nghiệp |
| Hết hạn | **2027-09-01** (cert + cả 4 hồ sơ) → 1 năm ký lại 1 lần |
| Ký lúc phát triển | hồ sơ `Thanh Dev fun` (bundle `fun.*`) · `Thanh Dev com` (bundle `com.*`) |
| Ký để phát cho người khác | hồ sơ `Thanh AdHoc fun` / `Thanh AdHoc com` + cert **Apple Distribution** |
| Máy đã đăng ký | `00008120-000A3D6C1403C01E` (iPhone founder) · `00008130-0012612636F9001C` (iPhone bạn gái) |

**Ký THỦ CÔNG, không Automatic**: ký tự động đòi đăng nhập Apple ID của chủ team trong Xcode.
Trong `project.yml` khai:
```yaml
DEVELOPMENT_TEAM: GYNRKXCZPQ
CODE_SIGN_STYLE: Manual
PROVISIONING_PROFILE_SPECIFIER: "Thanh Dev fun"   # hoặc "Thanh Dev com" nếu bundle bắt đầu bằng com.
CODE_SIGN_IDENTITY: "Apple Development"
```
Hồ sơ là **wildcard** `GYNRKXCZPQ.fun.*` / `GYNRKXCZPQ.com.*` nên phủ mọi app đặt tên đúng tiền tố,
kể cả target UITests và app extension — khai một lần ở `settings.base` là đủ.
**Ngoại lệ**: app cần push notification, iCloud hay Sign in with Apple thì wildcard KHÔNG phủ,
phải nhắn Hữu Anh xin hồ sơ riêng. Máy thứ ba cũng phải gửi UDID cho Hữu Anh thêm vào hồ sơ.

### Acc CÁ NHÂN — KHÔNG phải team (Hữu Anh dặn 06/10/2026: "acc mình là acc cá nhân, ko phải team")
- Acc Individual **KHÔNG cấp được** quyền "Access to Certificates, Identifiers & Profiles" cho thành viên
  khác, cũng KHÔNG nâng Admin cho người khác được. Founder chỉ là thành viên vai App Manager
  (`provisioningAllowed: false`) → **mọi mã định danh / hồ sơ ký đều do Hữu Anh tự bấm tạo**.
- Hướng dẫn kiểu "cấp quyền cho thành viên tự tạo" là của tài khoản team/doanh nghiệp → CẤM đề xuất.
- Khoá APNs dùng chung cho mọi app: **khoá APNs giữ riêng trên máy founder, tuyệt đối không đưa lên máy chủ/kho**
  (mã khoá + chỗ cất ghi ở trí nhớ cục bộ của máy founder). Đã có — KHÔNG xin lại.
- Thông báo đẩy của app ChicHub **đã BỎ ngày 06/10/2026** — vì khoá riêng tư APNs không được đưa lên máy chủ
  (máy chủ không có khoá thì không bắn push được). App cần push sau này phải giải bài toán giữ khoá trước.
- App cần push → soạn MỘT tin xin Hữu Anh ĐỦ 2 việc trong một lần (đừng xin nhỏ giọt):
  (1) Identifiers → App ID **Explicit** `<bundle>` tick **Push Notifications**;
  (2) Profiles → **iOS App Development** cho App ID đó + cert Apple Development của founder + máy cần cài,
  tên `Thanh Dev <App>` → gửi `.mobileprovision`.

## Build APP MỚI (Claude tự làm cho dự án đang mở)
1. Đọc cấu trúc dự án → chọn mục nào native + tên app. Backend: Worker riêng bind CHUNG D1, token Bearer.
2. Code SwiftUI (trang chủ + từng mục) + `project.yml` (XcodeGen — **`Assets.xcassets` để trong `sources:`, KHÔNG dùng `resources:`**, xem Gotcha icon) + **icon** (`sips` phóng 1024, vòng JPEG bỏ alpha).
3. Bỏ qua bước mở Xcode chọn team: bộ ký đã có sẵn, đặt bundle id bắt đầu bằng `fun.` hoặc `com.` là hồ sơ wildcard phủ ngay, build headless được từ lần đầu.
4. **GOTCHA CHÍ MẠNG — Team ID**: `security find-certificate -c "Apple Development" -p | openssl x509 -noout -subject` → Team ID = **`OU=...`**, KHÔNG phải số trong ngoặc CN (CN của cert hiện tại là "Created via API (T87J7958T4)" — T87J7958T4 KHÔNG phải team). Điền khối ký thủ công ở mục "Bộ ký hiện hành" vào `project.yml`, KHÔNG dùng `CODE_SIGN_STYLE=Automatic`.
5. Build + cài:
   ```bash
   UDID=<xcrun devicectl list devices → Identifier phần cứng iPhone>
   xcodegen generate -s <dir>/project.yml -p <dir>
   xcodebuild -project <dir>/<App>.xcodeproj -scheme <App> -destination "id=$UDID" -derivedDataPath /tmp/dd build
   xcrun devicectl device install app --device "$UDID" /tmp/dd/Build/Products/Debug-iphoneos/<App>.app
   ```
   - UDID lấy bằng `xcrun devicectl list devices` (cột Identifier) hoặc `xcrun xctrace list devices`. iPhone chưa bật Developer Mode → máy hiện trạng thái `connected (no DDI)`.
   - Mở app từ CLI: `xcrun devicectl device process launch --device "$UDID" <bundleId>`.
6. **Tường Apple (user tự làm)**: Developer Mode (bật+restart) · Tin cậy cert (Cài đặt → VPN & Quản lý thiết bị). Cài qua WiFi KHÔNG cần cáp, nhưng CẦN DDI (Developer Disk Image) đã nạp — đọc `ddiServicesAvailable` trong `devicectl device info lockState` trước khi cài: `false` (máy khoá mà DDI chưa nạp) thì cài trượt `12040` y như `device info apps` — chạy vòng thử lại nền chờ máy được mở, xem §Kiểm app đang cài; hay gặp CoreDeviceError 4000 ở lần bắt tay đầu — resign.sh đã tự thử lại 6 lần.
7. **APPEND vào registry** `~/.claude/ios-apps-registry.json` (để resign.sh ký lại được):
   ```json
   { "name":"<App>", "project_dir":"<path>", "app_dir":"<dir tương đối>", "scheme":"<App>",
     "bundle_id":"<id>", "team":"<OU>", "udid":"<udid>", "app_product":"<App>.app" }
   ```

### `project.yml` mẫu (XcodeGen: `xcodegen generate -s <dir>/project.yml -p <dir>` → ra `<Name>.xcodeproj`)
```yaml
name: <AppName>
options: { deploymentTarget: { iOS: "16.0" }, createIntermediateGroups: true }
targets:
  <AppName>:
    type: application
    platform: iOS
    sources: [ { path: Src } ]          # Assets.xcassets nằm TRONG Src — xem Gotcha icon
    settings:
      base:
        PRODUCT_BUNDLE_IDENTIFIER: fun.jst4.<app>
        DEVELOPMENT_TEAM: GYNRKXCZPQ
        CODE_SIGN_STYLE: Manual
        PROVISIONING_PROFILE_SPECIFIER: "Thanh Dev fun"   # "Thanh Dev com" nếu bundle mở đầu bằng com.
        CODE_SIGN_IDENTITY: "Apple Development"
        GENERATE_INFOPLIST_FILE: "YES"
        ASSETCATALOG_COMPILER_APPICON_NAME: AppIcon
        INFOPLIST_KEY_UILaunchScreen_Generation: "YES"
        INFOPLIST_KEY_CFBundleDisplayName: <AppName>
        TARGETED_DEVICE_FAMILY: "1"
```
- `.gitignore` trong thư mục app: `*.xcodeproj/`, `build/`, `DerivedData/` (project sinh lại từ `project.yml`).

### Icon — làm ngay từ đầu, đừng để app trắng trơn
```bash
mkdir -p <dir>/Src/Assets.xcassets/AppIcon.appiconset
sips -z 1024 1024 public/apple-touch-icon.png --out /tmp/i.png
sips -s format jpeg /tmp/i.png --out /tmp/i.jpg      # vòng qua JPEG để BỎ ALPHA
sips -s format png /tmp/i.jpg --out <dir>/Src/Assets.xcassets/AppIcon.appiconset/icon-1024.png
```
- `AppIcon.appiconset/Contents.json`: 1 ảnh `icon-1024.png`, `"idiom":"universal","platform":"ios","size":"1024x1024"`.
- ⚠️ Icon iOS **KHÔNG được có alpha** → luôn flatten (vòng JPEG như trên), không thì build báo lỗi / icon đen.

## Gotcha SwiftUI — layout
- **Hàng lệch/tràn ngang khi text dài** (`HStack { VStack text ; Spacer() ; icon/Link }`): `Spacer()` KHÔNG ép text wrap → text lấy bề rộng lý tưởng, đẩy cả hàng, icon trailing trôi. FIX: bỏ `Spacer()`, ghim VStack text `.frame(maxWidth: .infinity, alignment: .leading)` → text tự wrap, trailing đứng yên. Container tab ngoài cùng cũng ghim `maxWidth: .infinity`.

## Gotcha icon — Assets.xcassets phải trong `sources:`
- **App build xong nhưng iPhone KHÔNG hiện icon**: trong `project.yml`, `Assets.xcassets` phải nằm dưới `sources:` của target (XcodeGen tự nhận `.xcassets` là resource), **KHÔNG để dưới `resources:`** — XcodeGen KHÔNG có key `resources:` ở target nên bị IGNORE → `.app` thiếu `Assets.car`, Info.plist thiếu key icon → app không icon.
- **VERIFY sau build** (thiếu 1 trong 2 → icon KHÔNG vào app, phải sửa `sources:` rồi build lại): `.app/Assets.car` tồn tại VÀ `xcrun assetutil --info <app>/Assets.car | grep AppIcon` có kết quả.

## ⭐ Verify UI/UX = iOS Simulator (model TỰ nhìn) — CẤM chrome-devtools phone view
> Founder chốt (GLOBAL): kiểm UI/UX app iOS native **PHẢI** tự cài vào Simulator + chụp màn hình rồi ĐỌC ảnh. **CẤM** dùng chrome-devtools phone emulation để kết luận (nó KHÔNG mô phỏng được app native — chỉ web). Tự kiểm layout/luồng bằng simulator TRƯỚC khi báo xong; không đẩy cho user nếu simulator kiểm được.

**Quy trình chuẩn (build → cài simulator → chụp → đọc ảnh):**
```bash
# 1. Build cho SIMULATOR (không phải device) — destination generic simulator
xcodegen generate -s <dir>/project.yml -p <dir>
xcodebuild -project <dir>/<App>.xcodeproj -scheme <App> \
  -destination "generic/platform=iOS Simulator" -derivedDataPath /tmp/dd-sim build

# 2. Boot simulator — test trên DEVICE NGƯỜI DÙNG THỰC DÙNG (mặc định iPhone Pro / Pro Max đời hiện tại — hỏi/known device của user;
#    KHÔNG ép optimize cho iPhone SE nếu user không dùng SE vì màn nhỏ ép co dúm layout). Vẫn nên xem 1 device rộng + 1 vừa NHƯNG ưu tiên đúng device thật của user. Rồi cài .app vừa build.
#    CẤM mở cửa sổ Simulator lên trước — xem "Test không chiếm máy người dùng" ở dưới.
UDID=$(xcrun simctl create agent-lab "iPhone 17 Pro" "$(xcrun simctl list runtimes | grep -o 'com.apple.CoreSimulator.SimRuntime.iOS-[0-9-]*' | tail -1)")
xcrun simctl boot "$UDID" && xcrun simctl bootstatus "$UDID"   # KHÔNG mở cửa sổ nào
xcrun simctl install "$UDID" /tmp/dd-sim/Build/Products/Debug-iphonesimulator/<App>.app

# 3. Mở app rồi CHỤP MÀN HÌNH → ĐỌC ảnh (layout/luồng/spacing/safe-area/notch)
xcrun simctl launch "$UDID" <bundle_id>
xcrun simctl io "$UDID" screenshot /tmp/sim-app.png
```
**Check trên ảnh:** không tràn/cắt chữ · Spacer/HStack không đẩy trailing (Gotcha layout) · safe-area top/bottom đúng · từng mục điều hướng mở được · text tiếng Việt CÓ DẤU. Điều hướng qua nhiều màn → chụp từng bước.

### Test không chiếm máy người dùng (BẮT BUỘC)

> Founder chốt (nguyên văn): "tại sao test emulator thì phải control chuột của tao à? cứ hiện lên che các màn khác, lấy quyền dùng chuột của tao".

Người dùng đang LÀM VIỆC trên chính cái máy này. Test iOS **không được** chiếm cửa sổ, **không được** chạm vào con trỏ chuột thật.

**CẤM tuyệt đối** — hook `no_steal_focus_enforce.py` chặn tất định (`permissionDecision: deny`):
- Mở app Simulator lên trước (`open -a Simulator` không có cờ `-g`) — cửa sổ nhảy lên che màn hình đang dùng.
- AppleScript `activate` / `AXRaise` / `perform action` — kéo cửa sổ lên trước.
- `cliclick`, `xdotool`, CGEvent bơm click/phím vào MÀN HÌNH THẬT — giật chuột khỏi tay người dùng. Gói vào file `.sh` rồi gọi cũng bị chặn (hook soi nội dung script/binary đem ra chạy).

**Làm đúng — `simctl` headless. univ3 cài sẵn `sim-headless.sh` vào `~/.claude/universal-hooks/`:**
```bash
S=~/.claude/universal-hooks/sim-headless.sh
bash $S boot                      # tạo + boot DEVICE RIÊNG của agent (không mở cửa sổ nào)
bash $S install <App>.app
bash $S launch <bundle-id>
bash $S url "myapp://sau-khi-mo"  # deep-link / http
bash $S shot /tmp/sim.png         # chụp rồi ĐỌC ảnh
bash $S test <Scheme> <App>.xcodeproj   # XCUITest tự bấm
bash $S stop --xoa                # dọn device riêng
```
- **Device RIÊNG** (`xcrun simctl create`) — không dùng chung device người dùng hay worker khác đang xem; xong việc `stop --xoa`.
- **Cần TỰ BẤM trong app** → **XCUITest** (`xcodebuild test -destination "id=$UDID"`): bấm bằng API BÊN TRONG simulator, không đụng con trỏ chuột thật.
- **Web trong Safari simulator** → bơm `PointerEvent`/`dispatchEvent` bằng JS.
- **Bắt buộc phải nhìn tận mắt** → `open -g -a Simulator` (`-g` = mở ở NỀN).

**Đã đo thật (không đoán):** boot device riêng + `simctl launch` + `simctl io screenshot` cho ra ảnh nội dung thật, trong khi app frontmost của người dùng KHÔNG đổi (`Arc` trước và sau). `open -g -a Simulator` cũng không đổi frontmost.

**CHỈ escalate cho user test iPhone THẬT khi simulator KHÔNG kiểm được:** Face ID/Touch ID · camera thật · push notification thật · haptics/gesture tinh vi · share sheet gửi sang app thật · hiệu năng thiết bị thật · ký/cài App Store/provisioning thật. Ngoài các mục đó → PHẢI tự verify bằng simulator, CẤM đẩy cho user.

_(Rule verify chung: `rules/GATES.md` §0 — verify bằng công cụ, không đoán trạng thái.)_

## Auto-deploy Worker của app (CI)
- Worker backend deploy TÁCH khỏi web, bind CHUNG D1: `wrangler deploy -c <worker>/wrangler.toml`.
- Tự động hoá: workflow `.github/workflows/deploy-<worker>.yml` dùng `cloudflare/wrangler-action@v3`,
  `command: deploy -c <worker>/wrangler.toml`, trigger `on.push.paths: [<worker>/**]`.
- Secret cho CI: `gh secret set CLOUDFLARE_API_TOKEN -R <owner>/<repo>` + `CLOUDFLARE_ACCOUNT_ID`
  (token theo template **Edit Cloudflare Workers**; dán trong prompt Terminal, KHÔNG dán vào chat/log).

## Bảo mật
- **KHÔNG dán token/mật khẩu vào chat.** Cloudflare token cho CI: tạo (Edit Cloudflare Workers) → `gh secret set` (dán trong Terminal).
- `~/.claude/ios-apps-registry.json` là local, **KHÔNG commit** vào univ3/dự án.
