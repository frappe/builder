"""Unit tests for the ChatGPT sign-in (builder/ai/codex_login.py).

No network: the PKCE pair, the authorize URL, the account-id extraction, and the
device-code round trip against a stubbed auth.openai.com.
"""

import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

from builder.ai import codex, codex_login
from builder.ai.test_codex import fake_jwt


def answer(status: int, body: dict) -> MagicMock:
	response = MagicMock(status_code=status, ok=status < 400)
	response.json.return_value = body
	return response


class TestPkce(unittest.TestCase):
	def test_challenge_matches_rfc_7636_vector(self):
		verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
		self.assertEqual(codex_login.pkce_challenge(verifier), "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM")


class TestAuthorizeUrl(unittest.TestCase):
	def test_carries_the_pkce_and_state(self):
		url = codex_login.authorize_url("challenge-x", "state-y")
		parsed = urlparse(url)
		query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
		self.assertEqual(f"{parsed.scheme}://{parsed.netloc}{parsed.path}", codex_login.AUTHORIZE_URL)
		self.assertEqual(query["code_challenge"], "challenge-x")
		self.assertEqual(query["code_challenge_method"], "S256")
		self.assertEqual(query["state"], "state-y")
		self.assertEqual(query["redirect_uri"], codex_login.REDIRECT_URI)
		self.assertEqual(query["client_id"], codex.CLIENT_ID)


class TestAccountId(unittest.TestCase):
	def test_prefers_id_token_nested_claim(self):
		id_token = fake_jwt({"https://api.openai.com/auth": {"chatgpt_account_id": "acct_id_token"}})
		access = fake_jwt({"https://api.openai.com/auth": {"chatgpt_account_id": "acct_access"}})
		self.assertEqual(codex.account_id_from_tokens(id_token, access), "acct_id_token")

	def test_falls_back_to_access_token_then_org(self):
		access = fake_jwt({"organizations": [{"id": "org_1"}]})
		self.assertEqual(codex.account_id_from_tokens(None, access), "org_1")
		self.assertEqual(codex.account_id_from_tokens("not-a-jwt", None), "")


class TestDeviceSignIn(unittest.TestCase):
	def start(self) -> dict:
		code = answer(200, {"device_auth_id": "dev_1", "user_code": "ABCD-1234", "interval": "5"})
		with patch("builder.ai.codex_login.requests.post", return_value=code):
			return codex_login.start()

	def test_start_hands_out_a_code_for_the_device_page(self):
		login = self.start()
		self.assertEqual(
			(login["code"], login["url"], login["interval"]), ("ABCD-1234", codex_login.DEVICE_PAGE, 5)
		)
		codex_login.clear_login(login["state"])

	def test_poll_waits_until_the_user_approves(self):
		login = self.start()
		with patch("builder.ai.codex_login.requests.post", return_value=answer(403, {})):
			self.assertEqual(codex_login.poll(login["state"]), {"status": "pending"})
		codex_login.clear_login(login["state"])

	def test_an_approval_is_exchanged_with_the_device_redirect(self):
		login = self.start()
		approved = answer(200, {"authorization_code": "code_1", "code_verifier": "verifier_1"})
		with (
			patch("builder.ai.codex_login.requests.post", return_value=approved),
			patch("builder.ai.codex_login.exchange_code", return_value={"access": "a"}) as exchange,
			patch(
				"builder.ai.codex_login.install_provider", return_value={"provider": "ChatGPT", "models": []}
			),
		):
			result = codex_login.poll(login["state"])
		exchange.assert_called_once_with("code_1", "verifier_1", codex_login.DEVICE_REDIRECT_URI)
		self.assertEqual(result["status"], "connected")
		self.assertIsNone(codex_login.load_login(login["state"]))

	def test_an_unknown_state_has_expired(self):
		self.assertEqual(codex_login.poll("no-such-state"), {"status": "expired"})
