#!/usr/bin/env python3
"""
Laya Intent Router for Blinky.

Provides fast (~30ms) non-autoregressive System 1 intent classification and routing
using the Laya neural decision engine (NandhaKishorM/laya) combined with deterministic
structural safeguards.

Eliminates fragile regex collision bugs and removes cloud-roundtrip latency for
fast-path intent resolution across Browser-Use, AiCut, Excel, WhatsApp, Desktop Automation,
and Informational Chat.
"""

from __future__ import annotations

import logging
import re
from typing import Any

LOGGER = logging.getLogger("blinky.ai.laya_router")

_ROUTER_INSTANCE: Any = None
_ROUTER_FAILED: bool = False

INTENT_QUESTIONS = {
    "target_domain": {
        "type": "choice",
        "instructions": "What is the target medium or domain of this user request?",
        "criteria": {
            "web_url": "An online website, HTTP/HTTPS link, web domain, or online social platform (Instagram, YouTube, GitHub, TikTok, Twitter, Amazon, Reddit)",
            "local_media": "A local video or audio file on the user's computer drive (MP4, MKV, MP3, WAV) for offline FFmpeg editing",
            "spreadsheet": "Microsoft Excel spreadsheet, workbook, or tabular data cells",
            "chat_messaging": "WhatsApp messaging application or sending a message to a contact",
            "desktop_os": "Native Windows desktop application, clicking buttons, OS settings, keyboard/mouse automation",
            "general_qa": "General knowledge question, conversation, advice, greeting, or code explanation without computer action",
        },
    },
    "action_type": {
        "type": "choice",
        "instructions": "What primary action should the AI assistant perform?",
        "criteria": {
            "browser_navigation": "Browse or inspect an online website, navigate to a URL, extract web data, check comments on a website",
            "media_editing": "Edit, trim, cut, mix audio, or burn subtitles into a local media file using FFmpeg",
            "excel_operation": "Write numbers or text into Excel cells, format a spreadsheet, or run spreadsheet formulas",
            "send_message": "Send a message or chat with a contact on WhatsApp",
            "control_gui": "Click on a desktop window, type into a desktop application, automate Windows UI",
            "answer_chat": "Provide a conversational or informative text answer in chat without system action",
        },
    },
}

DOMAIN_TO_INTENT = {
    "web_url": "BROWSER_USE",
    "local_media": "VIDEO_EDIT",
    "spreadsheet": "SPREADSHEET",
    "chat_messaging": "WHATSAPP",
    "desktop_os": "DESKTOP_AUTOMATION",
    "general_qa": "CHAT",
}

ACTION_TO_INTENT = {
    "browser_navigation": "BROWSER_USE",
    "media_editing": "VIDEO_EDIT",
    "excel_operation": "SPREADSHEET",
    "send_message": "WHATSAPP",
    "control_gui": "DESKTOP_AUTOMATION",
    "answer_chat": "CHAT",
}

WEB_DOMAINS_RE = re.compile(
    r"\b(?:https?://|www\.|[a-zA-Z0-9-]+\.(?:com|org|net|io|ai|co|tv|app|dev)(?:/\S*)?)",
    re.IGNORECASE,
)


def get_laya_router() -> Any | None:
    """Retrieve or lazily initialize the singleton Laya Router."""
    global _ROUTER_INSTANCE, _ROUTER_FAILED
    if _ROUTER_FAILED:
        return None
    if _ROUTER_INSTANCE is not None:
        return _ROUTER_INSTANCE

    try:
        from laya import Router
        _ROUTER_INSTANCE = Router()
        LOGGER.info("Laya System 1 Router initialized successfully")
        return _ROUTER_INSTANCE
    except Exception as exc:
        LOGGER.warning("Could not initialize Laya Router (falling back to heuristic routing): %s", exc)
        _ROUTER_FAILED = True
        return None


