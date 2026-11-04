# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import json
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.clone_onboarding import (
	CLONE_USER,
	STATE_KEY,
	call_service,
	clone_status,
	clone_user_keys,
	confirm_clone_request,
	design_for,
	disable_clone_user,
	nonce_key,
	start_clone,
)

CLOUD = "builder.clone_onboarding.get_cloud_settings"
SERVICE = "builder.clone_onboarding.call_service"
SESSION = "builder.clone_onboarding.public_session"


class CloneTestCase(FrappeTestCase):
	def setUp(self):
		frappe.db.set_default(STATE_KEY, "")
		# the module commits so the service can use the key mid-request; the class rollback must still undo it
		commit = patch.object(frappe.db, "commit")
		commit.start()
		self.addCleanup(commit.stop)


class TestStartClone(CloneTestCase):
	def test_refuses_outside_frappe_cloud(self):
		with patch(CLOUD, return_value={"enabled": False}):
			self.assertRaises(frappe.ValidationError, start_clone, "example.com")

	def test_refuses_an_unknown_look(self):
		with patch(CLOUD, return_value={"enabled": True}):
			self.assertRaises(frappe.ValidationError, start_clone, "example.com", "glitter")

	def test_hands_the_service_a_fresh_key_and_a_nonce(self):
		confirmed = []

		def service(endpoint: str, payload: dict, http: str = "POST") -> dict:
			if endpoint == "status":
				return {"status": "Queued", "source_url": "https://example.com"}
			confirmed.append(confirm_clone_request(payload["nonce"]))
			return {"move": "m1", "token": "t1"}

		with patch(CLOUD, return_value={"enabled": True}), patch(SERVICE, side_effect=service) as called:
			view = start_clone("example.com", "redesign")
		payload = called.call_args_list[0].args[1]
		self.assertEqual(view["status"], "Queued")
		self.assertEqual(confirmed, [True])
		self.assertEqual(frappe.db.get_value("User", CLONE_USER, "api_key"), payload["api_key"])
		self.assertTrue({"System Manager", "Website Manager"} <= set(frappe.get_roles(CLONE_USER)))
		self.assertEqual(json.loads(payload["design"])["mode"], "redesign")
		self.assertEqual(json.loads(frappe.db.get_default(STATE_KEY)), {"clone": "m1", "token": "t1"})

	def test_other_looks_go_through_as_they_are(self):
		self.assertEqual(design_for("as_is"), {"mode": "as_is"})


class TestCloneStatus(CloneTestCase):
	def test_nothing_started(self):
		self.assertIsNone(clone_status())

	def test_a_finished_clone_disables_the_key(self):
		frappe.db.set_default(STATE_KEY, json.dumps({"clone": "m1", "token": "t1"}))
		clone_user_keys()
		with patch(SERVICE, return_value={"status": "Done"}) as service:
			self.assertEqual(clone_status()["status"], "Done")
		service.assert_called_once_with("status", {"move": "m1", "token": "t1"}, http="GET")
		self.assertEqual(frappe.db.get_value("User", CLONE_USER, ["enabled", "api_key"]), (0, None))
		disable_clone_user()


class TestConfirmCloneRequest(FrappeTestCase):
	def test_a_nonce_confirms_once(self):
		frappe.cache.set_value(nonce_key("abc"), 1)
		self.assertTrue(confirm_clone_request("abc"))
		self.assertFalse(confirm_clone_request("abc"))


class TestCallService(FrappeTestCase):
	def service(self, status: int, body: dict) -> MagicMock:
		response = MagicMock(status_code=status)
		response.json.return_value = body
		session = MagicMock()
		session.get.return_value = session.post.return_value = response
		return session

	def test_posts_and_unwraps_the_message(self):
		session = self.service(200, {"message": {"move": "m1"}})
		with patch(SESSION, return_value=session):
			self.assertEqual(call_service("start_into", {"url": "example.com"}), {"move": "m1"})
		self.assertTrue(session.post.call_args.args[0].endswith("/api/method/moveday.api.start_into"))

	def test_status_is_a_get(self):
		session = self.service(200, {"message": {"status": "Queued"}})
		with patch(SESSION, return_value=session):
			call_service("status", {"move": "m1"}, http="GET")
		self.assertEqual(session.get.call_args.kwargs["params"], {"move": "m1"})

	def test_shows_the_service_reason(self):
		reason = "A clone into this site is already running."
		messages = json.dumps([json.dumps({"message": ""}), json.dumps({"message": reason})])
		with patch(SESSION, return_value=self.service(417, {"_server_messages": messages})):
			with self.assertRaises(frappe.ValidationError) as caught:
				call_service("start_into", {})
		self.assertIn(reason, str(caught.exception))

	def test_falls_back_without_a_reason(self):
		with patch(SESSION, return_value=self.service(502, {})):
			self.assertRaises(frappe.ValidationError, call_service, "status", {}, "GET")
