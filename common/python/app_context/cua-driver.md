# CUA Agent Cursor Overlay

## App Overview
- **Process**: `cua-driver.exe`
- **Window Title**: `cua.agentcursoroverlay.default`
- **Purpose**: This is a system-level overlay component for Computer Use Agents (CUA). It is not a standard user-facing application but a background service that renders visual indicators (cursors, highlights, or bounding boxes) to show agent actions on the desktop.

## Standard Behaviors
- **Non-Interactive**: The overlay window is typically transparent and click-through. It does not accept direct user input (keyboard/mouse) unless specifically configured for debugging.
- **Visual Feedback**: Displays live cursors, action highlights, or status indicators corresponding to automated agent operations.
- **Background Process**: Runs as a driver/service; no standard taskbar icon or start menu entry is expected.

## Navigation & Access
- **No Standard Menus**: As an overlay, it lacks traditional File/Edit/View menus.
- **Settings/Configuration**: 
  - Configuration is usually managed via the parent agent application (e.g., Cursor, VS Code extension, or Codex CLI) or via command-line arguments to `cua-driver.exe`.
  - Check the parent application's settings for "Agent Visibility" or "Overlay Options."
- **Help/Support**: 
  - Refer to the documentation of the parent agent tool (e.g., K-Dense-AI/scientific-agents or OSWorld-Science benchmarks).
  - No in-app Help menu exists.

## Troubleshooting
- **If overlay is stuck**: Restart the parent agent application or terminate `cua-driver.exe` via Task Manager.
- **If invisible**: Ensure the parent agent is active and has permission to draw on the desktop.