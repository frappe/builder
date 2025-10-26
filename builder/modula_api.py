"""
Modula Integration API
Endpoints for communication between Modula (modula.digital) and Builder (builder.modula.digital)
"""

import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from pathlib import Path

import frappe
import requests
import jwt
from frappe import _
from frappe.utils import now_datetime, get_datetime
from werkzeug.wrappers import Response


# ============================================================================
# Configuration
# ============================================================================

def get_modula_config():
	"""Get Modula integration configuration from site config"""
	return {
		"api_url": frappe.conf.get("modula_api_url", "https://modula.digital"),
		"jwt_secret": frappe.conf.get("modula_jwt_secret"),
		"jwt_public_key": frappe.conf.get("modula_jwt_public_key"),
		"jwt_algorithm": frappe.conf.get("modula_jwt_algorithm", "HS256"),
		"snippets_path": frappe.conf.get("modula_snippets_path", "/content/snippets"),
		"templates_path": frappe.conf.get("modula_templates_path", "/content/themes/default/templates/blocks"),
	}


# ============================================================================
# Authentication
# ============================================================================

@frappe.whitelist(allow_guest=True)
def validate_token(token: str) -> Dict[str, Any]:
	"""
	Validate JWT token from Modula

	Args:
		token: JWT token from Modula

	Returns:
		Dict containing user info and permissions

	Raises:
		frappe.AuthenticationError if token is invalid
	"""
	try:
		config = get_modula_config()

		# Decode JWT
		if config["jwt_algorithm"].startswith("RS"):
			# RSA algorithm - use public key
			if not config["jwt_public_key"]:
				frappe.throw(_("JWT public key not configured"))
			payload = jwt.decode(
				token,
				config["jwt_public_key"],
				algorithms=[config["jwt_algorithm"]],
				audience="https://builder.modula.digital"
			)
		else:
			# Symmetric algorithm - use shared secret
			if not config["jwt_secret"]:
				frappe.throw(_("JWT secret not configured"))
			payload = jwt.decode(
				token,
				config["jwt_secret"],
				algorithms=[config["jwt_algorithm"]],
				audience="https://builder.modula.digital"
			)

		# Validate required fields
		required_fields = ["sub", "project_id", "type", "iat", "exp"]
		for field in required_fields:
			if field not in payload:
				frappe.throw(_(f"Missing required field: {field}"))

		# Check expiration
		if payload["exp"] < datetime.utcnow().timestamp():
			frappe.throw(_("Token has expired"))

		# Optionally validate with Modula API
		if frappe.conf.get("modula_validate_via_api"):
			validate_with_modula_api(token)

		return {
			"valid": True,
			"user_id": payload["sub"],
			"project_id": payload.get("project_id"),
			"build_type": payload.get("type"),
			"permissions": payload.get("permissions", ["edit", "publish"]),
			"expires_at": datetime.fromtimestamp(payload["exp"]).isoformat()
		}

	except jwt.ExpiredSignatureError:
		frappe.throw(_("Token has expired"), frappe.AuthenticationError)
	except jwt.InvalidTokenError as e:
		frappe.throw(_(f"Invalid token: {str(e)}"), frappe.AuthenticationError)
	except Exception as e:
		frappe.log_error(f"Token validation error: {str(e)}")
		frappe.throw(_("Token validation failed"), frappe.AuthenticationError)


def validate_with_modula_api(token: str) -> bool:
	"""Validate token by calling Modula's validation endpoint"""
	config = get_modula_config()

	try:
		response = requests.post(
			f"{config['api_url']}/api/auth/validate",
			json={"token": token},
			timeout=5
		)

		if response.status_code == 200:
			return response.json().get("valid", False)

		return False

	except requests.RequestException as e:
		frappe.log_error(f"Modula API validation error: {str(e)}")
		return False


def get_current_modula_user() -> Optional[Dict[str, Any]]:
	"""
	Get current Modula user from session
	Returns None if not authenticated via Modula
	"""
	token = frappe.get_request_header("Authorization", "").replace("Bearer ", "")
	if not token:
		return None

	try:
		return validate_token(token)
	except:
		return None


# ============================================================================
# Export API
# ============================================================================

