import unittest
import time
import json
import hmac
import hashlib
from requests_handler import BitvavoAPI
from config import APIConfig

# Dummy response to simulate a successful HTTP request.
class DummyResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code != 200:
            raise Exception("Bad status code")

    def json(self):
        return self._json

# Fake session to simulate requests.
class FakeSession:
    def __init__(self, response):
        self.response = response

    def request(self, method, url, headers, json, timeout):
        return self.response

class TestRequestsHandler(unittest.TestCase):
    def setUp(self):
        self.api_config = APIConfig(
            api_key="test_key",
            api_secret="secret",
            base_url="https://api.test.com/v2",
            rate_limit=300,
            timeout=30
        )
        self.api = BitvavoAPI(self.api_config)

    def test_generate_signature(self):
        method = "GET"
        endpoint = "/test"
        body = {"foo": "bar"}
        timestamp = "1234567890"

        # Compute the expected signature.
        full_endpoint = f'/v2{endpoint}' if not endpoint.startswith('/v2') else endpoint
        message = f"{timestamp}{method.upper()}{full_endpoint}" + json.dumps(body, separators=(',', ':'))
        expected_signature = hmac.new(
            self.api_config.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        signature = self.api._generate_signature(method, endpoint, body, timestamp)
        self.assertEqual(signature, expected_signature)

    def test_send_request_success(self):
        expected_json = {"result": "success"}
        fake_response = DummyResponse(expected_json)
        self.api.session = FakeSession(fake_response)

        result = self.api.send_request("GET", "/dummy")
        self.assertEqual(result, expected_json)

    def test_send_request_failure(self):
        # Simulate a failure by using a session that raises an exception.
        class FailingSession:
            def request(self, method, url, headers, json, timeout):
                raise Exception("Simulated failure")

        self.api.session = FailingSession()
        result = self.api.send_request("GET", "/dummy")
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
