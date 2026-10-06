#!/usr/bin/env python3
"""Pull, lint, push and publish Frappe Builder pages and components through frappectl.

    builder.py connect <site URL | profile> [--bench DIR]
    builder.py [-s PROFILE] pull <page name | route | URL | component/<id>> [--dir .builder]
    builder.py outline <workdir | json file>
    builder.py [-s PROFILE] lint <workdir | json file>
    builder.py [-s PROFILE] push <workdir> [--force]
    builder.py [-s PROFILE] publish <workdir>
    builder.py [-s PROFILE] sync <component id>
    builder.py [-s PROFILE] usage <component id>
    builder.py [-s PROFILE] instance <component id> [--props JSON]
    builder.py [-s PROFILE] copy <page> --to PROFILE [--replace]

A page workdir holds doc.json (the page as pulled, the rollback), blocks.json (the
working tree) and data_script.py. push writes draft_blocks, and page_data_script
when it changed; visitors see the blocks when the page is published.

A component workdir holds doc.json, block.json (the definition root) and
data_script.py. push saves the component, which is live at once for every
unpinned instance; sync then adds refs for new blocks and re-pins every instance.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from lint import Block, Linter
from transfer import SiteCopy
from tree import InstanceBuilder, block_ids, parse_blocks, walk


class Frappectl:
	def __init__(self, profile: str | None):
		self.profile = profile
		self.base = ["frappectl", *(["-s", profile] if profile else []), "--json"]

	def run(self, *args: str, hint: str = "", check: bool = True) -> object:
		result = subprocess.run([*self.base, *args], capture_output=True, text=True, stdin=subprocess.DEVNULL)
		if result.returncode and not check:
			return False
		if result.returncode:
			message = result.stderr.strip() or f"frappectl {args[0]} failed"
			sys.exit(f"{message}\n{hint}" if hint else message)
		return json.loads(result.stdout) if result.stdout.strip() else None

	def run_input(self, data: dict, *args: str, hint: str = "") -> object:
		# closed before frappectl opens it: Windows refuses a second open of a temp file
		fd, path = tempfile.mkstemp(suffix=".json")
		try:
			with os.fdopen(fd, "w") as handle:
				json.dump(data, handle)
			return self.run(*args, "--input", path, hint=hint)
		finally:
			os.unlink(path)

	def get(self, doctype: str, name: str) -> dict:
		return self.run("doc", "get", doctype, name)

	def names(self, doctype: str, *filters: str, fields: str = "name") -> list[dict]:
		flags = [part for f in filters for part in ("-f", f)]
		return self.run("doc", "list", doctype, *flags, "--fields", fields, "--all")

	def find_page(self, ref: str) -> str:
		route = (urlparse(ref).path.strip("/") if "://" in ref else ref.strip("/")) or self.home_route()
		for filters in (f"name={ref}", f"route={route}"):
			if pages := self.names("Builder Page", filters):
				return pages[0]["name"]
		sys.exit(f"No Builder Page with name or route '{ref}'")

	def home_route(self) -> str:
		home = self.get("Builder Settings", "Builder Settings").get("home_page")
		if not home:
			sys.exit("The site has no Builder home page (Builder Settings.home_page)")
		return home.strip("/")

	def embedding_pages(self, component_id: str) -> list[dict]:
		pages = {}
		for field in ("blocks", "draft_blocks"):
			for row in self.names(
				"Builder Page", f"{field} like %{component_id}%", fields="name,route,published"
			):
				pages[row["name"]] = row
		return list(pages.values())

	def definition(self, component_id: str) -> dict:
		return json.loads(self.get("Builder Component", component_id).get("block") or "{}")


class Target:
	"""What a workdir edits: a page's draft tree or a component definition."""

	doctype = ""
	tree_file = ""
	script_field = ""

	def __init__(self, workdir: Path):
		self.workdir = workdir
		self.doc_path = workdir / "doc.json"

	@staticmethod
	def of(workdir: Path) -> Target:
		doc = json.loads((workdir / "doc.json").read_text())
		return ComponentTarget(workdir) if doc.get("doctype") == "Builder Component" else PageTarget(workdir)

	@property
	def doc(self) -> dict:
		return json.loads(self.doc_path.read_text())

	@property
	def tree_path(self) -> Path:
		return self.workdir / self.tree_file

	@property
	def script_path(self) -> Path:
		return self.workdir / "data_script.py"

	def write(self, doc: dict):
		self.workdir.mkdir(parents=True, exist_ok=True)
		self.doc_path.write_text(json.dumps(doc, indent=1))
		self.tree_path.write_text(json.dumps(self.site_tree(doc), indent=1))
		self.script_path.write_text(doc.get(self.script_field) or "")

	def script_changed(self, doc: dict) -> bool:
		return self.script_path.exists() and self.script_path.read_text() != (
			doc.get(self.script_field) or ""
		)

	def has_unpushed_edits(self) -> bool:
		if not self.doc_path.exists() or not self.tree_path.exists():
			return False
		doc = self.doc
		return self.script_changed(doc) or self.local_tree() != self.site_tree(doc)

	def update(self) -> dict:
		doc = self.doc
		update = {self.tree_field(): self.encode_tree(), "modified": doc["modified"]}
		if self.script_changed(doc):
			update[self.script_field] = self.script_path.read_text()
		return update

	def encode_tree(self) -> str:
		return json.dumps(self.local_tree(), separators=(",", ":"))

	def refresh(self, ctl: Frappectl):
		doc = self.doc
		fresh = ctl.get(self.doctype, doc["name"])
		fresh["_snapshot"] = doc.get("_snapshot")
		self.doc_path.write_text(json.dumps(fresh, indent=1))


