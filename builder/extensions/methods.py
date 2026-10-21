# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Server methods an extension runs.

`method.call` lets an extension run the whitelisted methods of installed apps,
as the current user. The site answers it once, at install.

Methods owned by `frappe` or `builder` are refused. Without that floor,
`method.call` would reach `frappe.client.set_value`, which is `data.access` in
disguise, and `builder.extensions.*`, through which an extension could grant
itself every permission. The owner is read from the function's own module as
well as from the name the caller sent, so a method re-exported under another
app's path is still refused.

This wrapper always runs in a POST, so it checks the verb the frame sent
against the method's own `methods=` list, the way Frappe checks a request.
"""

import frappe
from frappe import _
from frappe.modules.utils import load_doctype_module

from builder.extensions.access import assert_extension_access

REFUSED_APPS = ("frappe", "builder")

# a doc method checks the document's own permission the way Frappe's v2 route does
DOC_PERMISSION = {"GET": "read", "POST": "write"}

MODULE_VERBS = ("GET", "POST", "PUT", "DELETE")


class ServerMethod:
	"""One method an extension names: `myapp.api.export`, or `Form.get_summary`.

	`<DocType>.<method>` names a method of that doctype: a method on its
	controller class, or a function in its controller module. Frappe's v2 API
	reaches both through the doctype's name.
	"""

	def __init__(self, key: str):
		prefix, _dot, self.method_name = (key or "").rpartition(".")
		if not prefix or not self.method_name:
			frappe.throw(_("Name a method as a dotted path, such as myapp.api.export."))
		self.key = key
		self.doctype = prefix if frappe.db.exists("DocType", prefix) else None

	@property
	def app(self) -> str:
		if self.doctype:
			return frappe.get_doctype_app(self.doctype)
		return owning_app(self.function)

	@property
	def function(self):
		"""The function a module method or a doctype method runs."""
		if not self.doctype:
			return resolve_function(self.key)
		function = getattr(load_doctype_module(self.doctype), self.method_name, None)
		if not callable(function):
			frappe.throw(_("{0} has no method {1}.").format(self.doctype, self.method_name))
		return function

	def assert_not_refused(self, function=None) -> None:
		apps = {self.app, owning_app(function)} if function else {self.app}
		refused = sorted(apps & set(REFUSED_APPS))
		if refused:
			frappe.throw(
				_(
					"An extension cannot run methods of {0}. It reaches their data through builder.data."
				).format(refused[0]),
				frappe.PermissionError,
			)


def resolve_function(path: str):
	path = frappe.override_whitelisted_method(path)
	try:
		return frappe.get_attr(path)
	except Exception:
		frappe.throw(_("There is no method {0}.").format(path), frappe.DoesNotExistError)


def owning_app(function) -> str:
	return (getattr(function, "__module__", "") or "").split(".", 1)[0]


def assert_runnable(server_method: ServerMethod, function, verb: str) -> None:
	"""The floor, Frappe's own whitelist, and the verb the frame sent."""
	server_method.assert_not_refused(function)
	frappe.is_whitelisted(function)
	if verb not in frappe.allowed_http_methods_for_whitelisted_func.get(function, ()):
		frappe.throw(_("{0} does not accept {1}.").format(server_method.key, verb), frappe.PermissionError)


def read_verb(verb: str, allowed: tuple[str, ...]) -> str:
	verb = (verb or "").upper()
	if verb not in allowed:
		frappe.throw(_("A method call must use one of: {0}").format(", ".join(allowed)))
	return verb


def run_with_form_dict(function, args: dict):
	"""Some Frappe code reads the whole request `form_dict`, which here holds this
	wrapper's own arguments. The method sees only its own, as it would over HTTP."""
	sent = frappe.local.form_dict
	frappe.local.form_dict = frappe._dict(args)
	try:
		return frappe.call(function, **args)
	finally:
		frappe.local.form_dict = sent


@frappe.whitelist(methods=["POST"])
def run_method(extension: str, method: str, verb: str = "POST", args: dict | None = None):
	"""A module method, or a function in a doctype's controller module."""
	assert_extension_access(extension, "method.call")
	server_method = ServerMethod(method)
	server_method.assert_not_refused()

	function = server_method.function
	assert_runnable(server_method, function, read_verb(verb, MODULE_VERBS))
	return run_with_form_dict(function, args or {})


@frappe.whitelist(methods=["POST"])
def run_doc_method(
	extension: str, doctype: str, name: str, method: str, verb: str = "POST", args: dict | None = None
) -> dict:
	"""A method on one document. Answers with the document too, the way Frappe does,
	so a frappe-ui document resource refreshes from it."""
	assert_extension_access(extension, "method.call")
	server_method = ServerMethod(f"{doctype}.{method}")
	server_method.assert_not_refused()

	verb = read_verb(verb, tuple(DOC_PERMISSION))
	document = frappe.get_doc(doctype, name)
	bound = getattr(document, method, None)
	if not callable(bound):
		frappe.throw(_("{0} has no method {1}.").format(doctype, method), frappe.DoesNotExistError)
	assert_runnable(server_method, getattr(bound, "__func__", bound), verb)

	document.check_permission(DOC_PERMISSION[verb])
	message = document.run_method(method, **(args or {}))
	document.apply_fieldlevel_read_permissions()
	return {"message": message, "docs": [document.as_dict()]}
