"""Signing in to ChatGPT, for the ChatGPT (Codex) provider.

The main way is a device code: Bob shows a short code, the user enters it on
ChatGPT's device page and approves, and the server polls OpenAI until the
approval lands. Nothing redirects back to the site, so it works the same on a
laptop bench and on a hosted site.

The browser link is the fallback, for a ChatGPT workspace with device codes
switched off. The Codex OAuth client only ever redirects to localhost:1455,
which a hosted site can't hear, so the user pastes the address the browser
ended up on and finish() completes the exchange. Either way the tokens never
pass through the browser session: the exchange happens server-side.
"""

import base64
import hashlib
import json
import secrets
import time
from urllib.parse import parse_qs, urlencode, urlparse

import frappe
import requests

from builder.ai.codex import CLIENT_ID, ORIGINATOR, TOKEN_URL, CodexError, account_id_from_tokens

AUTH_BASE = "https://auth.openai.com"
DEVICE_CODE_URL = f"{AUTH_BASE}/api/accounts/deviceauth/usercode"
DEVICE_TOKEN_URL = f"{AUTH_BASE}/api/accounts/deviceauth/token"
DEVICE_PAGE = f"{AUTH_BASE}/codex/device"
DEVICE_REDIRECT_URI = f"{AUTH_BASE}/deviceauth/callback"
AUTHORIZE_URL = f"{AUTH_BASE}/oauth/authorize"
REDIRECT_URI = "http://localhost:1455/auth/callback"
SCOPE = "openid profile email offline_access"
LOGIN_TTL = 900  # a device code lasts 15 minutes
REQUEST_TIMEOUT = 15
# what the device token endpoint answers while the user hasn't approved yet
STILL_WAITING = ("deviceauth_authorization_pending", "slow_down")


def start() -> dict:
	"""A device code to show the user, the page to enter it on, and the state to poll with."""
	resp = requests.post(DEVICE_CODE_URL, json={"client_id": CLIENT_ID}, timeout=REQUEST_TIMEOUT)
	if resp.status_code >= 400:
		raise CodexError("ChatGPT didn't hand out a sign-in code. Try again, or use a browser link.")
	data = resp.json()
	state = secrets.token_urlsafe(32)
	save_login(state, {"device_auth_id": data["device_auth_id"], "user_code": data["user_code"]})
	return {
		"state": state,
		"code": data["user_code"],
		"url": DEVICE_PAGE,
		"interval": int(data.get("interval") or 5),
	}


def poll(state: str) -> dict:
	"""Where a device sign-in stands: pending, connected (with the models found), or expired."""
	login = load_login(state)
	if not login or "device_auth_id" not in login:
		return {"status": "expired"}
	approval = check_device(login)
	if approval is None:
		return {"status": "pending"}
	clear_login(state)
	credential = exchange_code(approval["authorization_code"], approval["code_verifier"], DEVICE_REDIRECT_URI)
	return {"status": "connected", **install_provider(credential)}


def start_browser() -> dict:
	"""The fallback: a sign-in link whose redirect the user pastes back to finish()."""
	verifier = secrets.token_urlsafe(64)
	state = secrets.token_urlsafe(32)
	save_login(state, {"verifier": verifier})
	return {"url": authorize_url(pkce_challenge(verifier), state), "state": state}


def finish(redirect_url: str) -> dict:
	"""Complete a browser-link sign-in from the localhost address it ended on."""
	query = parse_qs(urlparse(redirect_url or "").query)
	code = (query.get("code") or [""])[0]
	state = (query.get("state") or [""])[0]
	if not code or not state:
		raise CodexError(
			"That address has no sign-in code. Paste the full localhost address the browser was sent to."
		)
	login = load_login(state)
	if not login or "verifier" not in login:
		raise CodexError("This sign-in has expired. Open a new browser link and try again.")
	credential = exchange_code(code, login["verifier"], REDIRECT_URI)
	clear_login(state)
	return {"status": "connected", **install_provider(credential)}


def install_provider(credential: dict) -> dict:
	from builder.ai import presets

	return presets.connect(presets.find_preset("codex"), json.dumps(credential))


# --- the OAuth exchange ------------------------------------------------------


def check_device(login: dict) -> dict | None:
	"""The approved code and its verifier, or None while the user hasn't approved yet."""
	resp = requests.post(
		DEVICE_TOKEN_URL,
		json={"device_auth_id": login["device_auth_id"], "user_code": login["user_code"]},
		timeout=REQUEST_TIMEOUT,
	)
	if resp.ok:
		return resp.json()
	if resp.status_code in (403, 404) or error_code(resp) in STILL_WAITING:
		return None
	raise CodexError("ChatGPT turned the sign-in down. Start again from /providers.")


def error_code(resp: requests.Response) -> str:
	try:
		error = resp.json().get("error")
	except Exception:
		return ""
	return (error.get("code") if isinstance(error, dict) else error) or ""


def authorize_url(challenge: str, state: str) -> str:
	params = {
		"response_type": "code",
		"client_id": CLIENT_ID,
		"redirect_uri": REDIRECT_URI,
		"scope": SCOPE,
		"code_challenge": challenge,
		"code_challenge_method": "S256",
		"state": state,
		"id_token_add_organizations": "true",
		"codex_cli_simplified_flow": "true",
		"originator": ORIGINATOR,
	}
	return f"{AUTHORIZE_URL}?{urlencode(params)}"


def pkce_challenge(verifier: str) -> str:
	digest = hashlib.sha256(verifier.encode("ascii")).digest()
	return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def exchange_code(code: str, verifier: str, redirect_uri: str) -> dict:
	# form-encoded on purpose: the token endpoint doesn't take JSON
	resp = requests.post(
		TOKEN_URL,
		data={
			"grant_type": "authorization_code",
			"client_id": CLIENT_ID,
			"code": code,
			"code_verifier": verifier,
			"redirect_uri": redirect_uri,
		},
		timeout=30,
	)
	if resp.status_code >= 400:
		raise CodexError("ChatGPT rejected the sign-in code. Start the sign-in again.")
	tokens = resp.json()
	access = tokens.get("access_token") or ""
	return {
		"access": access,
		"refresh": tokens.get("refresh_token") or "",
		"expires": int(time.time() * 1000) + int(tokens.get("expires_in") or 3600) * 1000,
		"account_id": account_id_from_tokens(tokens.get("id_token"), access),
	}


# --- pending sign-ins, shared across workers via redis -----------------------


def save_login(state: str, data: dict) -> None:
	frappe.cache().set_value(login_key(state), json.dumps(data), expires_in_sec=LOGIN_TTL)


def load_login(state: str) -> dict | None:
	raw = frappe.cache().get_value(login_key(state))
	return json.loads(raw) if raw else None


def clear_login(state: str) -> None:
	frappe.cache().delete_value(login_key(state))


def login_key(state: str) -> str:
	return f"codex_oauth:{state}"
