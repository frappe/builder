"""Unit tests for the ChatGPT sign-in helpers (builder/ai/codex_login.py).

Pure-function tests (no DB, no network): the PKCE pair, the authorize URL and
the account-id extraction. The listener and exchange need a browser and OpenAI.
"""

import unittest
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