class PageTarget(Target):
	doctype = "Builder Page"
	tree_file = "blocks.json"
	script_field = "page_data_script"
	kind = "page"

	def site_tree(self, doc: dict) -> list:
		return parse_blocks(doc.get("draft_blocks")) or parse_blocks(doc.get("blocks"))

	def local_tree(self) -> list:
		return parse_blocks(self.tree_path.read_text())

	def tree_field(self) -> str:
		return "draft_blocks"


class ComponentTarget(Target):
	doctype = "Builder Component"
	tree_file = "block.json"
	script_field = "component_data_script"
	kind = "component"

	def site_tree(self, doc: dict) -> dict:
		return json.loads(doc.get("block") or "{}")

	def local_tree(self) -> dict:
		return json.loads(self.tree_path.read_text())

	def tree_field(self) -> str:
		return "block"


def tree_file(target: str) -> Path:
	path = Path(target)
	if not path.is_dir():
		return path
	return path / ("block.json" if (path / "block.json").exists() else "blocks.json")


def roots_of(path: Path) -> list:
	return parse_blocks(path.read_text())


def cmd_pull(ctl: Frappectl, args):
	if args.ref.startswith("component/"):
		component_id = args.ref.split("/", 1)[1]
		doc = ctl.get("Builder Component", component_id)
		target = ComponentTarget(Path(args.dir) / f"component-{component_id}")
	else:
		doc = ctl.get("Builder Page", ctl.find_page(args.ref))
		target = PageTarget(Path(args.dir) / doc["name"])
	if target.has_unpushed_edits():
		sys.exit(f"{target.workdir} has edits you haven't pushed; push them, or pull into another --dir")
	target.write(doc)
	if target.kind == "component":
		pages = ctl.embedding_pages(doc["name"])
		print(f"{target.workdir}  component {doc['name']}  embedded on {len(pages)} page(s)")
		return
	state = "published" if doc.get("published") else "staging" if doc.get("staging") else "unpublished"
	source = "draft_blocks" if parse_blocks(doc.get("draft_blocks")) else "blocks"
	print(f"{target.workdir}  route=/{doc.get('route')}  {state}  working tree from {source}")
	if source == "draft_blocks" and parse_blocks(doc.get("blocks")) != parse_blocks(doc["draft_blocks"]):
		print("note: the page has unpublished edits; publishing ships them together with yours")


