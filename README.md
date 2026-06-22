<img width="4320" height="1440" alt="hh26 main poster 2 with sponsors 3x1 (4320 x 1440 px) (2)" src="https://github.com/user-attachments/assets/c698b2cd-da84-4cb0-9276-125c6a7244aa" />

# 🧠 Blinky — AI Desktop Tutor & Agent

> An offline-first, privacy-respecting AI desktop tutor that reads your screen and guides you visually or runs autopilot computer automation.

---

## 📌 Problem & Domain

Learning complex software (like VS Code, Blender, or system configurations) typically involves a lot of context switching between tutorials, videos, static documentation, and the application itself. This creates "tutorial hell" and slows down software onboarding.

Blinky brings the learning experience directly into the active application. By capturing the screen, running local OCR + Windows UIA, and leveraging local or cloud LLMs, Blinky guides users step-by-step with real-time visual highlights directly on their screen.

**Themes Selected (at least one):**
- [x] Human Experience & Productivity  
- [x] Learning & Knowledge Systems  
- [x] Developer Tools & Software Infrastructure  

---

## 🎯 Objective

Blinky serves students, developers, and general users learning to navigate desktop software.

- **Target Users**: Software learners, junior developers, and remote users looking for hands-on, contextual guide steps.
- **Pain Point**: Context-switching, static text manuals, video pacing issues, and lack of visual mapping.
- **Value Provided**: Real-time visual overlay highlighting on the actual screen, offline-first voice read-aloud via Sarvam AI, and hands-free desktop autopilot execution.

---

## 🧠 Team & Approach

### Team Name:  
`Team Blinky`

