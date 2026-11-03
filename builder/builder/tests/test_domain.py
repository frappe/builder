from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder import domain

PILOT_CLIENT = "frappe.integrations.frappe_providers.cloud_settings.PilotClient"


def pilot_row(name: str, *, is_site=False, is_primary=False, certificate="issued", redirect=False) -> dict:
	return {
		"domain": name,
		"is_site": is_site,
		"is_primary": is_primary,
		"certificate": certificate,
		"redirect_to_primary": redirect,
	}


class TestPilotDomains(FrappeTestCase):
	def setUp(self):
		self.client = MagicMock()
		self.client.site_path.side_effect = lambda path: f"sites/site.local/{path}"
		self.client.domain_path.side_effect = lambda name, suffix="": "/".join(
			filter(None, ["sites/site.local/domains", name, suffix])
		)
		for patcher in (
			patch.object(domain, "is_pilot_site", return_value=True),
			patch(PILOT_CLIENT, return_value=self.client),
			patch.object(domain, "capture"),
		):
			patcher.start()
			self.addCleanup(patcher.stop)

	def test_domains_come_from_pilot_in_the_frappe_cloud_shape(self):
		self.client.get.return_value = {
			"domains": [
				pilot_row("site.local", is_site=True, certificate="not_required", redirect=True),
				pilot_row("www.example.com", is_primary=True),
				pilot_row("shop.example.com", certificate="pending", redirect=True),
				pilot_row("old.example.com", certificate="missing"),
			]
		}

		self.assertEqual(
			domain.get_domains(),
			[
				{
					"domain": "www.example.com",
					"primary": True,
					"status": "Active",
					"redirect_to_primary": False,
				},
				{
					"domain": "shop.example.com",
					"primary": False,
					"status": "Pending",
					"redirect_to_primary": True,
				},
				{
					"domain": "old.example.com",
					"primary": False,
					"status": "Broken",
					"redirect_to_primary": False,
				},
			],
		)

	def test_the_site_name_is_listed_while_it_is_primary(self):
		self.client.get.return_value = {"domains": [pilot_row("site.local", is_site=True, is_primary=True)]}

		self.assertEqual([row["domain"] for row in domain.get_domains()], ["site.local"])

	def test_a_dns_mismatch_shows_the_pilot_message(self):
		self.client.get.return_value = {
			"matched": False,
			"message": "shop.example.com doesn't point here yet.",
		}

		with self.assertRaisesRegex(frappe.ValidationError, "doesn't point here yet"):
			domain.check_dns("shop.example.com")
		self.client.get.assert_called_once_with("sites/site.local/domains/shop.example.com/dns-check")

	def test_retry_adds_the_domain_again(self):
		domain.retry_add_domain("shop.example.com")

		self.client.post.assert_called_once_with("sites/site.local/domains", {"domain": "shop.example.com"})

	def test_primary_and_redirect_changes_patch_the_domain(self):
		domain.set_host_name("www.example.com")
		domain.set_redirect("shop.example.com")
		domain.unset_redirect("shop.example.com")

		self.assertEqual(
			[call.args[1] for call in self.client.patch.call_args_list],
			[{"primary": True}, {"redirect_to_primary": True}, {"redirect_to_primary": False}],
		)

	def test_the_server_ip_comes_from_pilot(self):
		self.client.get.return_value = {"ip": "203.0.113.10"}

		self.assertEqual(domain.get_server_ip(), "203.0.113.10")


class TestFrappeCloudDomains(FrappeTestCase):
	def test_a_frappe_cloud_v1_site_keeps_using_frappe_cloud(self):
		with (
			patch.object(domain, "is_pilot_site", return_value=False),
			patch.object(domain, "fc_call", return_value=[]) as fc_call,
		):
			self.assertEqual(domain.get_domains(), [])

		fc_call.assert_called_once_with("get_domains")