def cmd_create(ctl: Frappectl, args):
	source = Path(args.source)
	block_path, script_path = source / "block.json", source / "data_script.py"
	if lint(ctl, block_path) and not args.force:
		sys.exit("lint errors: fix them, or pass --force")
	if ctl.names("Builder Component", f"name={args.component}"):
		sys.exit(f"component {args.component} exists; pull component/{args.component} and push instead")
	doc = {
		"name": args.component,
		"component_id": args.component,
		"component_name": args.name or args.component,
		"block": json.dumps(json.loads(block_path.read_text()), separators=(",", ":")),
	}
	if script_path.exists():
		doc["component_data_script"] = script_path.read_text()
	created = ctl.run_input(doc, "doc", "create", "Builder Component")
	target = ComponentTarget(Path(args.dir) / f"component-{created['name']}")
	target.write(created)
	print(f"created component {created['name']}; workdir {target.workdir}")


def print_outline(block: Block, depth: int = 0):
	element = block.element or ("ref" if block.referenceBlockId else "?")
	parts = [f"{'  ' * depth}{block.blockId or '-'} {element}"]
	if block.blockName:
		parts.append(f"'{block.blockName}'")
	if block.classes:
		parts.append("." + ".".join(block.classes if isinstance(block.classes, list) else [block.classes]))
	if block.extendedFromComponent:
		parts.append(f"[component {block.extendedFromComponent}]")
	if block.referenceBlockId:
		parts.append(f"[of {block.referenceBlockId}]")
	if block.isRepeaterBlock:
		parts.append(f"[repeat {(block.dataKey or {}).get('key') or 'from definition'}]")
	if bound := [f"{b.get('property')}<-{b.get('key')}" for b in block.bindings() if b.get("property")]:
		parts.append("[bind " + ", ".join(bound) + "]")
	if block.props:
		parts.append("[props " + ", ".join(block.props) + "]")
	if block.script():
		parts.append("[script]")
	text = " ".join((block.innerHTML or "").split())
	if text:
		parts.append(repr(text[:60]))
	print(" ".join(parts))
	for child in block.children:
		print_outline(child, depth + 1)


def cmd_outline(target: str):
	for index, root in enumerate(roots_of(tree_file(target))):
		print_outline(Block(root, str(index)))


def used_components(roots: list) -> set[str]:
	found = set()
	walk(roots, lambda node: node.get("referenceBlockId") or found.add(node.get("extendedFromComponent")))
	return found - {None}


def site_names(ctl: Frappectl | None, doctype: str) -> set[str] | None:
	return {row["name"] for row in ctl.names(doctype)} if ctl else None


def lint(ctl: Frappectl | None, path: Path) -> int:
	kind = "component" if path.name == "block.json" else "page"
	roots, components = roots_of(path), site_names(ctl, "Builder Component")
	definitions = {cid: ctl.definition(cid) for cid in used_components(roots) & (components or set())}
	linter = Linter(roots, site_names(ctl, "Builder Token"), components, kind, definitions)
	issues = linter.run()
	for level, where, message in issues:
		print(f"{level:5} {where}: {message}")
	errors = sum(1 for level, _, _ in issues if level == "error")
	print(f"{errors} errors, {len(issues) - errors} warnings")
	return errors


def snapshot_page(ctl: Frappectl, target: Target):
	doc = target.doc
	if target.kind == "page" and not doc.get("_snapshot"):
		ctl.run(
			"method", "call", "create_manual_snapshot", "--doctype", "Builder Page",
			"--name", doc["name"], "-F", "label=Before agent edit",
		)  # fmt: skip
		doc["_snapshot"] = True
		target.doc_path.write_text(json.dumps(doc, indent=1))


def removed_block_ids(target: Target) -> set[str]:
	if target.kind != "component":
		return set()
	return block_ids(target.site_tree(target.doc)) - block_ids(target.local_tree())