### Team Members:  
- **Khanna Sparsh** (GitHub: [KhannaSparsh0001](https://github.com/KhannaSparsh0001) / Role: Voice & UI-UX Architect)
- **Sahil** (GitHub: [KingSahil](https://github.com/KingSahil) / Role: Backend & Tauri Developer)
- _[Placeholder] Team Member 3 (LinkedIn / GitHub / Role)_  
- _[Placeholder] Team Member 4 (LinkedIn / GitHub / Role)_

### Your Approach:
- **Why we chose this problem**: Traditional training methods fail because they are separated from the workspace. We wanted a tool that feels like a teacher looking over your shoulder.
- **Key challenges addressed**:
  - **Flicker-Free Screenshots**: Using Windows display affinity flags to exclude Blinky's overlay and command windows from screenshots without closing them.
  - **OCR Coordinates Mapping**: Matching local WinRT OCR box dimensions to physical monitor DPI scales for pixel-perfect overlays and clicking.
  - **Dynamic App Context**: Auto-generating keyboard shortcuts and menus documentation on first app run.
  - **Voice Synchronization**: Creating word-by-word active highlighting synchronized with the Sarvam TTS audio timeline.
- **Pivots & Iterations**: Shifted from pure on-screen highlighting to full autonomous Agent Mode, allowing users to choose between manual guidance and automatic autopilot execution. We also revamped the command bar to place actions at the bottom right like modern assistants (ChatGPT/Copilot).

---

## 🛠️ Tech Stack

### Core Technologies Used:
- **Frontend**: React 19, TypeScript, Vite
- **Desktop Wrapper**: Tauri 2 (Rust desktop shell, global shortcuts, native mouse/keyboard clicks, and local WebSockets on port 9001)
- **Backend**: Python 3.11+
- **OCR Engine**: Windows OCR API (WinRT), Fallback pytesseract
- **Screen Capture**: `dxcam` (DirectX-based high-frame capture)
- **Window Detection**: `pywinauto`
- **APIs**: Sarvam AI (saaras:v3 for Speech-To-Text, bulbul:v3 for Text-To-Speech)
- **Local AI Models**: Ollama (`gemma4:e4b`)
- **Cloud Models (Optional)**: Groq Vision API (`meta-llama/llama-4-scout-17b-16e-instruct`)
- **Search Engine**: SearXNG (for dynamic web search and app context acquisition)

### Additional Technologies Used (Optional):
- [x] AI / ML  
- [ ] Web3 / Blockchain  
- [ ] Cyber Security  
- [x] Cloud  

---

## 🏆 Sponsored Track (Optional)

Select if your project participates in any track:

- [x] **Expo Track** – Built using Expo  
- [ ] **Neo4j Track** – Uses AuraDB as primary database  
- [ ] **Base44 Track** – Prototype/Final Product built using Base44  

Provide a short note on how you used the partner technology:

> Under `common/mobile/`, we built an **Expo-powered mobile companion app**. It connects directly to the desktop Tauri WebSocket server (port 9001), allowing users to send voice commands and monitor autopilot workflows directly from their phone.

---

## ✨ Key Features

- 🤖 **Full Agent Mode (Computer Use)**: Autonomously launches apps, plays Spotify tracks, presses shortcuts, and types text natively.
- 🎨 **Modern Chatbar UI (ChatGPT/Copilot Layout)**: Features actions grouped at the bottom, with Mic, Read-Aloud, and Send aligned on the bottom right.
- 🗣️ **Sarvam AI Voice Integration**: Indian-context speech-to-text dictation and text-to-speech readbacks.
- 🏷️ **Dynamic Word Highlighting**: Fades out unspoken text, highlighting the active word dynamically as the voice readback plays.
- 🧭 **Bounded Autopilot Loop**: Safety-gated observe-act loop running up to 5 times for clicking, typing, and scrolling.
- 🌐 **Web Intelligence Search**: Integrates SearXNG local instances to query answers and resolve URIs offline.
- 🛡️ **Flicker-Free Screen Capture**: Uses native `SetWindowDisplayAffinity` to exclude the overlay from captures, ensuring the AI model gets a clean screenshot.

---

## 📽️ Demo & Deliverables

- **Demo Video Link (Mandatory):** _[Paste YouTube/Loom Link]_  
- **Deployment Link (Recommended):** _[Paste Tauri Build Releases Link]_  
- **Pitch Deck / PPT (Optional):** _[Paste Canva/Google Slides Link]_  

---

## ✅ Tasks & Bonus Checklist

- [ ] All team members completed the mandatory social task  
- [ ] Bonus Task 1 – Badge sharing  
- [ ] Bonus Task 2 – Blog/article  

---

## 🧪 How to Run the Project

### Requirements:
- Node.js / Bun (1.3.14+)
- Rust (Stable)
- Python (3.11+)
- Ollama
- Docker (Optional, for local search)

### Environment Configuration:
Create a `.env` file in the project folder with:
```bash
SARVAM_API_KEY="your-sarvam-key-here"
# To use Groq instead of Ollama:
BLINKY_AI_PROVIDER="groq"
GROQ_API_KEY="your-groq-key-here"
```

### Local Setup:
1. **Pull the Local Model**:
   ```bash
   ollama pull gemma4:e4b
   ```
2. **Install Dependencies**:
   ```bash
   bun install
   bun run setup:python
   bun run check:ollama
   ```
3. **Start SearXNG (Optional)**:
   ```bash
   docker compose up -d searxng
   ```
4. **Run Blinky in Dev Mode**:
   ```bash
   bun run dev
   ```

### ⌨️ Global Shortcuts:
- **Main Open**: `CTRL + SHIFT + SPACE`
- **Fallback Open**: `CTRL + SHIFT + ENTER`

---

## 📂 Project Structure

```text
common/
├── src-tauri/
│   ├── Rust desktop shell
│   ├── Overlay window
│   ├── Global hotkeys
│   ├── WebSocket server (port 9001)
│   └── Native SendInput clicking + scrolling
│
├── frontend/src/
│   ├── CommandBar.tsx       Primary command UI (voice, agent, autopilot)
│   ├── Overlay.tsx          Transparent highlight layer
│   ├── lib/autopilot.ts     Bounded observe-act loop (click/type/scroll)
│   ├── lib/guidance.ts      Step state helpers
│   ├── lib/tauri.ts         Typed Tauri command wrappers
│   ├── lib/tts.ts           Sarvam TTS/STT helpers
│   └── lib/webGuidance.ts   Browser intelligence bridge
│
├── python/
│   ├── main.py              Screen tutor orchestrator + intent router
│   ├── agent_router.py      Remote browser-agent sidecar
│   ├── browser_agent.py     Safe JSON browser planner
│   ├── browser_controller.py Playwright Edge controller
│   ├── ai/
│   │   ├── prompt.py        Preflight + screen + chat prompt builders
│   │   ├── client.py        Provider router (Ollama / Groq)
│   │   ├── ollama_client.py Local Ollama client
│   │   └── groq_client.py   Groq vision + text client
│   ├── app_context/
│   │   ├── registry.py      Dynamic app context generator (SearXNG + LLM)
│   │   ├── vscode.md        VS Code navigation guide
│   │   ├── browser.md       Chrome/Edge navigation guide
│   │   ├── whatsapp.root.md WhatsApp shortcuts guide
│   │   ├── chatgpt.md       ChatGPT desktop guide
│   │   ├── systemsettings.md Windows Settings guide
│   │   └── ...              Auto-generated guides for other apps
│   ├── capture/screen.py    Screenshot capture + Screenshot dataclass
│   ├── computer_use/
│   │   ├── agent.py         Intent regex router
│   │   └── tools.py         open_app, shortcut, play_spotify tools
│   ├── ocr/extract.py       OCR provider registry (WinRT / tesseract)
│   ├── tools/
│   │   ├── registry.json    Registered browser/data tool schemas
│   │   ├── find_crypto_price.py
│   │   ├── lookup_wikipedia_entity.py
│   │   ├── lookup_youtube_stats.py
│   │   └── search_product_info.py
│   ├── utils/
│   │   ├── matching.py      Fuzzy target matcher
│   │   ├── ui_map_cache.py  Stable @ref UI element cache
│   │   ├── screen_elements.py @ref assignment
│   │   ├── sufficiency_checker.py LLM tool output auditor
│   │   ├── generalizer.py   Background tool generalization
│   │   ├── uia.py           Windows UIA extraction
│   │   └── window.py        Active window + overlay exclusion
│   └── wil/
│       ├── pipeline.py      Web Intelligence Layer orchestrator
│       ├── searxng_client.py SearXNG JSON client
│       ├── acquirer.py       Source page fetcher
│       ├── http_fetcher.py   HTTP fetch helper
│       ├── browser_engine.py Playwright fallback fetcher
│       ├── processor.py      Source text cleaner
│       └── reasoner.py       LLM answer synthesizer
│
├── mobile/
│   ├── App.tsx              Expo remote controller UI
│   └── usePCWebSocket.ts    WebSocket hook (ws://host:9001)
│
├── shared/
│   └── clicky-result.schema.json   Result JSON schema
│
└── searxng/                 SearXNG configuration files

windows/                     Windows configuration & setup scripts
└── scripts/
    ├── setup-python.ps1
    └── check-ollama.ps1

linux/                       Linux configuration & setup scripts
└── scripts/
    ├── setup-python.sh
    ├── check-ollama.sh
    └── groq-check.sh
```

---

## 🧬 Future Scope

- 📈 **More Integrations**: Control tools for major developer software suites (Docker, Kubernetes dashboards, cloud consoles).
- 🛡️ **Enhanced Sandbox Protection**: Sandboxed execution mode for the Agent Mode to verify instructions in safe virtual states before desktop typing/clicking.
- 🌐 **Deep Localization**: Supporting regional languages using Sarvam API for multi-lingual tutors.
- 🕶️ **Multi-Monitor Layouts**: Autopilot click mapping extended to multiple monitor coordinate frames.

---

## 📎 Resources / Credits

- **APIs**: Sarvam AI API for Speech features, Groq Vision API.
- **Libraries**: Tauri, React, ReactMarkdown, dxcam, WinRT OCR APIs, pywinauto, Playwright.
- **Acknowledgements**: Inspired by modern assistive agents and built for hackathon learners worldwide.

---

## 🏁 Final Words

Blinky has been a thrilling journey of integrating Rust (Tauri), React, and Python sidecars into a single, cohesive desktop assistant. Solving overlay flickering and mapping OCR coordinates to physical DPI frames was a major engineering obstacle, but seeing the visual guide draw directly on top of target apps made every hour of development worth it!
