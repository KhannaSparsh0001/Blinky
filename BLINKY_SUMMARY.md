# 🧠 Blinky — Project Summary & Architecture Overview

> **"Ask. Learn. Click. Done."**
> An offline-first, privacy-respecting AI desktop tutor and autonomous computer-use agent for Windows and Linux, accompanied by a React Native (Expo) mobile companion, a pure-Rust agent & OS daemon, a local System 1 neural decision engine, an Offline Knowledge Format (OKF) notebook workspace, an AiCut C++ video editing suite, an Antigravity IDE bridge, an ESP32 hardware daemon, and a WhatsApp bridge.

---

## 1. System Architecture Map

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 DESKTOP HOST (Tauri 2)                                 │
│                                                                                        │
│  ┌───────────────────────┐             ┌────────────────────────────────────────────┐  │
│  │  Frontend (React 19)  │             │   Rust Core (Tauri 2)                      │  │
│  │  - CommandBar         │◄── IPC ────►│   - Multi-window Overlay (WDA_EXCLUDE)     │  │
│  │  - Visual Overlay     │             │   - WS Gateway (:9001, TLS Public-Pinning) │  │
│  │  - Sarvam Word Sync   │             │   - File Server (:9002, 16MB Chunk Stream) │  │
│  │  - Notebook Hub View  │             │   - Process Lifecycle & Security Guard     │  │
│  └───────────────────────┘             └─────────────┬──────────────────────────────┘  │
│                                                      │ Sockets / stdio IPC             │
│  ┌───────────────────────────────────────────────────┴──────────────────────────────┐  │
│  │  Autonomous Execution & Reasoning Engines                                        │  │
│  │                                                                                  │  │
│  │  ┌────────────────────────────────────┐  ┌────────────────────────────────────┐  │  │
│  │  │ Pure Rust Agent (crates/blinky-agent)│  │ Pure Rust Daemon (crates/blinky-daemon)│  │
│  │  │ - Multi-provider (OpenAI/Groq/Ollama)│ │ - Headless Linux (Wayland/X11)     │  │  │
│  │  │ - Native Rust Tools (desktop/system)│  │ - PipeWire Capture & ATSPI2 Tree   │  │  │
│  │  │ - Embedded Vector Store (rusqlite)  │  │ - /dev/uinput & Coordinate Mapping │  │  │
│  │  └────────────────────────────────────┘  └────────────────────────────────────┘  │  │
│  │                                                                                  │  │
│  │  ┌────────────────────────────────────┐  ┌────────────────────────────────────┐  │  │
│  │  │ System 1 Decision Engine (ONNX)    │  │ Notebook Hub & OKF Engine          │  │  │
│  │  │ - <1ms Transformer / ONNX Classifier│ │ - Full-Context Structured Docs     │  │  │
│  │  │ - Non-autoregressive Reflex Router │  │ - "▶ Execute on PC" Action Links   │  │  │
│  │  │ - Calibrated Temperature Logits    │  │ - sqlite-vec & MiniSearch Fallback │  │  │
│  │  └────────────────────────────────────┘  └────────────────────────────────────┘  │  │
│  │                                                                                  │  │
│  │  ┌────────────────────────────────────┐  ┌────────────────────────────────────┐  │  │
│  │  │ Python Backend Services            │  │ AiCut Suite & MCP Server           │  │  │
│  │  │ - Capture: dxcam, Portal, PipeWire │  │ - C++17 Core Engine + CMake        │  │  │
│  │  │ - Grounding: WinRT OCR, OmniParser │  │ - faster-whisper Forced Alignment  │  │  │
│  │  │ - Actuation: SendInput, ydotool    │  │ - FFmpeg Trimming & Silence Cut    │  │  │
│  │  │ - Antigravity IDE Bridge (:9003)   │  │ - JSON-RPC / MCP Server protocol   │  │  │
│  │  └────────────────────────────────────┘  └────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────▲───────────────────────────────▲────────────────────────────┘
                            │ WSS (:9001) / HTTPS (:9002)   │ Serial / UDP / Webhooks