def cmd_push(ctl: Frappectl, args):
	target = Target.of(Path(args.workdir))
	if lint(ctl, target.tree_path) and not args.force:
		sys.exit("lint errors: fix them, or pass --force")
	if (removed := removed_block_ids(target)) and not args.force:
		sys.exit(
			f"the definition drops block ids {sorted(removed)}; every instance's skeleton points at them."
			" Keep ids when you edit, or pass --force if the blocks are really gone"
		)
	snapshot_page(ctl, target)
	update = target.update()
	ctl.run_input(
		update, "doc", "update", target.doctype, target.doc["name"],
		hint="Someone saved it after your pull: pull into another --dir, merge, push from there.",
	)  # fmt: skip
	target.refresh(ctl)
	if rewritten := rewritten_blocks(target, update):
		sys.exit(
			f"the site rewrote blocks on save ({', '.join(rewritten[:5])}), so the saved draft is not what"
			" you sent. Builder before v1.33 sanitises raw HTML and attributes on save. Restore the"
			" 'Before agent edit' snapshot (see SKILL.md) and update Builder before pushing again."
		)
	report_push(ctl, target, update)


def rewritten_blocks(target: Target, update: dict) -> list[str]:
	sent = json.loads(update[target.tree_field()])
	try:
		saved = target.site_tree(target.doc)
	except ValueError:
		return ["all of them: the saved tree is no longer valid JSON"]
	if sent == saved:
		return []
	before, after = blocks_by_id(sent), blocks_by_id(saved)
	return [block_id for block_id in before if before[block_id] != after.get(block_id)] or ["tree"]


def blocks_by_id(tree) -> dict:
	found = {}
	walk(tree, lambda node: found.setdefault(str(node.get("blockId")), {**node, "children": None}))
	return found


def report_push(ctl: Frappectl, target: Target, update: dict):
	name = target.doc["name"]
	if target.kind == "page":
		print(f"draft saved on {name}; visitors see the blocks after publish")
		if target.script_field in update:
			print("page_data_script has no draft: the live page runs the new script already")
		return
	pages = ctl.embedding_pages(name)
	print(f"component {name} saved and live for unpinned instances on {len(pages)} page(s):")
	for page in pages:
		print(f"  {page['name']}  /{page.get('route')}  {'published' if page.get('published') else 'draft'}")
	print(f"run `sync {name}` to add refs for new blocks and re-pin editor-dropped instances")


def cmd_publish(ctl: Frappectl, args):
	target = Target.of(Path(args.workdir))
	if target.kind != "page":
		sys.exit("components have no publish step; push saves them live")
	doc = target.doc
	if (
		target.local_tree() != target.site_tree(ctl.get("Builder Page", doc["name"]))
		or target.has_unpushed_edits()
	):
		sys.exit(
			"The page's draft differs from this workdir: push your edits, or pull to review"
			" someone else's, before you publish"
		)
	route = ctl.run("method", "call", "publish", "--doctype", "Builder Page", "--name", doc["name"])
	target.refresh(ctl)
	print(f"published {doc['name']} at /{route}")


def cmd_sync(ctl: Frappectl, args):
	ctl.run("method", "call", "builder.api.sync_component", "-F", f"component_id={args.component}")
	print(
		f"synced {args.component} on {len(ctl.embedding_pages(args.component))} page(s), live blocks included"
	)


def cmd_connect(ctl: Frappectl, args):
	ensure_frappectl()
	update_skill()
	ctl = Frappectl(args.site or profile_for(args.target))
	who = ctl.run("auth", "whoami")
	print(f"connected to {who['site']} as {who['user']}; use -s {who['source']}")
	if who.get("read_only"):
		print(
			f"the profile is read-only: ask the human to run `frappectl auth configure {who['source']} --writable`"
		)
	versions = ctl.run("api", "method/frappe.utils.change_log.get_versions")
	if "builder" not in versions:
		sys.exit("Builder is not installed on this site")
	print(f"Builder {versions['builder']['version']}, Frappe {versions['frappe']['version']}")
	if too_old(versions["builder"]["version"]):
		print("this skill expects Builder v1.35 or later: ask the human to update Builder on the site")
	if args.bench:
		update_bench(Path(args.bench))


