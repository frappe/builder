from urllib.parse import urlparse

import frappe
import socket

from frappe.utils.safe_exec import (
	FrappeTransformer,
	NamespaceDict,
	get_python_builtins,
	safe_exec_flags,
	get_safe_globals,
	SERVER_SCRIPT_FILE_PREFIX
)

from RestrictedPython import compile_restricted



def get_doc_as_dict(doctype, name):
	assert isinstance(doctype, str)
	assert isinstance(name, str)
	return frappe.get_doc(doctype, name).as_dict()

def get_cached_doc_as_dict(doctype, name):
	assert isinstance(doctype, str)
	assert isinstance(name, str)
	return frappe.get_cached_doc(doctype, name).as_dict()


def make_safe_get_request(url, **kwargs):
	parsed = urlparse(url)
	parsed_ip = socket.gethostbyname(parsed.hostname)
	if parsed_ip.startswith("127", "10", "192", "172"):
		return

	return frappe.integrations.utils.make_get_request(url, **kwargs)

def safe_get_list(*args, **kwargs):
	if args and len(args) > 1 and isinstance(args[1], list):
		args = list(args)
		args[1] = remove_unsafe_fields(args[1])

	fields = kwargs.get("fields", [])
	if fields:
		kwargs["fields"] = remove_unsafe_fields(fields)

	return frappe.db.get_list(
		*args,
		**kwargs,
	)

def safe_get_all(*args, **kwargs):
	kwargs["ignore_permissions"] = True
	if "limit_page_length" not in kwargs:
		kwargs["limit_page_length"] = 0

	return safe_get_list(*args, **kwargs)


def remove_unsafe_fields(fields):
	return [f for f in fields if not "(" in f]

def get_safer_globals():
	safe_globals = get_safe_globals()

	out = NamespaceDict(
		json=safe_globals["json"],
		as_json=frappe.as_json,
		dict=safe_globals["dict"],
		frappe=NamespaceDict(
			db=NamespaceDict(
				count=frappe.db.count,
				exists=frappe.db.exists,
				get_all=safe_get_all,
				get_list=safe_get_list,
			),
			make_get_request=make_safe_get_request,
			get_doc=get_doc_as_dict,
			get_cached_doc=get_cached_doc_as_dict,
			_=frappe._,
			session=safe_globals["frappe"]["session"],
		),
	)

	out._write_ = safe_globals["_write_"]
	out._getitem_ = safe_globals["_getitem_"]
	out._getattr_ = safe_globals["_getattr_"]
	out._getiter_ = safe_globals["_getiter_"]
	out._iter_unpack_sequence_ = safe_globals["_iter_unpack_sequence_"]

	# add common python builtins
	out.update(get_python_builtins())

	return out


def safer_exec(
	script: str,
	_globals: dict | None = None,
	_locals: dict | None = None,
	*,
	script_filename: str | None = None,
):
	exec_globals = get_safer_globals()
	if _globals:
		exec_globals.update(_globals)

	filename = SERVER_SCRIPT_FILE_PREFIX
	if script_filename:
		filename += f": {frappe.scrub(script_filename)}"

	with safe_exec_flags():
		# execute script compiled by RestrictedPython
		exec(
			compile_restricted(
				script, filename=filename, policy=FrappeTransformer
			),
			exec_globals,
			_locals,
		)

	return exec_globals, _locals
