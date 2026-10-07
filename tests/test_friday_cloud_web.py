import unittest
from unittest.mock import patch
from urllib.error import URLError

from fastapi.testclient import TestClient
from carapace_integrations.friday_cloud_web import WebSettings, backend_request, create_cloud_web, verify_iap


class CloudWebTests(unittest.TestCase):
    def setUp(self):
        self.settings = WebSettings("https://private-api.run.app", "https://friday-web.run.app",
                                    "/projects/123/locations/asia-south1/services/friday-web",
                                    {"one@example.com": "one", "two@example.com": "two"},
                                    {"one": "secret-one", "two": "secret-two"})
        self.calls = []

        def verify(token, audience):
            self.assertEqual(audience, self.settings.iap_audience)
            if token == "invalid":
                raise ValueError("bad signature")
            return {"email": token}

        def transport(settings, tenant, path, method, body, mime):
            self.calls.append((tenant, path, method, body, mime))
            return 200, {"ok": True}

        self.app = create_cloud_web(self.settings, verifier=verify, transport=transport,
                                   html="<h1>Friday</h1>")
        self.client = TestClient(self.app)
        self.headers = {"X-Goog-Iap-Jwt-Assertion": "one@example.com",
                        "Origin": self.settings.public_origin}

    def test_missing_and_invalid_identity_rejected(self):
        self.assertEqual(self.client.get("/").status_code, 401)
        self.assertEqual(self.client.get("/", headers={"X-Goog-Iap-Jwt-Assertion": "invalid"}).status_code, 401)
        self.assertEqual(self.calls, [])

    def test_unenrolled_identity_rejected(self):
        self.assertEqual(self.client.get("/", headers={"X-Goog-Iap-Jwt-Assertion": "other@example.com"}).status_code, 403)

    def test_public_health_contains_no_credentials(self):
        result = self.client.get("/health")
        self.assertEqual(result.status_code, 200)
        self.assertNotIn("secret", result.text)

    def test_verified_identity_selects_tenant_not_browser_header(self):
        headers = dict(self.headers, **{"X-Carapace-Tenant": "two", "X-Carapace-API-Key": "attacker"})
        self.assertEqual(self.client.get("/api/friday/mandate", headers=headers).status_code, 200)
        self.assertEqual(self.calls[0][0], "one")
        headers["X-Goog-Iap-Jwt-Assertion"] = "two@example.com"
        self.client.get("/api/friday/mandate", headers=headers)
        self.assertEqual(self.calls[-1][0], "two")

    def test_post_requires_same_origin(self):
        for source in (None, "https://evil.example", "null"):
            headers = dict(self.headers)
            if source is None:
                del headers["Origin"]
            else:
                headers["Origin"] = source
            self.assertEqual(self.client.post("/api/friday/live-input", headers=headers, json={}).status_code, 403)
        self.assertEqual(self.calls, [])

    def test_permitted_json_forwarded_once(self):
        response = self.client.post("/api/friday/live-input", headers=self.headers, json={"content_text": "new bill"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][1:3], ("/v1/friday/live-input", "POST"))
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_unrestricted_proxy_and_legacy_routes_absent(self):
        for path in ("/api/friday/../admin", "/api/friday/watch", "/api/friday/inbox",
                     "/api/friday/https://evil.example", "/operations", "/docs"):
            self.assertEqual(self.client.get(path, headers=self.headers).status_code, 404)
        self.assertEqual(self.client.delete("/api/friday/mandate", headers=self.headers).status_code, 404)

    def test_query_injection_rejected(self):
        self.assertEqual(self.client.get("/api/friday/mandate?tenant=two", headers=self.headers).status_code, 400)
        self.assertEqual(self.client.post("/api/friday/documents?filename=../secret", headers=self.headers,
                                         content=b"pdf").status_code, 400)

    def test_document_query_encoded_and_mime_validated(self):
        headers = dict(self.headers, **{"Content-Type": "application/pdf"})
        response = self.client.post("/api/friday/documents?filename=bill%20one.pdf", headers=headers, content=b"pdf")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.calls[-1][1], "/v1/friday/documents?filename=bill+one.pdf")
        self.assertEqual(self.client.post("/api/friday/live-input", headers=headers, content=b"pdf").status_code, 415)

    def test_oversized_upload_rejected_before_upstream(self):
        headers = dict(self.headers, **{"Content-Type": "application/pdf"})
        response = self.client.post("/api/friday/documents?filename=x.pdf", headers=headers, content=b"x" * (8 * 1024 * 1024 + 1))
        self.assertEqual(response.status_code, 413)
        self.assertEqual(self.calls, [])

    def test_settings_fail_closed(self):
        for backend in ("http://private-api.run.app", "https://evil.example", "https://user@private-api.run.app", "https://private-api.run.app?x=y"):
            with self.assertRaises(ValueError):
                WebSettings(backend, self.settings.public_origin, self.settings.iap_audience,
                            self.settings.users, self.settings.tenant_keys)
        with self.assertRaises(ValueError):
            WebSettings(self.settings.backend_url, self.settings.public_origin, self.settings.iap_audience,
                        {"one@example.com": "one", "two@example.com": "one"}, self.settings.tenant_keys)

    def test_auth_errors_are_not_cacheable(self):
        for headers in ({}, {"X-Goog-Iap-Jwt-Assertion": "invalid"},
                        {"X-Goog-Iap-Jwt-Assertion": "other@example.com"}):
            response = self.client.get("/", headers=headers)
            self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertEqual(response.headers["x-content-type-options"], "nosniff")

    def test_iap_verifier_passes_exact_audience_and_rejects_wrong_issuer(self):
        with patch("google.oauth2.id_token.verify_token") as verify:
            verify.return_value = {"iss": "https://cloud.google.com/iap", "sub": "subject"}
            verify_iap("signed-token", self.settings.iap_audience)
            self.assertEqual(verify.call_args.kwargs["audience"], self.settings.iap_audience)
            self.assertEqual(verify.call_args.kwargs["certs_url"], "https://www.gstatic.com/iap/verify/public_key")
            for claims in ({"iss": "https://attacker.example", "sub": "subject"},
                           {"iss": "https://cloud.google.com/iap"}):
                verify.return_value = claims
                with self.assertRaises(ValueError):
                    verify_iap("signed-token", self.settings.iap_audience)
            verify.side_effect = ValueError("expired or wrong audience")
            with self.assertRaises(ValueError):
                verify_iap("signed-token", self.settings.iap_audience)

    def test_missing_backend_identity_never_sends_request(self):
        from google.auth.exceptions import DefaultCredentialsError
        with patch("google.oauth2.id_token.fetch_id_token", side_effect=DefaultCredentialsError("private details")), \
             patch("carapace_integrations.friday_cloud_web.urlopen") as upstream:
            status, body = backend_request(self.settings, "one", "/v1/friday/live-input", "POST", b"{}", "application/json")
            self.assertEqual(status, 503)
            self.assertNotIn("private details", str(body))
            upstream.assert_not_called()

    def test_unknown_post_outcome_never_retries(self):
        with patch("google.oauth2.id_token.fetch_id_token", return_value="private-token"), \
             patch("carapace_integrations.friday_cloud_web.urlopen", side_effect=URLError("timeout")) as upstream:
            status, body = backend_request(self.settings, "one", "/v1/friday/live-input", "POST", b"{}", "application/json")
            self.assertEqual(status, 502)
            self.assertIn("unknown", body["detail"])
            self.assertEqual(upstream.call_count, 1)
            self.assertNotIn("private-token", str(body))

    def test_cloud_home_removes_local_worker_controls_and_handlers(self):
        app = create_cloud_web(self.settings, verifier=lambda *_: {"email": "one@example.com"})
        response = TestClient(app).get("/", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('class="card watch-card"', response.text)
        self.assertNotIn("let watching=false", response.text)
        self.assertNotIn("setInterval(refreshInbox", response.text)
        self.assertIn("Continuous cloud monitoring is not enabled yet", response.text)


if __name__ == "__main__":
    unittest.main()