def read_terminal(fd: int) -> bytes:
	try:
		return os.read(fd, 1024)
	except OSError:  # the terminal closed when frappectl exited
		return b""


def profile_for(target: str | None) -> str | None:
	if not target:
		return None
	profiles = Frappectl(None).run("auth", "list", check=False) or []
	for profile in profiles:
		if target.rstrip("/") in (profile["profile"], profile["site"].rstrip("/")):
			return profile["profile"]
	if "://" not in target:
		sys.exit(f"no frappectl profile '{target}'; pass the site URL to sign in")
	return login(target.rstrip("/"))


def login(site: str) -> str:
	name = urlparse(site).hostname
	command = [
		"frappectl",
		"auth",
		"login",
		site,
		"--name",
		name,
		"--description",
		"",
		"--oauth",
		"--writable",
	]
	if os.name != "posix":
		sys.exit(f"ask the human to run this in a terminal, then connect again: {shlex.join(command)}")
	import pty

	print("signing in: the human approves it in the browser tab that opens", flush=True)
	# frappectl insists on a terminal even when the flags answer every prompt; pty.spawn
	# would hang on macOS before Python 3.10 once frappectl exits, so relay output by hand
	controller, terminal = pty.openpty()
	process = subprocess.Popen(command, stdin=terminal, stdout=terminal, stderr=terminal)
	os.close(terminal)
	while chunk := read_terminal(controller):
		sys.stdout.write(chunk.decode(errors="replace"))
		sys.stdout.flush()
	os.close(controller)
	if process.wait():
		sys.exit("sign-in did not complete")
	return name


def ensure_frappectl():
	# a frappectl too old for --writable can't sign in the way login does
	if shutil.which("frappectl") and "--writable" in run_text("frappectl", "auth", "login", "--help"):
		return
	if not shutil.which("uv"):
		sys.exit("install uv (https://docs.astral.sh/uv/getting-started/installation/), then connect again")
	action = "upgrade" if shutil.which("frappectl") else "install"
	result = subprocess.run(
		["uv", "tool", action, "frappectl"], capture_output=True, text=True, stdin=subprocess.DEVNULL
	)
	if result.returncode:
		sys.exit(result.stderr.strip() or f"uv tool {action} frappectl failed")
	if not shutil.which("frappectl"):
		sys.exit(
			"frappectl is installed but not on PATH: run `uv tool update-shell`, then connect again in a new shell"
		)


def update_skill():
	if not shutil.which("npx"):
		print("npx is missing, so the frappe-builder skill was not checked for updates")
		return
	skill = Path(__file__).parent.parent
	before = (skill / "SKILL.md").read_bytes()
	lock = next((d for d in list(skill.parents)[:4] if (d / "skills-lock.json").exists()), None)
	subprocess.run(
		["npx", "-y", "skills", "update", "frappe-builder", "-y", *([] if lock else ["-g"])],
		cwd=lock, capture_output=True, stdin=subprocess.DEVNULL,
	)  # fmt: skip
	if (skill / "SKILL.md").read_bytes() != before:
		print("the frappe-builder skill was updated: read SKILL.md again before going on")


def run_text(*command: str) -> str:
	return subprocess.run(command, capture_output=True, text=True, stdin=subprocess.DEVNULL).stdout


def too_old(version: str) -> bool:
	if "dev" in version:
		return False
	return tuple(int(n) for n in re.findall(r"\d+", version)[:2]) < (1, 35)


def update_bench(bench: Path):
	"""Pulls Frappe and Builder when their checkouts track develop untouched."""
	behind = []
	for app in ("frappe", "builder"):
		git = GitCheckout(bench / "apps" / app)
		if git.branch() != "develop" or git.dirty():
			print(f"{app}: on {git.branch()}{' with local changes' if git.dirty() else ''}, left as is")
		elif count := git.behind():
			behind.append(app)
			print(f"{app}: {count} commits behind develop")
	if behind:
		print("updating with bench update (backs up and migrates every site on the bench)", flush=True)
		subprocess.run(
			["bench", "update", "--pull", "--requirements", "--patch", "--build", "--apps", ",".join(behind)],
			cwd=bench, stdin=subprocess.DEVNULL,
		)  # fmt: skip