┌───────────────────────────▼─────────────────┐   ┌─────────▼────────────────────────────┐
│   Expo Mobile Companion (React Native 57)   │   │ External Peripherals & Integrations  │
│   - Standalone APK with Android KeyStore    │   │ - ESP32 Smart Light (NeoPixels)      │
│   - Sentinel Telemetry, Remote WoL & Power  │   │ - WhatsApp Web Headless Bridge       │
│   - Antigravity IDE Realtime Progress/HITL  │   │ - Antigravity IDE Lifecycle Hooks    │
│   - 16MB Chunked File Transfer & AiCut Sync │   └──────────────────────────────────────┘
└─────────────────────────────────────────────┘
```

---

## 2. System 1 Neural Decision Engine (`decision_engine/`)

Blinky introduces a two-tier cognitive routing architecture distinguishing sub-millisecond reflexes (System 1) from deliberative multi-step reasoning (System 2):

* **Sub-Millisecond Inference (<1ms):** Powered by an exported sequence-classification Transformer (`decision_engine/infer.py` and `export_onnx.py`) that operates directly on CPU/GPU without token-by-token autoregressive LLM overhead.
* **Calibrated Logit Temperature:** Uses calibrated softmax probabilities (`calibration.json`) to classify incoming intents into routing domains:
  1. `daemon_system` — Direct OS-level commands (volume, brightness, power, lock) requiring zero LLM processing.
  2. `ocr_exact` — Pure textual UI targets directly resolvable via fast OCR coordinate lookup.
  3. `vision_spatial` — Spatial layout queries (e.g. "top-right button", "next to search bar").
  4. `vision_visual` — Visual icon/graphic queries requiring OmniParser YOLO detection.
  5. `hybrid_consensus` — Cross-modal queries combining text and visual cues.
  6. `complex_goal` — Complex multi-step instructions dispatched to System 2 agent loops.
* **Quoted Entity Extraction:** Automatically parses quoted targets (`"Save"`, `'Project Settings'`) in <0.1ms via regex parsing for zero-shot atomic dispatch.

---

## 3. Pure Rust Agent & Headless Linux Daemon (`crates/`)

To achieve maximum performance and minimize resource consumption, Blinky includes native Rust crates alongside its Python subsystem:

### A. Pure Rust Autonomous Agent (`crates/blinky-agent`)
Activated optionally via `BLINKY_USE_NATIVE_AGENT=1`, this is an ultra-fast, standalone Rust autonomous agent loop:
* **Multi-Provider AI Engine:** Direct HTTP/2 streaming client supporting OpenAI, Anthropic, Gemini, Groq, and Ollama (`src/providers/`).
* **Native Tool Registry:** Fully implemented Rust tools in `src/tools/`:
  * `desktop.rs` — Screen grounding, UI element discovery, and input actuation.
  * `system.rs` — OS controls, processes, power states, and application launching.
  * `esp32.rs` — UDP/HTTP commands for physical ambient smart light peripherals.
  * `ide_bridge.rs` — Direct bidirectional IPC with IDE environments.
  * `reflex.rs` — Ultra-fast deterministic rule-based command dispatch.
  * `utility.rs` — Math, clipboard, time, and system utilities.
  * `wil.rs` — Web-In-The-Loop automated browser navigation.
* **Embedded Vector RAG:** Built-in PDF extraction (`lopdf`) and vector storage (`rusqlite`) for offline document question-answering without external services.

### B. Pure Rust Headless Linux Daemon (`crates/blinky-daemon`)
A dedicated Linux automation daemon designed for modern Wayland and X11 compositors:
* **Hyprland & wlroots First-Class Support:** Communicates with Hyprland IPC sockets for window tracking and workspace management.
* **Direct Input Synthesizer:** Emits keystrokes, pointer movements, and touch events via Linux `/dev/uinput` and `evdev`.
* **AT-SPI2 Accessibility Integration:** Inspects application accessibility trees directly via DBus (`zbus`) for instant UI hierarchy retrieval.
* **PipeWire & Portal Screen Capture:** Captures high-frame-rate desktop surfaces securely via `xdg-desktop-portal` and PipeWire streams.

---

## 4. Blinky Notebook Hub & OKF (Offline Knowledge Format)

Inspired by personal intelligence workspaces (like NotebookLM), Blinky incorporates a dedicated **Notebook Hub** (`common/python/notebooks/`, `docs/OKF.md`):

* **OKF as a Direct Substitute for RAG:**
  * For small-to-medium documents (PDFs, manuals, app context guides) that fit within modern 128k–1M context windows, traditional vector chunking fragments semantic coherence.
  * OKF parses documents into high-density structured Markdown, preserving headers, lists, code blocks, and context integrity.
  * **Zero Embedding Latency:** Eliminates heavy embedding model downloads and inference latencies on mobile devices and low-spec PCs.
* **"▶ Execute on PC" Actionable Desktop Citations:**
  * If a notebook source mentions software instructions (e.g. *"How to export audio in FL Studio"* or *"Git rebase instructions"*), citations render an actionable **"▶ Execute on PC"** button.
  * Clicking the button directly routes coordinates and shortcuts into Blinky's desktop actuation engine.
* **Studio Artifacts:** One-click generation of Executive Summaries, FAQs, Action Plans, and Study Guides from active notebook sources.
* **Standalone Mobile Mode (`Blinky.apk` via Expo):**
  * When mobile pairs with desktop, PC securely syncs encrypted API keys to **Android KeyStore** (`EncryptedSharedPreferences`).
  * When PC is powered off, `Blinky.apk` operates completely standalone, querying cloud LLMs (Groq, Gemini, DeepSeek) directly from the phone.
  * Incorporates hybrid fallback: `sqlite-vec` / BM25 on PC, and lightweight `MiniSearch` JS on mobile.

---

## 5. AiCut C++17 Video Processing Suite & MCP Server (`common/aicut/`)

Blinky includes a high-performance local video editing engine accessible from both desktop UI, mobile companion, and AI agent tool calling:

* **High-Performance C++17 Core:** Native CMake build utilizing FFmpeg libraries for frame-accurate video slicing, multi-track audio merging, and lossy/lossless transcoding.
* **Word-Level Forced Audio Alignment:** Integrates `faster-whisper` and forced alignment algorithms to compute exact millisecond timestamps for every spoken word.
* **Intelligent Silence Cutting:** Detects silence gaps in speech tracks with customizable decibel thresholds, automatically trimming video dead-air.
* **AiCut MCP Server (`aicut_mcp.py`):** Model Context Protocol (MCP) server exposing tools for natural language video editing:
  * `cut_video` / `trim_video` — Time-range and timestamp-based cuts.
  * `remove_silence` — Audio amplitude silence stripping.
  * `align_script_subtitles` — Subtitle generation and burning (ASS/SRT styles).
  * `merge_audio_video` — Multi-track mixing with background music ducking.

---

## 6. Antigravity IDE Realtime Bridge & Mobile HITL Gate

Blinky connects directly with AI coding assistants (such as Google Antigravity IDE) via a dedicated webhook bridge (`common/python/antigravity_bridge.py`):

* **Port 9003 Webhook Listener:** Receives lifecycle hooks (`PreInvocation`, `PostToolUse`, `Stop`) from the IDE agent.
* **Realtime Terminal Streaming:** Converts IDE file edits, terminal commands, and grep searches into clean, human-readable status updates streamed directly to the mobile chatbar (`Running: pytest...`, `Editing main.py`).
* **Mobile Human-in-the-Loop (HITL) Safety Gate:** Whenever a dangerous desktop action or privileged IDE tool is requested, Blinky prompts the user with an interactive approval card on their phone to allow or abort execution.

---

## 7. Vision, Grounding & Computer-Use Automation

* **Hybrid Vision Engine:** Combines WinRT OCR / Tesseract with OmniParser YOLO icon detection (`model.pt`) and OS accessibility trees (UIA on Windows, AT-SPI2 on Linux).
* **`@ref` Spatial Indexing:** Assigns stable `@ref` identifiers (e.g. `@e14`) to every interactive screen element with a 2-second IOU and text-similarity cache.
* **Desktop Occlusion & Taskbar Partitioning:** Correctly excludes the Windows Taskbar, hidden system trays, and off-screen windows from interactive coordinates.
* **Fast Folder Launcher (`folder_launcher.py`):** Direct Windows Explorer folder launching with rapid path normalization and URI protocol execution.
* **Bounded Autopilot Loop:** Executes full UI tasks (up to 5 autonomous attempts per action) supporting clicks, text typing into focused controls, keyboard shortcuts, and directional scrolling (`SendInput` on Windows / `ydotool` on Linux).
* **Web in the Loop (WIL):** Playwright + Chromium/Edge automation backed by local SearXNG search for autonomous web tasks.

---

## 8. Voice & Audio Sync (Sarvam AI & Local Wake Word)

* **Speech-to-Text (STT):** Real-time multilingual voice command dictation via Sarvam `saaras:v3`.
* **Text-to-Speech (TTS):** Natural Indian-accented voice guidance and audio read-aloud via Sarvam `bulbul:v3`.
* **Synchronized Dynamic Word Highlighting:** Fades out unspoken text while dynamically highlighting the active word in real time matching the Sarvam TTS audio timeline.
* **Local Offline Wake Word:** Zero-latency wake phrase detection powered by bundled `hey_blinky.onnx` executed via ONNX Runtime.

---

## 9. Expo Mobile Companion App (`common/mobile`)

* **Dual-Mode Transport & Security:**
  * **Development:** Direct WebSocket connection (`ws://<ip>:9001`) with automatic `/24` subnet scanning.
  * **Release:** Native `BlinkySecureSocket` module with OkHttp TLS SHA-256 certificate public-key pinning and Android KeyStore AES-256 GCM credential encryption.
