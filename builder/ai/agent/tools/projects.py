import json

from builder.ai import projects
from builder.ai.agent.registry import Tool


def read_project(ctx, args):
	return json.dumps(projects.for_page(ctx.page_id) or {"tasks": [], "revision": 0})


def update_project(ctx, args):
	return json.dumps(projects.save_project(ctx.page_id, **args))


def create_page(ctx, args):
	task = projects.create_project_page(ctx.page_id, args["task_id"])
	return json.dumps(
		{
			**task,
			"next": "Open this draft to build it. Its chat inherits the shared project brief and task map.",
		}
	)


TOOLS = [
	Tool(
		name="read_project",
		side="server",
		description="Read the durable project route/dependency map and shared brief across page chats.",
		parameters={"type": "object", "properties": {}},
		handler=read_project,
	),
	Tool(
		name="update_project",
		side="server",
		description="Save a multipage route/task plan. Read its revision first. Keep completed work and dependencies; done requires verification evidence.",
		parameters={
			"type": "object",
			"properties": {
				"title": {"type": "string"},
				"brief": {"type": "string"},
				"expected_revision": {"type": "integer"},
				"tasks": {
					"type": "array",
					"items": {
						"type": "object",
						"properties": {
							"id": {"type": "string"},
							"title": {"type": "string"},
							"route": {"type": "string"},
							"page": {"type": "string"},
							"goal": {"type": "string"},
							"status": {"type": "string", "enum": ["pending", "running", "blocked", "done"]},
							"depends_on": {"type": "array", "items": {"type": "string"}},
							"evidence": {"type": "string"},
						},
						"required": ["id", "title", "status"],
					},
				},
			},
			"required": ["title", "expected_revision", "tasks"],
		},
		handler=update_project,
		effects=("project",),
	),
	Tool(
		name="create_project_page",
		side="server",
		description="Create the draft for a planned project task exactly once; its route is checked for collisions. Returns the page ID to open and build.",
		parameters={"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]},
		handler=create_page,
		effects=("page", "project"),
	),
]
