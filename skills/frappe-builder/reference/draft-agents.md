# Agents that prepare drafts for human review

Use this mode when an external agent should create pages and edit page trees, while a human controls publishing, data scripts and shared components. Frappe's built-in MCP server at `/api/v2/mcp` supplies document reads and method discovery; Builder supplies the narrow draft methods below. The built-in MCP server requires a recent Frappe v16 release (for example v16.60.2).

## Set up the agent's account

Create a dedicated System User with the **Builder Draft Editor** role. This role reads Builder pages, components, tokens, client scripts and fonts. It grants no ordinary create, write, delete or share permission on those documents. The draft methods are the account's write path.

Do not give this account Website Manager, System Manager, or other roles or shares that grant writes. Frappe combines role permissions: adding this role to an administrator does not restrict that administrator. Connect MCP with the dedicated account's credentials, separate from any server-administration credentials the agent uses elsewhere.

For ERPNext data, grant only the required read permissions and User Permissions through a separate role. Builder does not grant access to ERPNext records. Use the MCP document tools to inspect schema, list records and read permitted data.

## Draft workflow

Use `search_methods` / `get_method_schema` to discover `builder.draft_api`, then call these methods with MCP's `call_method` tool (or POST through the normal Frappe method API):

- `builder.draft_api.create_page(page_title, blocks, source_page=None)` creates an unpublished regular page at a generated route. An optional readable source page supplies its existing data script and client-script links unchanged. This reuses human-configured behavior without modifying the source or its scripts.
- `builder.draft_api.save_page(page, blocks, modified)` replaces only `draft_blocks`. Supply the original `modified` value from `get_document` or the preceding result. A stale write fails: read again and merge the human's changes. Before each accepted edit, Builder snapshots the current live and draft trees; identical snapshots may be deduplicated. Standard and template pages must first be copied to a regular page.

Both return `page`, `modified`, `snapshot` and an authenticated `preview_url`. The preview renders the draft without publishing or updating the published page's thumbnail. It runs the page's existing data and client scripts. Rendering HTML alone does not validate layout, console output or form behavior: inspect the preview with the agent's browser tools and report what was actually checked.

Ask humans to close editor tabs before an agent writes, and reload them afterwards: an open editor can autosave its old tree over the agent's draft. Reuse existing components, tokens and preconfigured data/form behavior. These methods accept no route changes, publishing flags, page data scripts or shared-document updates. Changes to that behavior belong to the human editor.

Return the preview URL for review. The human publishes from Builder using their own account. The agent must not call `publish`, `publish_to_staging`, `restore_snapshot`, general document writes or component sync. Server permissions reject those writes for the dedicated role; this is not merely an instruction to the model.