def classify_with_laya(query: str) -> dict[str, Any] | None:
    """
    Classify user query into Blinky intents using Laya System 1 Router + structural safeguards.

    Returns dict with keys:
      - 'intent': 'BROWSER_USE' | 'VIDEO_EDIT' | 'SPREADSHEET' | 'WHATSAPP' | 'DESKTOP_AUTOMATION' | 'CHAT'
      - 'domain': str
      - 'action': str
      - 'confidence': float
      - 'source': 'laya_neural' | 'structural_guard'
    """
    if not query or not query.strip():
        return None

    q = query.strip()
    q_lower = q.lower()

    # ── Structural Safeguards (100% Deterministic Overrides) ──
    # 1. Any HTTP/HTTPS URL or web domain is ALWAYS BROWSER_USE
    if WEB_DOMAINS_RE.search(q) or re.search(r"\b(?:go\s+to|navigate\s+to|open\s+website|open\s+url)\b", q_lower):
        return {
            "intent": "BROWSER_USE",
            "domain": "web_url",
            "action": "browser_navigation",
            "confidence": 1.0,
            "source": "structural_guard",
        }

    # 2. Explicit Excel cell addressing (e.g. "cell A1", "in A1 and B2")
    if re.search(r"\b(?:cell\s+[a-z]\d+|in\s+[a-z]\d+\b|type\s+.+?\s+in\s+[a-z]\d+)", q_lower):
        return {
            "intent": "SPREADSHEET",
            "domain": "spreadsheet",
            "action": "excel_operation",
            "confidence": 1.0,
            "source": "structural_guard",
        }

    # 3. Explicit WhatsApp sending
    if re.search(r"\b(?:send|message)\s+.+?\s+(?:to\s+.+?\s+)?on\s+whatsapp\b", q_lower):
        return {
            "intent": "WHATSAPP",
            "domain": "chat_messaging",
            "action": "send_message",
            "confidence": 1.0,
            "source": "structural_guard",
        }

    # 4. Explicit local media editing with local file extensions (.mp4, .mkv, .mov, .mp3, .wav)
    # MUST NOT contain web URLs or web domains
    if not WEB_DOMAINS_RE.search(q):
        if re.search(r"\b[^\s\"']+\.(?:mp4|mov|mkv|avi|webm|mp3|wav)\b", q_lower) and any(
            w in q_lower for w in ["trim", "cut", "subtitle", "caption", "burn", "mix", "song", "audio", "silence", "merge", "concat"]
        ):
            return {
                "intent": "VIDEO_EDIT",
                "domain": "local_media",
                "action": "media_editing",
                "confidence": 1.0,
                "source": "structural_guard",
            }

    # 5. Fast Folder & File Explorer operations
    if not WEB_DOMAINS_RE.search(q):
        try:
            from computer_use.folder_launcher import is_folder_or_explorer_request
            if is_folder_or_explorer_request(q):
                return {
                    "intent": "OPEN_FOLDER",
                    "domain": "desktop_os",
                    "action": "open_folder",
                    "confidence": 1.0,
                    "source": "structural_guard",
                }
        except Exception as exc:
            LOGGER.debug("Folder launcher guard check failed: %s", exc)

    # 6. Windows-Use fast-path operations (Notepad tab creation, typing, compound UIA tasks)
    if not WEB_DOMAINS_RE.search(q):
        try:
            from computer_use.windows_use_engine import (
                is_microsoft_store_install_request,
                resolve_windows_use_request,
            )
            if is_microsoft_store_install_request(q):
                return {
                    "intent": "COMPUTER_USE",
                    "domain": "desktop_os",
                    "action": "control_gui",
                    "confidence": 1.0,
                    "source": "structural_guard",
                    "params": {"backend": "cua", "query": q},
                }
            wu_match = resolve_windows_use_request(q)
            if wu_match:
                return {
                    "intent": "WINDOWS_USE",
                    "domain": "desktop_os",
                    "action": "control_gui",
                    "confidence": 1.0,
                    "source": "structural_guard",
                    "params": wu_match,
                }
        except Exception as exc:
            LOGGER.debug("Windows-Use pre-check failed: %s", exc)

        # DESKTOP_AUTOMATION structural guard:
        # Fire only for compound "open APP and type TEXT" patterns that DO NOT contain notepad
        # (notepad is always handled by Windows-Use engine above).
        _has_notepad = "notepad" in q_lower
        if not _has_notepad:
            if re.search(r"\b(?:open|launch|start)\s+(?:the\s+)?[a-zA-Z0-9 ._-]+\s+(?:and|then)\s+(?:type|write|enter|input)\b", q_lower) or \
               re.search(r"\b(?:type|write|enter|input)\s+.+?\s+(?:in|into|to)\s+(?:the\s+)?[a-zA-Z0-9 ._-]+\b", q_lower):
                return {
                    "intent": "DESKTOP_AUTOMATION",
                    "domain": "desktop_os",
                    "action": "control_gui",
                    "confidence": 1.0,
                    "source": "structural_guard",
                }

        # 6. Direct app launch fast-path (e.g. "open notepad", "open notepad only", "launch chrome")
        app_open_match = re.match(
            r"^\s*(?:please\s+)?(?:open|launch|start)\s+(?:the\s+)?(?P<app>[a-zA-Z0-9 .+_-]{2,40}?)\s*(?:app|application|only|just|window|please)*\s*$",
            q,
            re.IGNORECASE,
        )
        if app_open_match:
            candidate = re.sub(r"\b(app|application|only|just|window|please)$", "", app_open_match.group("app"), flags=re.IGNORECASE).strip()
            if candidate and not any(w in candidate.lower() for w in [" and ", " then ", " type ", " write ", " search ", " find "]):
                from computer_use.agent import is_web_destination, is_in_app_action
                if is_web_destination(candidate) or is_in_app_action(candidate):
                    return {
                        "intent": "DESKTOP_AUTOMATION",
                        "domain": "desktop_os",
                        "action": "control_gui",
                        "confidence": 1.0,
                        "source": "structural_guard",
                    }
                # Notepad open goes to WINDOWS_USE so UIA can handle it properly
                if "notepad" in candidate.lower():
                    return {
                        "intent": "WINDOWS_USE",
                        "domain": "desktop_os",
                        "action": "control_gui",
                        "confidence": 1.0,
                        "source": "structural_guard",
                        "params": {"action": "notepad_open", "app": "notepad", "text": "", "raw_query": q},
                    }
                return {
                    "intent": "OPEN_APP",
                    "domain": "desktop_os",
                    "action": "open_app",
                    "confidence": 1.0,
                    "source": "structural_guard",
                    "params": {"app_name": candidate},
                }

    # ── Laya System 1 Neural Forward Pass ──
    router = get_laya_router()
    if router is None:
        return None

    try:
        res = router.predict(q, INTENT_QUESTIONS)
        answers = res.get("answers", {})

        domain_ans = answers.get("target_domain", {})
        action_ans = answers.get("action_type", {})

        domain_choice = domain_ans.get("choice", "general_qa")
        action_choice = action_ans.get("choice", "answer_chat")

        domain_probs = domain_ans.get("probabilities", {})
        action_probs = action_ans.get("probabilities", {})

        domain_conf = domain_probs.get(domain_choice, 0.5)
        action_conf = action_probs.get(action_choice, 0.5)
        avg_confidence = round((domain_conf + action_conf) / 2.0, 3)

        # Cross-validation & intent synthesis
        has_web_url = bool(WEB_DOMAINS_RE.search(q))

        if has_web_url:
            resolved_intent = "BROWSER_USE"
        elif domain_choice == "desktop_os" or action_choice == "control_gui":
            try:
                from computer_use.windows_use_engine import resolve_windows_use_request
                wu_check = resolve_windows_use_request(q)
                if wu_check:
                    resolved_intent = "WINDOWS_USE"
                else:
                    resolved_intent = "DESKTOP_AUTOMATION"
            except Exception:
                resolved_intent = "DESKTOP_AUTOMATION"
        elif domain_choice == "general_qa":
            # Conversational Q&A unless user explicitly asked to browse/search the web
            if action_choice == "browser_navigation" and any(k in q_lower for k in ["browse", "search online", "google", "web"]):
                resolved_intent = "BROWSER_USE"
            else:
                resolved_intent = "CHAT"
        elif domain_choice == "web_url" or action_choice == "browser_navigation":
            resolved_intent = "BROWSER_USE"
        elif domain_choice == "local_media" or action_choice == "media_editing":
            resolved_intent = "VIDEO_EDIT"
        elif domain_choice == "spreadsheet" or action_choice == "excel_operation":
            resolved_intent = "SPREADSHEET"
        elif domain_choice == "chat_messaging" or action_choice == "send_message":
            resolved_intent = "WHATSAPP"
        else:
            resolved_intent = "CHAT"

        return {
            "intent": resolved_intent,
            "domain": domain_choice,
            "action": action_choice,
            "confidence": avg_confidence,
            "domain_confidence": domain_conf,
            "action_confidence": action_conf,
            "source": "laya_neural",
            "raw": res,
        }
    except Exception as exc:
        LOGGER.debug("Laya neural forward pass failed: %s", exc)
        return None


