import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from twilio.request_validator import RequestValidator

import routes.twilio as twilio_route
import services.supabase as supabase_service
from config import TWILIO_AUTH_TOKEN
from main import app


class TwilioWebhookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not TWILIO_AUTH_TOKEN:
            raise unittest.SkipTest("TWILIO_AUTH_TOKEN is not configured")
        cls.client = TestClient(app)
        cls.validator = RequestValidator(TWILIO_AUTH_TOKEN)

    def signed_headers(self, path, data):
        signature = self.validator.compute_signature(
            f"http://testserver{path}", data
        )
        return {"X-Twilio-Signature": signature}

    def test_unauthenticated_request_returns_403(self):
        with patch.object(twilio_route, "get_ai_reply") as ai_reply:
            response = self.client.post(
                "/twilio/webhook",
                data={"From": "+15551234567", "Body": "Hello"},
            )

        self.assertEqual(response.status_code, 403)
        ai_reply.assert_not_called()

    def test_valid_request_returns_twiML_with_mocked_dependencies(self):
        data = {"From": "+15551234567", "Body": "How much for an SUV?"}
        logged = Mock()

        with (
            patch.object(
                twilio_route, "get_ai_reply", return_value="Booking reply"
            ) as ai_reply,
            patch.object(twilio_route, "log_interaction", logged),
        ):
            response = self.client.post(
                "/sms",
                data=data,
                headers=self.signed_headers("/sms", data),
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("application/xml"))
        self.assertIn("<Message>Booking reply</Message>", response.text)
        ai_reply.assert_called_once_with(
            user_id="+15551234567",
            message="How much for an SUV?",
        )
        self.assertEqual(
            logged.call_args_list,
            [
                unittest.mock.call(
                    "+15551234567", "inbound_message", "How much for an SUV?"
                ),
                unittest.mock.call("+15551234567", "ai_reply", "Booking reply"),
            ],
        )

    def test_database_failure_uses_application_log_fallback(self):
        original_client = supabase_service.supabase
        supabase_service.supabase = None
        try:
            with self.assertLogs("services.supabase", level="WARNING") as logs:
                persisted = supabase_service.log_interaction(
                    "+15551234567", "inbound_call", "Missed call"
                )
        finally:
            supabase_service.supabase = original_client

        self.assertFalse(persisted)
        self.assertIn("Supabase unavailable", logs.output[0])


if __name__ == "__main__":
    unittest.main()