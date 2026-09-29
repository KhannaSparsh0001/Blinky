<img width="4320" height="1440" alt="hh26 main poster 2 with sponsors 3x1 (4320 x 1440 px) (2)" src="https://github.com/user-attachments/assets/c698b2cd-da84-4cb0-9276-125c6a7244aa" />

<div align="center">

# 🧠 Blinky — AI Desktop Tutor, Autonomous Agent & Workstation Companion

> An offline-first, privacy-respecting AI desktop tutor and remote workstation companion that reads your screen, guides you visually, runs background headless computer automation via Hermes `cua-driver`, bridges to mobile over encrypted WebSocket, and synchronizes with physical IoT hardware.

<br>

### _Ask. Learn. Automate. Control from Anywhere._

<br>

<p align="center">

<img src="https://img.shields.io/badge/Tauri-2.x-orange?style=for-the-badge">
<img src="https://img.shields.io/badge/React-19-61dafb?style=for-the-badge">
<img src="https://img.shields.io/badge/Bun-1.3.14-f9f1e1?style=for-the-badge">
<img src="https://img.shields.io/badge/Python-3.11-yellow?style=for-the-badge">
<img src="https://img.shields.io/badge/Expo-SDK%2057%20(RN%200.86)-black?style=for-the-badge">

</p>

<p align="center">

<img src="https://img.shields.io/badge/Actuator-cua--driver%200.28.1%20(Hermes)-purple?style=for-the-badge">
<img src="https://img.shields.io/badge/Groq-Llama%203.3%2070B%20%26%20Qwen%2027B-purple?style=for-the-badge">
<img src="https://img.shields.io/badge/Ollama-gemma4:e4b-green?style=for-the-badge">
<img src="https://img.shields.io/badge/Vision-OmniParser%20%2B%20WinRT-blue?style=for-the-badge">

</p>

<p align="center">

<img src="https://img.shields.io/badge/Voice-Sarvam%20AI%20(saaras%20%2B%20bulbul)-red?style=for-the-badge">
<img src="https://img.shields.io/badge/Hardware-ESP32%20Ambient%20Sync-darkgreen?style=for-the-badge">
<img src="https://img.shields.io/badge/Monetization-RevenueCat%20%2B%20Vouchers-blue?style=for-the-badge">

</p>

<br>

