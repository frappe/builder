"""Browser sign-in for the ChatGPT (Codex) provider.

The Codex OAuth client only ever redirects to http://localhost:1455/auth/callback,
so the login can't land on the site directly. start() binds a one-shot listener
on that port, which catches the redirect whenever the server and the browser
share a machine (any local bench). When they don't, or the port is taken, the
user pastes the URL the browser ended up on and finish() completes the same
exchange. Either way the tokens never pass through the browser session: the
code is exchanged server-side with the PKCE verifier cached at start().
"""

import base64
import hashlib
import json
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import frappe
import requests

from builder.ai.codex import CLIENT_ID, ORIGINATOR, TOKEN_URL, CodexError, account_id_from_tokens

AUTHORIZE_URL = "https://auth.openai.com/oauth/authorize"
REDIRECT_URI = "http://localhost:1455/auth/callback"
SCOPE = "openid profile email offline_access"
CALLBACK_PORT = 1455
LOGIN_TTL = 600  # seconds a started login stays completable


def start() -> dict:
	"""A fresh login attempt: PKCE pair and state cached for poll()/finish(),
	plus the local callback listener when the port allows one."""
	verifier = secrets.token_urlsafe(64)
	state = secrets.token_urlsafe(32)
	save_login(state, {"status": "pending", "verifier": verifier})
	capture = start_listener(frappe.local.site)
	return {"url": authorize_url(pkce_challenge(verifier), state), "state": state, "capture": capture}


def poll(state: str) -> dict:
	"""Where a started login stands. The listener thread only stashes the
	exchanged credential; the provider row is created here, in an ordinary
	authenticated request, never from the unauthenticated callback."""
	login = load_login(state)
	if not login:
		return {"status": "expired"}
	if login["status"] == "connected":
		install_provider(login["credential"])
		clear_login(state)
		return {"status": "connected"}
	if login["status"] == "failed":
		clear_login(state)
		return {"status": "failed", "message": login.get("message") or "Sign-in failed"}
	return {"status": "pending"}


def finish(redirect_url: str) -> dict:
	"""Complete a login from the pasted redirect URL, for when the listener
	could not see the browser's redirect (remote server, port taken)."""
	query = parse_qs(urlparse(redirect_url or "").query)
	code = (query.get("code") or [""])[0]
	state = (query.get("state") or [""])[0]
	if not code or not state:
		raise CodexError(
			"That URL has no sign-in code. Paste the full localhost address the browser was sent to."
		)
	login = load_login(state)
	if not login:
		raise CodexError("This sign-in attempt has expired. Click Sign in with ChatGPT and try again.")
	install_provider(exchange_code(code, login["verifier"]))
	clear_login(state)
	return {"status": "connected"}


def install_provider(credential: dict) -> None:
	# models come later from the setup flow's normal finish step
	from builder.ai import presets

	preset = presets.find_preset("codex")
	presets.install_preset(preset, json.dumps(credential), "", [])


# --- the OAuth exchange ------------------------------------------------------


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


def exchange_code(code: str, verifier: str) -> dict:
	# form-encoded on purpose: the token endpoint doesn't take JSON
	resp = requests.post(
		TOKEN_URL,
		data={
			"grant_type": "authorization_code",
			"client_id": CLIENT_ID,
			"code": code,
			"code_verifier": verifier,
			"redirect_uri": REDIRECT_URI,
		},
		timeout=30,
	)
	if resp.status_code >= 400:
		raise CodexError("ChatGPT rejected the sign-in code. Click Sign in with ChatGPT and try again.")
	tokens = resp.json()
	access = tokens.get("access_token") or ""
	return {
		"access": access,
		"refresh": tokens.get("refresh_token") or "",
		"expires": int(time.time() * 1000) + int(tokens.get("expires_in") or 3600) * 1000,
		"account_id": account_id_from_tokens(tokens.get("id_token"), access),
	}


# --- pending logins, shared across workers via redis -------------------------


def save_login(state: str, data: dict) -> None:
	frappe.cache().set_value(login_key(state), json.dumps(data), expires_in_sec=LOGIN_TTL)


def load_login(state: str) -> dict | None:
	raw = frappe.cache().get_value(login_key(state))
	return json.loads(raw) if raw else None


def clear_login(state: str) -> None:
	frappe.cache().delete_value(login_key(state))


def login_key(state: str) -> str:
	return f"codex_oauth:{state}"


# --- the localhost callback listener -----------------------------------------

listener_lock = threading.Lock()
listener_running = False


def start_listener(site: str) -> bool:
	"""One listener serves every pending login: the redirect carries the state,
	and the state finds its verifier in the cache. So a retried sign-in reuses
	the running listener instead of fighting it for the port."""
	global listener_running
	with listener_lock:
		if listener_running:
			return True
		try:
			server = HTTPServer(("127.0.0.1", CALLBACK_PORT), CallbackHandler)
		except OSError:
			return False  # someone else holds the port (the codex CLI?): the paste path still works
		server.site = site
		listener_running = True
	threading.Thread(target=serve_logins, args=(server,), daemon=True).start()
	return True


def serve_logins(server: HTTPServer) -> None:
	global listener_running
	deadline = time.time() + LOGIN_TTL
	server.timeout = 5
	try:
		while time.time() < deadline and not getattr(server, "done", False):
			server.handle_request()
	finally:
		with listener_lock:
			listener_running = False
		server.server_close()


class CallbackHandler(BaseHTTPRequestHandler):
	def do_GET(self):
		parsed = urlparse(self.path)
		query = parse_qs(parsed.query)
		code = (query.get("code") or [""])[0]
		state = (query.get("state") or [""])[0]
		if parsed.path != "/auth/callback" or not code or not state:
			self.respond(404, "Not found")
			return
		outcome = complete_captured(self.server.site, state, code)
		if outcome is None:
			self.respond(400, "This sign-in attempt is stale. Return to Builder and try again.")
			return
		self.server.done = True
		ok, message = outcome
		self.respond(200 if ok else 500, message)

	def respond(self, status: int, message: str) -> None:
		body = PAGE.format(message=message).encode()
		self.send_response(status)
		self.send_header("Content-Type", "text/html; charset=utf-8")
		self.send_header("Content-Length", str(len(body)))
		self.end_headers()
		self.wfile.write(body)

	def log_message(self, *args) -> None:
		pass  # keep the web server's log out of it


def complete_captured(site: str, state: str, code: str) -> tuple[bool, str] | None:
	"""Exchange a captured code and stash the outcome for poll(). Runs on the
	listener thread, which has no request context; borrow one for redis."""
	frappe.init(site)
	try:
		login = load_login(state)
		if not login or login.get("status") != "pending":
			return None
		try:
			credential = exchange_code(code, login["verifier"])
			save_login(state, {"status": "connected", "credential": credential})
			return True, "Connected. You can close this tab and return to Builder."
		except Exception as e:
			save_login(state, {"status": "failed", "message": str(e)})
			return False, "Sign-in failed. Return to Builder and try again."
	finally:
		frappe.destroy()


PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Builder</title></head>
<body style="font-family: -apple-system, sans-serif; display: grid; place-items: center; height: 100vh; margin: 0; color: #1f272e;">
<p style="font-size: 15px;">{message}</p>
</body></html>"""
