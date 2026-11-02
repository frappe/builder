"""A persistent route and dependency map shared by the user's page chats."""

import json

import frappe

DOCTYPE = "Builder AI Project"


def validate_tasks(tasks):
	if not isinstance(tasks, list) or len(tasks) > 40:
		raise ValueError("Keep a project to at most 40 page tasks")
	ids, routes = set(), set()
	for task in tasks:
		if not isinstance(task, dict) or not task.get("id") or task["id"] in ids:
			raise ValueError("Every task needs a unique ID")
		ids.add(task["id"])
		route = str(task.get("route") or "").strip("/")
		if route and route in routes:
			raise ValueError("Project routes must be unique")
		routes.add(route)
		if task.get("status", "pending") not in ("pending", "running", "blocked", "done"):
			raise ValueError("Invalid task status")
		if task.get("status") == "done" and not task.get("evidence"):
			raise ValueError("A completed task needs its verification evidence or explicit manual acceptance")
		if page := task.get("page"):
			frappe.get_doc("Builder Page", page).check_permission("write")
		if len(json.dumps(task)) > 4000:
			raise ValueError("Keep each task under 4000 characters")
	by_id = {task["id"]: task for task in tasks}

	def visit(identity, ancestors):
		if identity in ancestors or identity not in by_id:
			raise ValueError("Tasks contain a dependency cycle or a missing dependency")
		for dependency in by_id[identity].get("depends_on", []):
			visit(dependency, {*ancestors, identity})

	for identity in ids:
		visit(identity, set())
	return tasks


def validate_project(doc):
	validate_tasks(json.loads(doc.tasks_json or "[]"))
	if len(doc.brief or "") > 8000:
		raise ValueError("Keep the shared project brief under 8000 characters")


def for_page(page_id):
	frappe.get_doc("Builder Page", page_id).check_permission("read")
	name = frappe.db.get_value("Builder Page", page_id, "ai_project")
	if not name:
		return None
	doc = frappe.get_doc(DOCTYPE, name)
	if not doc.has_permission("read"):
		return None
	return {
		"name": doc.name,
		"title": doc.title,
		"brief": doc.brief,
		"revision": doc.revision,
		"tasks": json.loads(doc.tasks_json or "[]"),
	}


@frappe.whitelist(methods=["POST"])
def save_project(
	page_id: str, title: str, brief: str = "", tasks: list | None = None, expected_revision: int = 0
):
	page = frappe.get_doc("Builder Page", page_id, for_update=True)
	page.check_permission("write")
	if page.ai_project:
		doc = frappe.get_doc(DOCTYPE, page.ai_project, for_update=True)
		doc.check_permission("write")
		if int(doc.revision or 0) != int(expected_revision):
			raise ValueError("The project changed. Read it again before updating the plan.")
	else:
		doc = frappe.new_doc(DOCTYPE)
	doc.update(
		{
			"title": title[:140],
			"brief": brief,
			"tasks_json": json.dumps(validate_tasks(tasks or [])),
			"revision": int(doc.revision or 0) + 1,
		}
	)
	doc.save()
	for linked_page in {page_id, *(task["page"] for task in tasks or [] if task.get("page"))}:
		other = frappe.get_doc("Builder Page", linked_page, for_update=True)
		other.check_permission("write")
		if other.ai_project and other.ai_project != doc.name:
			raise ValueError("One of these pages already belongs to another project")
		frappe.db.set_value("Builder Page", linked_page, "ai_project", doc.name)
	return for_page(page_id)


def create_project_page(page_id, task_id):
	project = for_page(page_id)
	if not project:
		raise ValueError("Save the project route map first")
	doc = frappe.get_doc(DOCTYPE, project["name"], for_update=True)
	doc.check_permission("write")
	tasks = json.loads(doc.tasks_json or "[]")
	task = next((item for item in tasks if item["id"] == task_id), None)
	if not task:
		raise ValueError("Task not found")
	if not task.get("page") or not frappe.db.exists("Builder Page", task["page"]):
		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": task.get("title") or task_id,
				"route": task.get("route"),
				"ai_project": doc.name,
			}
		).insert()
		task.update({"page": page.name, "status": "pending"})
		task.pop("evidence", None)
		doc.tasks_json, doc.revision = json.dumps(tasks), doc.revision + 1
		doc.save()
	return task