![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20Android-blue)
![License](https://img.shields.io/badge/license-MIT-purple)

</div>

---

Blinky is an AI-powered desktop tutor and autonomous workstation agent. In tutor mode, it observes your screen, runs local WinRT OCR and Microsoft OmniParser bounding-box grounding, and guides you with real-time visual highlights and word-by-word synchronized voice guidance. In **Agent Mode**, it executes desktop tasks entirely autonomously in the background using the **`cua-driver` (Hermes engine)** without stealing your mouse focus. With its **Expo-powered Mobile Companion**, Blinky bridges to your phone for live IDE monitoring, remote PC telemetry, Wake-on-LAN power controls, remote file explorer sync, and physical ESP32 ambient lighting synchronization.

---

## 📌 Problem & Domain

Learning complex software (like VS Code, Blender, CAD, or system configurations) typically involves constant context switching between tutorials, video timestamps, static manuals, and the application workspace. This induces "tutorial hell" and stalls productivity.

Blinky brings the learning experience and autonomous task execution directly into the active application. By capturing the screen, extracting accessibility trees via Windows UIA and OmniParser, and leveraging high-performance local or cloud LLMs, Blinky guides users step-by-step or handles repetitive workflows autonomously.

**Themes Selected:**
- [x] Human Experience & Productivity  
- [x] Learning & Knowledge Systems  
- [x] Developer Tools & Software Infrastructure  

---

## 🎯 Objective

Blinky serves software learners, power users, and remote developers:
- **Pain Points Addressed**: Context-switching, static manuals, inability to multitask while agents hijack mouse input, and lack of mobile visibility into desktop workflows.
- **Value Provided**: Non-intrusive on-screen overlay highlighting, background headless desktop automation, low-latency Sarvam AI voice guidance, and an encrypted mobile companion with remote power and filesystem management.

---

## 🧠 Team & Approach

### Team Name:  
`Tech Nerds`

### Team Members:  
- **Sparsh Khanna** (GitHub: [KhannaSparsh0001](https://github.com/KhannaSparsh0001) / Role: Voice & UI-UX Architect)
- **Sahil** (GitHub: [KingSahil](https://github.com/KingSahil) / Role: Backend & Tauri Developer)
- **FeV-06** (GitHub: [FeV-06](https://github.com/FeV-06) / Role: Mobile and Linux Developer)
- **meharwanfr** (GitHub: [meharwanfr](https://github.com/meharwanfr) / Role: Linux Developer)

### Engineering Highlights & Milestones:
- **Headless Actuation via `cua-driver`**: Replaced foreground pointer hijacking with Nous Research's `cua-driver 0.28.1`. Actions execute on background windows without stealing mouse focus or switching virtual desktops.
- **Flicker-Free Screen Capture**: Uses Windows Display Affinity (`WDA_EXCLUDEFROMCAPTURE`) to make Blinky's overlay completely invisible to the AI screen grabber while remaining visible to the user.
- **OmniParser & UIA Element Trees**: Integrates Microsoft OmniParser for bounding-box grounding and parses up to 1,000+ native Windows UIA elements for precision targeting.
- **Voice Timeline Synchronization**: Word-by-word active text highlights dynamically aligned with the Sarvam TTS audio timeline.
- **Multi-Device Companion**: Encrypted WebSocket transport with token authentication, Wake-on-LAN power triggers, remote Windows Credential Provider unlock, and remote file sync.

---

## 🛠️ Tech Stack

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Desktop Shell** | Tauri 2 (Rust) | Native window management, system tray, hotkeys, authenticated WebSocket gateway (`:9001`) |
| **Desktop Frontend** | React 19 + TypeScript (Vite) | Floating command bar, overlay highlights, companion cursor |
| **Mobile Companion** | Expo SDK 57 / React Native 0.86 | Remote dashboard, IDE bridge, telemetry, file sync, paywall |
| **Actuator & Driver** | `cua-driver 0.28.1` (Hermes Engine) | Background headless desktop actuation; fallback to native `SendInput` / `pywinauto` |
| **AI Models (Cloud)** | Groq `llama-3.3-70b-versatile` & `qwen/qwen3.6-27b` | High-speed reasoning, vision grounding, and preflight intent classification |
| **AI Models (Local)** | Ollama `gemma4:e4b` | 100% offline private local inference |
| **Vision & Screen Grounding** | Microsoft OmniParser + Windows WinRT OCR + dxcam | High-frame DirectX capture, UI element parsing, coordinate mapping |
| **Voice Engine** | Sarvam AI `saaras:v3` (STT) + `bulbul:v3` (TTS) | Real-time Indian-accented speech-to-text and synchronized text-to-speech readbacks |
| **Web Automation** | Playwright + WhatsApp Web (`wwebjs_auth`) | Headless browser execution and WhatsApp session management |
| **Local Search** | SearXNG + Docker Compose | Offline-first, privacy-respecting metasearch |
| **IoT Hardware** | ESP32 Universal Micro-Daemon | Physical desk ambient lighting synced with agent states |
| **Monetization** | RevenueCat SDK + Offline Promo Code Engine | Pro feature gating for PC telemetry and remote power actions |

---

## 🏆 Sponsored Track Participation

- [x] **Expo Track** – Built a full-featured mobile companion app (`common/mobile`) under React Native 0.86 and Expo SDK 57, featuring WebSocket auto-discovery, live IDE streaming, file transfer, and remote power controls.
- [x] **Sarvam Track** – Integrated Sarvam AI `saaras:v3` (STT) and `bulbul:v3` (TTS) with real-time word-by-word visual synchronization.
- [x] **Base44 Track** – Built and deployed our interactive showcase and download portal at [blinky.base44.app](https://blinky.base44.app).
- [ ] **Neo4j Track**

---

## ✨ Key Features

### 🤖 1. Headless Background Computer-Use (`cua-driver` / Hermes Actuator)
Blinky integrates `cua-driver 0.28.1` (the actuator powering Nous Research's Hermes Agent) for autonomous desktop execution:
- **Zero Cursor Hijacking**: Executes clicks, keyboard input, and window interactions in the background without stealing user focus or moving the physical mouse.
- **Deep UIA Element Trees**: Queries Windows Accessibility APIs to inspect 1,000+ UI elements on screen with native roles and screen-absolute bounding boxes.
- **Virtual Companion Cursor**: Renders an aesthetic visual overlay cursor to show the user what Blinky is pointing to without interfering with active user typing.
- **Bounded Autopilot**: Executes multi-step observe-act loops with robust fallback to native `SendInput` when background actuation is unsupported.

### 📱 2. Expo Mobile Companion & Antigravity IDE Bridge (`common/mobile`)
Connect your Android/iOS phone over LAN, USB port forwarding (`adb reverse tcp:9001 tcp:9001`), or Tailscale:
- **Antigravity IDE Remote Bridge**: Live-streams agent thinking steps, shell outputs, and transcript milestones straight to your phone. Approve CLI permissions with a single tap.
- **Sentinel PC Telemetry & Power Controls**: Real-time meters for PC CPU %, RAM usage, and battery/AC power. Dispatch remote Sleep, Restart, Hibernate, or wake the PC via **Wake-on-LAN (WoL)** magic packets.
- **Bi-Directional File Explorer**: Remotely browse your PC filesystem from your phone, save images/videos to your camera roll, or batch-upload photos and documents directly to your desktop agent.
- **Windows Remote Unlock**: Unlock locked Windows desktop sessions securely from your phone via our custom Windows Credential Provider DLL.

### 💬 3. Full WhatsApp Web Automation Engine
- Powered by `wwebjs_auth` with headless Chromium session management.
- Quick in-app QR code pairing directly from the desktop command bar.
- Summarize chat threads, extract contact updates, and query WhatsApp messages using fast-path token-saving LLM routing.

### 💡 4. Hardware Ambient Sync (ESP32 Micro-Daemon)
- Direct UART / Wi-Fi communication with physical ESP32 microcontrollers (`esp32_firmware/`).
- Synchronizes desk ambient RGB lighting with Blinky's live state (idle, listening, thinking, executing, success, error).

### 🎬 5. AiCut Multimodal Video & Media Pipeline
- Automated video concatenation, background music ducking, and auto-generated subtitle burning.
- Natural language video trimming powered by Google Gemini Vision.
- Whisper audio forced alignment for precise caption placement.

### 💳 6. RevenueCat In-App Monetization & Offline Vouchers
- **RevenueCat Paywall**: Protects advanced PC telemetry and remote power actions behind `react-native-purchases`.
- **Store-Independent Promo Engine**: Fully offline voucher redemption (`SHIPATHON`, `BLINKYVIP`, `EARLYBIRD`) allowing judges and direct APK sideload users to unlock Pro features without Google Play billing.

### 🗣️ 7. Sarvam AI Voice & Dynamic Word Highlighting
- Real-time speech recognition (`saaras:v3`) and high-fidelity Indian-accented speech synthesis (`bulbul:v3`).
- **Dynamic Word Highlighting**: Fades out unspoken text, highlighting the active word dynamically as the voice readback plays in sync with the audio duration timeline.

### 🗂️ 8. Dynamic App Context Generation
- Auto-generates markdown navigation guides for any newly encountered desktop app by searching SearXNG for shortcuts and synthesizing a structured guide cached in `python/app_context/`.

---

## 📽️ Demo & Deliverables

- **Demo Video Link (Mandatory):** [YouTube Video](https://youtu.be/CHFF9J_Jqgw)
- **Deployment Link (Recommended):** [blinky.base44.app](https://blinky.base44.app)
- **Pitch Deck / PPT (Optional):** [Blinky Presentation Deck](https://docs.google.com/presentation/d/10isbvsbzb3Xm2RzeHyaA_FQqcjUTUzRipflrhuyABRY/edit?slide=id.g3f49da6dcbc_0_157#slide=id.g3f49da6dcbc_0_157)
- **Technical Blog:** [Building Blinky: Fighting CAPTCHAs, Invisible Windows, and the Agony of Visualizing AI](https://medium.com/@khannasparsh0001/building-blinky-fighting-captchas-invisible-windows-and-the-agony-of-visualizing-ai-b1247b9fc324?sharedUserId=khannasparsh0001)

---

## 🧪 How to Run the Project

### Prerequisites
- **Bun** 1.3+
- **Rust** Stable
- **Python** 3.11+
- **Node.js** & **Expo CLI** (for mobile companion)
- **Ollama** (optional, for local offline inference)
- **Docker** (optional, for local SearXNG search)

---

### 1️⃣ Setup Desktop Core (One-Click)

#### Windows (Recommended):
```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1
# or: bun run setup
```
*Checks Bun/Rust/Python, installs npm packages, builds Python `.venv`, installs Playwright browsers, and initializes `.env`.*

#### Linux:
```bash
chmod +x setup.sh && ./setup.sh
# or: bun run setup:linux
```

---

### 2️⃣ Start Blinky Desktop

```bash
bun run dev
```

- **Main Hotkey**: `CTRL + SHIFT + SPACE`
- **Fallback Hotkey**: `CTRL + SHIFT + ENTER`

*(Optional) Start local SearXNG search engine:*
```bash
docker compose -f common/docker-compose.yml up -d
```

---

### 3️⃣ Start Mobile Companion (`common/mobile`)

```bash
cd common/mobile
bun install
bun run start
```
- Scan the QR code using Expo Go or run on a connected Android phone:
```bash
# Connect via USB port forwarding
connect_usb.bat

# Install standalone APK directly
install_apk.bat
```

---

## 📂 Project Structure

```text
Blinky/
├── common/
│   ├── src-tauri/                   Tauri 2 Rust shell, WS gateway (:9001), Windows Credential DLL
│   │   ├── src/lib.rs               Window affinity, hotkeys, and secure WebSocket server
│   │   └── tauri.conf.json          Tauri window and strict CSP security configuration
│   │
│   ├── frontend/src/                React 19 desktop webview UI
│   │   ├── CommandBar.tsx           Primary floating command hub & voice synthesizer
│   │   ├── Overlay.tsx              Transparent screen highlight & companion cursor layer
│   │   └── lib/autopilot.ts         Observe-act bounded autopilot execution loop
│   │
│   ├── mobile/                      Expo SDK 57 / React Native 0.86 companion app
│   │   ├── App.tsx                  Dashboard, tab router, and WebSocket subscriber
│   │   ├── components/              Modular UI screens
│   │   │   ├── SystemScreen.tsx     Sentinel hardware telemetry, power controls, and WoL
│   │   │   ├── FilesScreen.tsx      Remote PC file explorer & camera roll sync
│   │   │   ├── PromoCodeModal.tsx   Offline voucher bypass sheet
│   │   │   ├── SlashCommandMenu.tsx Antigravity IDE slash command bar
│   │   │   └── BottomNavigation.tsx Tab navigation with Pro lock indicators
│   │   ├── lib/purchases.ts         RevenueCat SDK + Offline Promo Code Engine
│   │   ├── usePCWebSocket.ts        Duplex WSS transport with ?token= authentication
│   │   └── eas.json                 EAS standalone Android APK build profiles
│   │
│   └── python/                      Python 3.11 AI & automation daemon
│       ├── main.py                  Screen tutor orchestrator and preflight intent classifier
│       ├── computer_use/            Actuation engine
│       │   ├── backends/cua_driver.py cua-driver (Hermes) background desktop actuator
│       │   ├── backends/base.py     Platform-neutral computer-use abstractions
│       │   └── tools.py             Desktop automation tools (app launch, shortcuts, Spotify)
│       ├── ai/                      Model provider routing (Groq Llama 3.3 / Ollama gemma4)
│       ├── ocr/                     Microsoft OmniParser and WinRT OCR extraction
│       └── whatsapp_backend/        Headless Chromium WhatsApp Web automation
│
├── esp32_firmware/                  ESP32 universal micro-daemon for ambient lighting sync
├── docs/                            Comprehensive architecture, Hermes plan, and security guides
│   ├── HERMES-INTEGRATION-PLAN.md   Detailed cua-driver actuator documentation
│   ├── LINUX-PORT-ROADMAP.md        Wayland/X11 Linux porting progress
│   ├── SECURITY-REMEDIATION.md      WebSocket auth hardening & CSP policy
│   ├── history.md                   Full post-100 commits architectural evolution
│   └── REVENUECAT-AND-ANDROID-DISTRIBUTION-GUIDE.md  RevenueCat audit & APK packaging guide
│
├── setup.ps1                        Automated Windows installation script
└── setup.sh                         Automated Linux installation script
```

---

## 🔒 Security & Privacy

- **Authenticated WebSocket Transport**: Every command sent from the mobile companion requires secret token verification (`?token=`), hardened against unauthorized LAN access.
- **Strict Content Security Policy (CSP)**: Tauri webview CSP strictly prevents credential exfiltration.
- **Automated Firewall Rules**: Windows NSIS installer automatically configures restrictive inbound firewall rules for port `9001`.
- **Local Processing**: Offline-first screen OCR via Windows WinRT and local LLM inference via Ollama ensure zero screenshots leave your machine unless cloud Groq inference is explicitly enabled.

---

## 📎 Resources & Credits

- **Actuation**: Built on [cua-driver](https://github.com/nousresearch) by Nous Research.
- **Voice**: [Sarvam AI](https://sarvam.ai) for multilingual speech-to-text (`saaras:v3`) and text-to-speech (`bulbul:v3`).
- **Vision**: Microsoft OmniParser for bounding-box grounding and DirectX `dxcam` for high-speed capture.
- **Mobile**: Built with [Expo](https://expo.dev) and [React Native](https://reactnative.dev).
- **Desktop**: Powered by [Tauri 2](https://v2.tauri.app) and [React 19](https://react.dev).