class GitCheckout:
	def __init__(self, path: Path):
		self.path = path

	def git(self, *args: str) -> str:
		return subprocess.run(
			["git", "-C", str(self.path), *args], capture_output=True, text=True
		).stdout.strip()

	def branch(self) -> str:
		return self.git("branch", "--show-current")

	def dirty(self) -> bool:
		return bool(self.git("status", "--porcelain", "--untracked-files=no"))

	def behind(self) -> int:
		remote = "upstream" if "upstream" in self.git("remote").split() else "origin"
		self.git("fetch", "-q", remote, "develop")
		return int(self.git("rev-list", "--count", "HEAD..FETCH_HEAD") or 0)


def cmd_copy(ctl: Frappectl, args):
	SiteCopy(ctl, Frappectl(args.to), replace=args.replace).page(ctl.find_page(args.ref))


def cmd_usage(ctl: Frappectl, args):
	for page in ctl.embedding_pages(args.component):
		print(f"{page['name']}  /{page.get('route')}  {'published' if page.get('published') else 'draft'}")


def cmd_instance(ctl: Frappectl, args):
	props = json.loads(args.props) if args.props else None
	try:
		print(json.dumps(InstanceBuilder(ctl.definition).build(args.component, props), indent=1))
	except KeyError as error:
		sys.exit(str(error))


def main():
	parser = argparse.ArgumentParser(
		description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
	)
	parser.add_argument("-s", "--site", help="frappectl profile")
	sub = parser.add_subparsers(dest="command", required=True)
	pull = sub.add_parser("pull")
	pull.add_argument("ref")
	pull.add_argument("--dir", default=".builder")
	sub.add_parser("outline").add_argument("target")
	sub.add_parser("lint").add_argument("target")
	push = sub.add_parser("push")
	push.add_argument("workdir")
	push.add_argument("--force", action="store_true", help="push despite lint errors or dropped block ids")
	sub.add_parser("publish").add_argument("workdir")
	sub.add_parser("sync").add_argument("component")
	sub.add_parser("usage").add_argument("component")
	create = sub.add_parser("create")
	create.add_argument("component")
	create.add_argument(
		"--from", dest="source", required=True, help="folder with block.json and data_script.py"
	)
	create.add_argument("--name", help="component label")
	create.add_argument("--dir", default=".builder")
	create.add_argument("--force", action="store_true", help="create despite lint errors")
	connect = sub.add_parser("connect")
	connect.add_argument("target", nargs="?", help="site URL or frappectl profile")
	connect.add_argument("--bench", help="local bench folder: pull Frappe and Builder there when behind")
	copy = sub.add_parser("copy")
	copy.add_argument("ref")
	copy.add_argument("--to", required=True, help="frappectl profile of the site to copy into")
	copy.add_argument(
		"--replace",
		action="store_true",
		help="overwrite what differs there, including the live page fields and another user's draft",
	)
	instance = sub.add_parser("instance")
	instance.add_argument("component")
	instance.add_argument("--props", help="JSON object of prop values")
	args = parser.parse_args()

	if args.command == "outline":
		return cmd_outline(args.target)
	ctl = Frappectl(args.site)
	if args.command == "lint":
		site_aware = args.site or os.environ.get("FRAPPE_SITE")
		sys.exit(1 if lint(ctl if site_aware else None, tree_file(args.target)) else 0)
	commands = {
		"pull": cmd_pull,
		"push": cmd_push,
		"publish": cmd_publish,
		"sync": cmd_sync,
		"usage": cmd_usage,
		"instance": cmd_instance,
		"create": cmd_create,
		"copy": cmd_copy,
		"connect": cmd_connect,
	}
	return commands[args.command](ctl, args)


if __name__ == "__main__":
	main()