@frappe.whitelist()
def export_build(
	page_name: str,
	format: str = "all",
	options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
	"""
	Export a Builder page to various formats

	Args:
		page_name: Name of the Builder Page document
		format: Export format - "html", "json", "tpl", or "all"
		options: Export options (minify, inline_css, scoped, etc.)

	Returns:
		Dict containing exported content in requested format(s)
	"""
	# Validate permissions
	if not frappe.has_permission("Builder Page", "read", page_name):
		frappe.throw(_("You do not have permission to export this page"))

	# Load page
	page = frappe.get_doc("Builder Page", page_name)

	# Parse options
	if isinstance(options, str):
		options = json.loads(options)
	options = options or {}

	# Generate build code if not exists
	build_code = page.get("modula_build_code")
	if not build_code:
		build_code = f"b_{frappe.generate_hash(length=12)}"
		page.db_set("modula_build_code", build_code, update_modified=False)

	# Export based on format
	exports = {}

	if format in ["html", "all"]:
		exports["html"] = export_html_fragment(page, options)

	if format in ["json", "all"]:
		exports["json"] = export_mdk_json(page, options)

	if format in ["tpl", "all"]:
		exports["tpl"] = export_smarty_template(page, options)

	return {
		"build_code": build_code,
		"page_name": page_name,
		"exports": exports,
		"timestamp": now_datetime().isoformat()
	}


def export_html_fragment(page, options: Dict[str, Any]) -> str:
	"""
	Export page as clean HTML fragment
	Suitable for direct injection into Modula pages
	"""
	from builder.builder.doctype.builder_page.builder_page import BuilderPageRenderer

	# Get page HTML
	renderer = BuilderPageRenderer(path="")
	renderer.docname = page.name
	renderer.doctype = "Builder Page"
	frappe.local.no_cache = 1
	renderer.init_context()
	response = renderer.render()
	html = str(response.data, "utf-8")

	# Extract body content (remove <html>, <head>, etc.)
	html = extract_body_content(html)

	# Apply options
	if options.get("scoped", True):
		html = add_scoped_styles(html, page.get("modula_build_code"))

	if options.get("minify", False):
		html = minify_html(html)

	if options.get("inline_css", True):
		html = inline_critical_css(html)

	# Add metadata comment
	metadata = f"<!-- Modula Build: {page.get('modula_build_code')} | Generated: {now_datetime().isoformat()} -->\n"

	return metadata + html


def export_mdk_json(page, options: Dict[str, Any]) -> Dict[str, Any]:
	"""
	Export page as MDK JSON schema
	Enables re-editing and portability
	"""
	blocks = json.loads(page.blocks or "[]")

	# Get current user from Modula context
	modula_user = get_current_modula_user()

	mdk_schema = {
		"version": "1.0.0",
		"type": page.get("modula_build_type", "component"),
		"project_id": page.get("modula_project_id"),

		"metadata": {
			"name": page.page_title or page.name,
			"description": page.get("description"),
			"created_at": page.creation.isoformat() if page.creation else None,
			"updated_at": page.modified.isoformat() if page.modified else None,
			"author": modula_user.get("user_id") if modula_user else page.owner,
			"tags": []
		},

		"tree": convert_blocks_to_mdk_tree(blocks),

		"variables": extract_variables_from_blocks(blocks),

		"responsive": {
			"breakpoints": {
				"mobile": 768,
				"tablet": 1024
			}
		},

		"assets": extract_assets_from_page(page),

		"scripts": {
			"interactions": [],
			"custom": page.get("page_script") or ""
		}
	}

	return mdk_schema


def export_smarty_template(page, options: Dict[str, Any]) -> str:
	"""
	Export page as Smarty template (.tpl)
	For first-class Sngine integration
	"""
	# Get HTML fragment
	html = export_html_fragment(page, options)

	# Convert variables to Smarty syntax
	html = convert_to_smarty_variables(html)

	# Add Smarty header
	build_code = page.get("modula_build_code")
	version = page.get("modula_version", "1.0.0")

	header = f"""{{*
 * Modula Builder - Smarty Template
 * Build: {build_code}
 * Version: {version}
 * Generated: {now_datetime().isoformat()}
 *
 * This file was automatically generated by Modula Builder.
 * Manual changes may be overwritten on next publish.
 *}}

"""

	return header + html


# ============================================================================
# Publish API
# ============================================================================

@frappe.whitelist()
def publish_build(
	page_name: str,
	version: Optional[str] = None,
	callback_url: Optional[str] = None,
	options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
	"""
	Publish a build and optionally send callback to Modula

	Args:
		page_name: Name of the Builder Page
		version: Version string (e.g., "1.0.1")
		callback_url: URL to send publish notification
		options: Publish options (create_version, deploy_to_file, etc.)

	Returns:
		Dict with publish status and artifact URLs
	"""
	# Validate permissions
	if not frappe.has_permission("Builder Page", "write", page_name):
		frappe.throw(_("You do not have permission to publish this page"))

	# Parse options
	if isinstance(options, str):
		options = json.loads(options)
	options = options or {}

	# Load page
	page = frappe.get_doc("Builder Page", page_name)

	# Generate build code
	build_code = page.get("modula_build_code")
	if not build_code:
		build_code = f"b_{frappe.generate_hash(length=12)}"
		page.db_set("modula_build_code", build_code, update_modified=False)

	# Determine version
	if not version:
		current_version = page.get("modula_version", "1.0.0")
		version = increment_version(current_version)

	# Update page version
	page.db_set("modula_version", version, update_modified=False)
	page.db_set("modula_published_at", now_datetime(), update_modified=False)

	# Export all formats
	export_options = {
		"minify": options.get("minify", False),
		"inline_css": options.get("inline_css", True),
		"scoped": options.get("scoped", True)
	}

	exports = export_build(page_name, format="all", options=export_options)

	# Create version snapshot if requested
	if options.get("create_version", True):
		create_version_snapshot(page, version, exports)

	# Deploy to file system if requested
	artifact_urls = {}
	if options.get("deploy_to_file", True):
		artifact_urls = deploy_to_filesystem(page, version, exports)

	# Send callback to Modula
	callback_sent = False
	if callback_url:
		callback_sent = send_publish_callback(
			callback_url,
			page,
			build_code,
			version,
			artifact_urls
		)

	return {
		"success": True,
		"build_code": build_code,
		"version": version,
		"page_name": page_name,
		"artifacts": artifact_urls,
		"callback_sent": callback_sent,
		"published_at": now_datetime().isoformat()
	}


def create_version_snapshot(page, version: str, exports: Dict[str, Any]):
	"""Create a version snapshot in Modula Builder Version doctype"""
	# TODO: Create custom doctype for version history
	# For now, store in page's custom field

	snapshot = {
		"version": version,
		"timestamp": now_datetime().isoformat(),
		"exports": exports,
		"blocks": page.blocks,
		"page_data": page.page_data_script
	}

	# Store snapshot (this would go to modula_builder_versions table)
	frappe.log_error(f"Version snapshot created: {json.dumps(snapshot)[:500]}")


def deploy_to_filesystem(page, version: str, exports: Dict[str, Any]) -> Dict[str, str]:
	"""
	Deploy artifacts to file system
	Returns dict of artifact URLs
	"""
	config = get_modula_config()
	project_id = page.get("modula_project_id", "default")

	# Create directories
	snippets_dir = Path(config["snippets_path"]) / project_id / version
	snippets_dir.mkdir(parents=True, exist_ok=True)

	templates_dir = Path(config["templates_path"])
	templates_dir.mkdir(parents=True, exist_ok=True)

	artifact_urls = {}

	# Save HTML fragment
	if "html" in exports["exports"]:
		html_path = snippets_dir / "fragment.html"
		html_path.write_text(exports["exports"]["html"])
		artifact_urls["html_fragment"] = f"/content/snippets/{project_id}/{version}/fragment.html"

	# Save MDK JSON
	if "json" in exports["exports"]:
		json_path = snippets_dir / "build.mdk.json"
		json_path.write_text(json.dumps(exports["exports"]["json"], indent=2))
		artifact_urls["mdk_json"] = f"/content/snippets/{project_id}/{version}/build.mdk.json"

	# Save Smarty template
	if "tpl" in exports["exports"]:
		build_type = page.get("modula_build_type", "component")
		tpl_filename = f"{build_type}_{project_id}.tpl"
		tpl_path = templates_dir / tpl_filename
		tpl_path.write_text(exports["exports"]["tpl"])
		artifact_urls["smarty_tpl"] = f"/content/themes/default/templates/blocks/{tpl_filename}"

	# Create "latest" symlink
	latest_link = Path(config["snippets_path"]) / project_id / "latest"
	if latest_link.exists():
		latest_link.unlink()
	latest_link.symlink_to(version, target_is_directory=True)

	return artifact_urls


def send_publish_callback(
	callback_url: str,
	page,
	build_code: str,
	version: str,
	artifacts: Dict[str, str]
) -> bool:
	"""Send publish notification to Modula"""
	try:
		# Generate JWT for builder -> modula auth
		config = get_modula_config()

		payload = {
			"iss": "https://builder.modula.digital",
			"aud": config["api_url"],
			"sub": "builder",
			"iat": datetime.utcnow().timestamp(),
			"exp": (datetime.utcnow() + timedelta(minutes=5)).timestamp()
		}

		if config["jwt_algorithm"].startswith("RS"):
			# Would use private key here
			token = jwt.encode(payload, config.get("jwt_private_key", ""), algorithm=config["jwt_algorithm"])
		else:
			token = jwt.encode(payload, config["jwt_secret"], algorithm=config["jwt_algorithm"])

		# Send callback
		response = requests.post(
			callback_url,
			headers={
				"Authorization": f"Bearer {token}",
				"Content-Type": "application/json"
			},
			json={
				"project_id": page.get("modula_project_id"),
				"build_code": build_code,
				"version": version,
				"artifacts": artifacts,
				"status": "published",
				"timestamp": now_datetime().isoformat()
			},
			timeout=10
		)

		return response.status_code == 200

	except Exception as e:
		frappe.log_error(f"Publish callback error: {str(e)}")
		return False


# ============================================================================
# Import/Re-open API
# ============================================================================

@frappe.whitelist()
def import_from_mdk(
	mdk_json: str | Dict[str, Any],
	page_name: Optional[str] = None,
	project_id: Optional[str] = None
) -> Dict[str, Any]:
	"""
	Import/re-open build from MDK JSON

	Args:
		mdk_json: MDK JSON schema (string or dict)
		page_name: Optional existing page name to update
		project_id: Modula project ID

	Returns:
		Dict with page info
	"""
	# Parse JSON if string
	if isinstance(mdk_json, str):
		mdk_json = json.loads(mdk_json)

	# Validate schema
	validate_mdk_schema(mdk_json)

	# Create or update page
	if page_name and frappe.db.exists("Builder Page", page_name):
		page = frappe.get_doc("Builder Page", page_name)
		if not frappe.has_permission("Builder Page", "write", page_name):
			frappe.throw(_("You do not have permission to update this page"))
	else:
		page = frappe.new_doc("Builder Page")
		page.page_title = mdk_json["metadata"].get("name", "Untitled")

	# Convert MDK tree to Frappe Builder blocks
	blocks = convert_mdk_tree_to_blocks(mdk_json["tree"])

	# Update page
	page.blocks = json.dumps(blocks)
	page.modula_project_id = project_id or mdk_json.get("project_id")
	page.modula_build_type = mdk_json.get("type")
	page.modula_version = mdk_json.get("version", "1.0.0")

	if mdk_json.get("scripts", {}).get("custom"):
		page.page_script = mdk_json["scripts"]["custom"]

	# Save
	if page.is_new():
		page.insert()
	else:
		page.save()

	return {
		"success": True,
		"page_name": page.name,
		"page_title": page.page_title
	}


# ============================================================================
# Helper Functions
# ============================================================================

def extract_body_content(html: str) -> str:
	"""Extract content from <body> tag"""
	import re
	body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL)
	if body_match:
		return body_match.group(1).strip()
	return html


def add_scoped_styles(html: str, build_code: str) -> str:
	"""Add scoped attribute to style tags"""
	import re
	html = re.sub(r'<style>', f'<style scoped data-build="{build_code}">', html)
	return html


def minify_html(html: str) -> str:
	"""Basic HTML minification"""
	import re
	# Remove comments
	html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
	# Remove extra whitespace
	html = re.sub(r'\s+', ' ', html)
	# Remove whitespace between tags
	html = re.sub(r'>\s+<', '><', html)
	return html.strip()


def inline_critical_css(html: str) -> str:
	"""Inline critical CSS (basic implementation)"""
	# TODO: Implement critical CSS extraction
	return html


def convert_blocks_to_mdk_tree(blocks: list) -> Dict[str, Any]:
	"""Convert Frappe Builder blocks to MDK tree format"""
	if not blocks or len(blocks) == 0:
		return {}

	root_block = blocks[0] if isinstance(blocks, list) else blocks

	return convert_block_to_mdk_node(root_block)


def convert_block_to_mdk_node(block: Dict[str, Any]) -> Dict[str, Any]:
	"""Convert a single block to MDK node"""
	node = {
		"blockId": block.get("blockId"),
		"element": block.get("element", "div"),
		"attributes": block.get("attributes", {}),
		"baseStyles": block.get("baseStyles", {}),
	}

	if "mobileStyles" in block:
		node["mobileStyles"] = block["mobileStyles"]

	if "tabletStyles" in block:
		node["tabletStyles"] = block["tabletStyles"]

	if "children" in block and block["children"]:
		node["children"] = [convert_block_to_mdk_node(child) for child in block["children"]]

	if "dataKey" in block:
		node["dataBinding"] = block["dataKey"]

	return node


def convert_mdk_tree_to_blocks(tree: Dict[str, Any]) -> list:
	"""Convert MDK tree to Frappe Builder blocks"""
	if not tree:
		return []

	return [convert_mdk_node_to_block(tree)]


def convert_mdk_node_to_block(node: Dict[str, Any]) -> Dict[str, Any]:
	"""Convert MDK node to Frappe Builder block"""
	block = {
		"blockId": node.get("blockId"),
		"element": node.get("element", "div"),
		"attributes": node.get("attributes", {}),
		"baseStyles": node.get("baseStyles", {}),
	}

	if "mobileStyles" in node:
		block["mobileStyles"] = node["mobileStyles"]

	if "tabletStyles" in node:
		block["tabletStyles"] = node["tabletStyles"]

	if "children" in node and node["children"]:
		block["children"] = [convert_mdk_node_to_block(child) for child in node["children"]]

	if "dataBinding" in node:
		block["dataKey"] = node["dataBinding"]

	return block


def extract_variables_from_blocks(blocks: list) -> Dict[str, Any]:
	"""Extract variable definitions from blocks"""
	variables = {}

	def extract_from_block(block):
		if "dataKey" in block:
			data_key = block["dataKey"]
			variables[data_key] = {
				"type": "text",
				"source": f"dynamic.{data_key}",
				"default": ""
			}

		if "children" in block:
			for child in block["children"]:
				extract_from_block(child)

	for block in blocks:
		extract_from_block(block)

	return variables


def extract_assets_from_page(page) -> list:
	"""Extract asset references from page"""
	assets = []

	# TODO: Parse blocks for images, fonts, etc.

	return assets


def convert_to_smarty_variables(html: str) -> str:
	"""Convert variable syntax to Smarty format"""
	import re

	# Convert {{user.name}} to {$user->_data.user_name}
	# This is a simplified conversion - real implementation would be more sophisticated

	def replacer(match):
		var_path = match.group(1)
		parts = var_path.split('.')

		# Map common variables to Sngine data structure
		if parts[0] == 'user':
			if len(parts) > 1:
				field = parts[1]
				return f"{{$user->_data.user_{field}}}"
			return "{$user->_data.user_name}"

		# Default conversion
		smarty_var = "$" + "->".join(parts)
		return f"{{{smarty_var}}}"

	html = re.sub(r'\{\{([^}]+)\}\}', replacer, html)

	return html


def validate_mdk_schema(mdk_json: Dict[str, Any]):
	"""Validate MDK JSON schema"""
	required_fields = ["version", "type", "metadata", "tree"]
	for field in required_fields:
		if field not in mdk_json:
			frappe.throw(_(f"Invalid MDK schema: missing {field}"))


def increment_version(version: str) -> str:
	"""Increment semantic version (patch level)"""
	parts = version.split('.')
	if len(parts) == 3:
		major, minor, patch = parts
		return f"{major}.{minor}.{int(patch) + 1}"
	return "1.0.1"


# ============================================================================
# Session Management
# ============================================================================

@frappe.whitelist(allow_guest=True)
def create_builder_session(token: str, project_id: str) -> Dict[str, Any]:
	"""
	Create a Builder session from Modula JWT
	Used when user clicks "Edit" in Modula

	Args:
		token: JWT from Modula
		project_id: Modula project ID

	Returns:
		Session info and redirect URL
	"""
	# Validate token
	user_info = validate_token(token)

	# Check if page exists for this project
	page_name = frappe.db.get_value("Builder Page", {"modula_project_id": project_id}, "name")

	if not page_name:
		# Create new page
		page = frappe.new_doc("Builder Page")
		page.page_title = f"Modula Project {project_id}"
		page.modula_project_id = project_id
		page.modula_build_type = user_info.get("build_type", "component")
		page.insert(ignore_permissions=True)
		page_name = page.name

	# Store token in session for subsequent API calls
	frappe.local.session.modula_token = token
	frappe.local.session.modula_project_id = project_id

	return {
		"success": True,
		"page_name": page_name,
		"redirect_url": f"/app/builder/{page_name}",
		"user_id": user_info["user_id"],
		"project_id": project_id
	}
