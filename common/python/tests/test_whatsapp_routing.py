import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
from tools.whatsapp_tool import resolve_whatsapp_request, resolve_whatsapp_send_request, run_send
from main import classify_request, run_whatsapp_tool
import agent_router

class TestWhatsAppRouting(unittest.IsolatedAsyncioTestCase):
    def test_resolve_whatsapp_send_request_requires_explicit_recipient_and_text(self):
        cases = [
            (
                "send a WhatsApp message to Sahil Gupta saying hello from Blinky",
                ("Sahil Gupta", "hello from Blinky"),
            ),
            (
                "send WhatsApp message to Sahil Gupta: test message",
                ("Sahil Gupta", "test message"),
            ),
            (
                "send 'hello again' to Sahil Gupta on WhatsApp",
                ("Sahil Gupta", "hello again"),
            ),
            ("send a message to Sahil Gupta", None),
        ]
        for query, expected in cases:
            with self.subTest(query=query):
                self.assertEqual(resolve_whatsapp_send_request(query), expected)

    def test_resolve_whatsapp_request_phrasings(self):
        cases = [
            ("summarize hackathon crew in whatsapp", ("summarize", "hackathon crew")),
            ("summarize hackathon crew on whatsapp", ("summarize", "hackathon crew")),
            ("summarize the hackathon crew group in whatsapp", ("summarize", "hackathon crew")),
            ("whatsapp summarize hackathon crew", ("summarize", "hackathon crew")),
            ("summarize whatsapp group hackathon crew", ("summarize", "hackathon crew")),
            ("give me a summary of hackathon crew in whatsapp", ("summarize", "hackathon crew")),
            ("recap hackathon crew on whatsapp", ("summarize", "hackathon crew")),
            ("check whatsapp status", ("status", None)),
            ("whatsapp status", ("status", None)),
            ("list whatsapp chats", ("chats", None)),
            ("show my whatsapp chats", ("chats", None)),
            ("open whatsapp", None),
            ("play music on spotify", None),
            ("search python tutorials", None),
        ]
        for query, expected in cases:
            with self.subTest(query=query):
                self.assertEqual(resolve_whatsapp_request(query), expected)

    def test_classify_request_whatsapp_fastpath_no_vision(self):
        warnings = []
        with patch("ai.client.ask_groq_vision", side_effect=AssertionError("Groq vision model must not be called")) as mock_vision:
            result = classify_request("summarize hackathon crew in whatsapp", None, warnings, None, agent_mode=True)
            self.assertIsNotNone(result)
            self.assertEqual(result["intent"], "WHATSAPP")
            self.assertFalse(result["needs_screen"])
            self.assertEqual(result["extracted_params"]["wa_action"], "summarize")
            self.assertEqual(result["extracted_params"]["wa_chat_name"], "hackathon crew")
            mock_vision.assert_not_called()

    def test_classify_request_whatsapp_send_extracts_message_without_vision(self):
        warnings = []
        with patch("ai.client.ask_groq_vision", side_effect=AssertionError("Groq vision model must not be called")) as mock_vision:
            result = classify_request(
                "send a WhatsApp message to Sahil Gupta saying hello from Blinky",
                None,
                warnings,
                None,
                agent_mode=True,
            )

        self.assertEqual(result["intent"], "WHATSAPP")
        self.assertEqual(result["extracted_params"]["wa_action"], "send")
        self.assertEqual(result["extracted_params"]["wa_chat_name"], "Sahil Gupta")
        self.assertEqual(result["extracted_params"]["wa_message"], "hello from Blinky")
        mock_vision.assert_not_called()

    async def test_agent_router_handles_whatsapp_summarize_without_vision(self):
        mock_summary = "*📌 Key Updates*\n- Team finalized hackathon project architecture\n- Demo scheduled for 4 PM"
        with (
            patch("main.run_whatsapp_tool", return_value={"summary": mock_summary, "steps": []}) as mock_wa,
            patch("agent_router.send_response") as mock_send,
            patch("ai.client.ask_groq_vision", side_effect=AssertionError("Vision model should NEVER be called")) as mock_vision,
        ):
            line = '{"requestId":"req-123","query":"summarize hackathon crew in whatsapp"}'
            await agent_router.handle_request(line)

            mock_wa.assert_called_once()
            args, _ = mock_wa.call_args
            self.assertEqual(args[0], "summarize")
            self.assertEqual(args[1], "hackathon crew")
            mock_send.assert_any_call("req-123", "success", data={"response": mock_summary})
            mock_vision.assert_not_called()

    async def test_agent_router_handles_whatsapp_status(self):
        with (
            patch("main.run_whatsapp_tool", return_value={"summary": "WhatsApp is connected and ready.", "steps": []}) as mock_wa,
            patch("agent_router.send_response") as mock_send,
        ):
            line = '{"requestId":"req-456","query":"check whatsapp status"}'
            await agent_router.handle_request(line)

            mock_wa.assert_called_once()
            args, _ = mock_wa.call_args
            self.assertEqual(args[0], "status")
            self.assertIsNone(args[1])
            mock_send.assert_any_call("req-456", "success", data={"response": "WhatsApp is connected and ready."})

    def test_run_send_resolves_exact_chat_and_posts_message(self):
        response = MagicMock(status_code=200, text="")
        response.headers = {"content-type": "application/json"}
        response.json.return_value = {"ok": True, "messageId": "msg-1"}
        with (
            patch("tools.whatsapp_tool.run_chats", return_value={"chats": [
                {"id": "447700900123@c.us", "name": "Sahil Gupta"},
                {"id": "120363-group@g.us", "name": "Sahil Gupta Community"},
            ]}),
            patch("tools.whatsapp_tool.requests.post", return_value=response) as post,
        ):
            result = run_send("http://localhost:3000", "Sahil Gupta", "hello from tests")

        self.assertTrue(result["sent"])
        self.assertEqual(result["chat_name"], "Sahil Gupta")
        post.assert_called_once()
        self.assertIn("447700900123%40c.us", post.call_args.args[0])
        self.assertEqual(post.call_args.kwargs["json"], {"message": "hello from tests"})

    def test_run_send_resolves_profile_name_to_whatsapp_self_chat(self):
        response = MagicMock(status_code=200, text="")
        response.headers = {"content-type": "application/json"}
        response.json.return_value = {"ok": True, "messageId": "msg-self"}
        with (
            patch("tools.whatsapp_tool.run_chats", return_value={"chats": [
                {"id": "0@c.us", "name": "WhatsApp"},
            ]}),
            patch("tools.whatsapp_tool.run_status", return_value={"status": "connected", "me": {"name": "Sahil Gupta"}}),
            patch("tools.whatsapp_tool.requests.post", return_value=response) as post,
        ):
            result = run_send("http://localhost:3000", "Sahil Gupta", "hello myself")

        self.assertTrue(result["sent"])
        self.assertEqual(result["chat_id"], "0@c.us")
        self.assertEqual(result["chat_name"], "Sahil Gupta")
        self.assertIn("0%40c.us", post.call_args.args[0])
