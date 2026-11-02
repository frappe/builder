import json

from builder.ai.agent.registry import Tool
from builder.ai.artifacts import Artifact


def read_result(ctx, args):
	_, value = Artifact.get(args["artifact_id"], ctx.page_id, "tool_result")
	text = value["text"]
	offset, limit = max(0, int(args.get("offset", 0))), max(1, min(8000, int(args.get("limit", 8000))))
	return json.dumps(
		{
			"text": text[offset : offset + limit],
			"next_offset": offset + limit if offset + limit < len(text) else None,
			"total": len(text),
		}
	)


TOOLS = [
	Tool(
		name="read_artifact",
		side="server",
		description="Read the next bounded slice of a large tool result. Use its exact artifact ID and next_offset.",
		parameters={
			"type": "object",
			"properties": {
				"artifact_id": {"type": "string"},
				"offset": {"type": "integer"},
				"limit": {"type": "integer"},
			},
			"required": ["artifact_id"],
		},
		handler=read_result,
	)
]
