import importlib
import os
import unittest


class ExtensionSmokeTests(unittest.TestCase):
    def test_extract_auth_magic_link(self):
        from browser_agent.otp_relay import _extract_auth

        body = "Click here: https://stytch.com/v1/magic_links/redirect?token=abc123"
        result = _extract_auth(body)
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "magic_link")

    def test_extract_auth_otp(self):
        from browser_agent.otp_relay import _extract_auth

        body = "Your verification code: 123456"
        result = _extract_auth(body)
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "otp")
        self.assertEqual(result["value"], "123456")

    def test_github_trending_url_is_dynamic_and_encoded(self):
        from scanner.scan_agent import _github_trending_search_url

        url = _github_trending_search_url(30)
        self.assertIn("q=stars%3A%3E100+pushed%3A%3E", url)
        self.assertIn("sort=stars", url)

    def test_credential_vault_repo_override(self):
        os.environ["GITHUB_REPO_OWNER"] = "ExampleOwner"
        os.environ["GITHUB_REPO_NAME"] = "example-repo"
        module = importlib.import_module("browser_agent.credential_vault")
        module = importlib.reload(module)
        self.assertEqual(module.REPO_OWNER, "ExampleOwner")
        self.assertEqual(module.REPO_NAME, "example-repo")


if __name__ == "__main__":
    unittest.main()