* **Sentinel Telemetry Dashboard:** Live monitoring of host CPU/RAM usage, battery status, uptime, active OS/compositor, and network MAC addresses.
* **Power Controls & Wake-on-LAN:** Remote triggers for hibernate, sleep, reboot, shutdown, and lock/unlock (with PIN/password support), plus 3-packet UDP magic packet bursts for sleeping hosts.
* **High-Speed File Streaming:** 16MB chunked bidirectional transfers on port `9002` with native streaming SHA-256 hashing.
* **Native LaTeX & Markdown:** Custom renderer converting complex LaTeX formulas into clean Unicode typography without webviews.
* **Gesture Screenshot Canvas:** Multi-touch canvas with focal-anchored double-tap (1x ↔ 2.5x), smooth pinch zoom (1x–5x), and bounded rubber-band panning.
* **Hardware Volume Rocker Hijack:** Intercepts physical phone volume buttons to adjust PC master volume over the socket.
* **Monetization & Entitlements:** RevenueCat paywall and promo code redemption engine (`lib/purchases.ts`).

---

## 10. Hardware & External Integrations

* **ESP32 Ambient Light Daemon (`BlinkyUniversalDaemon`):** Arduino C++ firmware for ESP32 microcontrollers controlling NeoPixel LEDs for system state signaling.
* **WhatsApp Bridge:** Headless WhatsApp Web bot for conversational commands from outside the local network.