def get_preflight_from_laya(query: str, previous_question: str | None = None) -> dict[str, Any] | None:
    """
    Produce a Blinky-compatible preflight dictionary from Laya classification.
    Returns None if Laya router is unavailable or confidence is insufficient.
    """
    classification = classify_with_laya(query)
    if not classification:
        return None

    intent = classification["intent"]
    confidence = classification.get("confidence", 0.0)
    source = classification.get("source", "laya")

    extracted_params: dict[str, Any] = {}

    if intent == "BROWSER_USE":
        try:
            from tools.browser_use_tool import resolve_browser_use_request
            bu_match = resolve_browser_use_request(query)
            extracted_params = bu_match or {"task": query}
        except Exception:
            extracted_params = {"task": query}
        needs_screen = False

    elif intent == "SPREADSHEET":
        try:
            from tools.spreadsheet_tool import resolve_spreadsheet_request
            sheet_match = resolve_spreadsheet_request(query)
            extracted_params = sheet_match or {"action": "open", "raw_prompt": query}
        except Exception:
            extracted_params = {"action": "open", "raw_prompt": query}
        needs_screen = False

    elif intent == "WHATSAPP":
        try:
            from tools.whatsapp_tool import resolve_whatsapp_request, resolve_whatsapp_send_request
            send_match = resolve_whatsapp_send_request(query)
            if send_match:
                extracted_params = {"wa_action": "send", "wa_chat_name": send_match[0], "wa_message": send_match[1]}
            else:
                wa_match = resolve_whatsapp_request(query)
                if wa_match:
                    extracted_params = {"wa_action": wa_match[0], "wa_chat_name": wa_match[1]}
                else:
                    extracted_params = {"wa_action": "status"}
        except Exception:
            extracted_params = {"wa_action": "status"}
        needs_screen = False

    elif intent == "VIDEO_EDIT":
        try:
            from tools.aicut_tool import resolve_aicut_request
            aicut_match = resolve_aicut_request(query)
            extracted_params = aicut_match or {"action": "video edit", "prompt": query}
        except Exception:
            extracted_params = {"action": "video edit", "prompt": query}
        needs_screen = False

    elif intent == "OPEN_APP":
        app_params = classification.get("params") or {}
        extracted_params = app_params if app_params.get("app_name") else {"app_name": query}
        needs_screen = False

    elif intent == "WINDOWS_USE":
        extracted_params = classification.get("params") or {}
        if not extracted_params:
            try:
                from computer_use.windows_use_engine import resolve_windows_use_request
                extracted_params = resolve_windows_use_request(query) or {"query": query}
            except Exception:
                extracted_params = {"query": query}
        needs_screen = False

    elif intent == "DESKTOP_AUTOMATION":
        try:
            from computer_use.windows_use_engine import resolve_windows_use_request
            wu_match = resolve_windows_use_request(query)
            if wu_match:
                intent = "WINDOWS_USE"
                needs_screen = False
                extracted_params = wu_match
            else:
                needs_screen = True
                extracted_params = {"backend": "cua", "query": query}
        except Exception:
            needs_screen = True
            extracted_params = {"backend": "cua", "query": query}

    elif intent == "COMPUTER_USE":
        needs_screen = True
        extracted_params = classification.get("params") or {"backend": "cua", "query": query}

    elif intent == "CHAT":
        intent = "INFORMATIONAL_CHAT"
        needs_screen = False
        extracted_params = {}

    else:
        return None

    return {
        "intent": intent,
        "needs_screen": needs_screen,
        "is_continuation": False,
        "extracted_params": extracted_params,
        "confidence": confidence,
        "source": source,
        "laya_classification": classification,
    }
