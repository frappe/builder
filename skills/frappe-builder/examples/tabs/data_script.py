# ruff: noqa: F821  (props, component and json are injected by Builder)
rows = props.get("rows") or []
if isinstance(rows, str):
	rows = json.loads(rows)
tabs = []
for raw in rows:
	parts = [part.strip() for part in str(raw).split("|", 1)]
	tabs.append({"label": parts[0], "body": parts[1] if len(parts) > 1 else ""})
component.tabs = tabs
component.component_data = {"count": len(tabs)}
