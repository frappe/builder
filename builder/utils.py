from urllib.parse import urlparse

import frappe
import socket

from frappe.utils.safe_exec import (
	FrappeTransformer,
	NamespaceDict,
	_getattr_for_safe_exec,
	_getitem,
	_write,
	get_python_builtins,
	patched_qb,
	safe_exec_flags,
)

import json
from RestrictedPython import compile_restricted
from frappe.core.utils import html2text

from RestrictedPython.Guards import guarded_iter_unpack_sequence


def get_doc_as_dict(doctype, name):
	assert isinstance(doctype, str)
	assert isinstance(name, str)
	return frappe.get_doc(doctype, name).as_dict()


def make_safe_get_request(url, **kwargs):
	parsed = urlparse(url)
	parsed_ip = socket.gethostbyname(parsed.hostname)
	if parsed_ip.startswith("127", "10", "192", "172"):
		return

	return frappe.integrations.utils.make_get_request(url, **kwargs)


def safe_get_all(
	doctype,
	fields=None,
	**kwargs,
):
	# remove fields with function
	if fields:
		fields = [f for f in fields if "(" not in f]

	return frappe.db.get_all(
		doctype,
		fields,
		**kwargs,
	)


def get_safest_globals():
	user = getattr(frappe.local, "session", None) and frappe.local.session.user \
		or "Guest"

	out = NamespaceDict(
		json=NamespaceDict(loads=json.loads, dumps=json.dumps),
		as_json=frappe.as_json,
		dict=dict,
		get_value=frappe.db.get_value,
		get_all=frappe.db.get_all,
		get_list=safe_get_all,
		exists=frappe.db.exists,
		count=frappe.db.count,
		html2text=html2text,
		frappe=NamespaceDict(
			qb=frappe.qb,
			make_get_request=make_safe_get_request,
			get_doc=get_doc_as_dict,
		),
		session=frappe._dict(
			user=user,
			csrf_token=frappe.local.session.data.csrf_token
			if getattr(frappe.local, "session", None)
			else "",
		),
	)

	out._write_ = _write
	out._getitem_ = _getitem
	out._getattr_ = _getattr_for_safe_exec

	# allow iterators and list comprehension
	out._getiter_ = iter
	out._iter_unpack_sequence_ = guarded_iter_unpack_sequence

	# add common python builtins
	out.update(get_python_builtins())

	return out


def safer_exec(
	script: str,
	_globals: dict | None = None,
	_locals: dict | None = None,
	*,
	restrict_commit_rollback: bool = False,
	script_filename: str | None = None,
):
	exec_globals = get_safest_globals()
	if _globals:
		exec_globals.update(_globals)

	with safe_exec_flags(), patched_qb():
		# execute script compiled by RestrictedPython
		exec(
			compile_restricted(
				script, filename="<data-script>", policy=FrappeTransformer
			),
			exec_globals,
			_locals,
		)

	return exec_globals, _locals
