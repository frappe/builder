"""Unit tests for the ChatGPT sign-in helpers (builder/ai/codex_login.py).

No DB, no network: the PKCE pair, the authorize URL, the account-id extraction,
and the device poll's steps with the cache and OpenAI stubbed.
"""

import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

from builder.ai import codex, codex_login
from builder.ai.test_codex import fake_jwt


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


class TestDevicePoll(unittest.TestCase):
	"""The cache and OpenAI are stubbed: poll() is only the order of its steps."""

	def setUp(self):
		self.logins = {"s1": {"device_auth_id": "dev-1", "user_code": "ABCD-1234"}}
		self.approval = {"authorization_code": "auth-1", "code_verifier": "verifier-1"}
		stubs = {
			"load_login": lambda state: self.logins.get(state),
			"save_login": lambda state, data: self.logins.__setitem__(state, data),
			"clear_login": lambda state: self.logins.pop(state, None),
			"check_device": Mock(return_value=None),
			"exchange_code": Mock(return_value={"access": "token-1"}),
			"install_provider": Mock(return_value={"provider": "ChatGPT", "models": []}),
		}
		for name, stub in stubs.items():
			patcher = patch.object(codex_login, name, stub)
			patcher.start()
			self.addCleanup(patcher.stop)
		self.stubs = stubs

	def test_waits_until_approved(self):
		self.assertEqual(codex_login.poll("s1"), {"status": "pending"})
		self.stubs["exchange_code"].assert_not_called()

	def test_reports_the_approval_before_exchanging_it(self):
		self.stubs["check_device"].return_value = self.approval
		self.assertEqual(codex_login.poll("s1"), {"status": "approved"})
		self.stubs["exchange_code"].assert_not_called()

		result = codex_login.poll("s1")
		self.assertEqual(result, {"status": "connected", "provider": "ChatGPT", "models": []})
		self.stubs["exchange_code"].assert_called_once_with(
			"auth-1", "verifier-1", codex_login.DEVICE_REDIRECT_URI
		)
		self.stubs["install_provider"].assert_called_once_with({"access": "token-1"})
		self.assertNotIn("s1", self.logins)
		self.assertEqual(self.stubs["check_device"].call_count, 1)

	def test_unknown_state_has_expired(self):
		self.assertEqual(codex_login.poll("gone"), {"status": "expired"})
