# Builder MCP Server

Every Builder site serves a stateless [MCP](https://modelcontextprotocol.io) endpoint at `POST /mcp`. Point Claude Code (or any MCP client) at your site to build pages, edit blocks, manage scripts and design tokens, publish, and query site data. Edits mirror live into any open editor, and each mutating call saves an automatic revert snapshot first.

No process to run and no extra dependencies: the endpoint is served by the web workers, and every request is self-contained.

## Connect with an API key

Generate an API key and secret on your user (Settings > My Settings > API Access), then:

```sh
claude mcp add --transport http builder https://yoursite.com/mcp \
  --header "Authorization: token <api_key>:<api_secret>"
```

For a local bench: `http://yoursite.localhost:8000/mcp`.

The connected user needs write access to Builder Pages (System Manager or Website Manager). Tool calls run with that user's normal Frappe permissions.

## Connect with OAuth (claude.ai connectors)

Adding the server without a header triggers the standard MCP OAuth flow: the 401 response advertises the site's protected-resource metadata, and Frappe's built-in OAuth provider handles discovery, dynamic client registration, PKCE, and consent.

- The defaults in **OAuth Settings** (metadata + dynamic client registration enabled) are all that's needed.
- claude.ai custom connectors can alternatively use a manually created **OAuth Client** doc: paste its client id/secret under the connector's advanced settings.
- Dynamic registration rejects `http://localhost` redirect URIs unless the site runs in `developer_mode` (literal loopback IPs like `127.0.0.1` are always accepted).

## Tools

Page lifecycle: `list_pages`, `create_page`, `read_page`, `duplicate_page`, `copy_page_design`, `publish_page`, `unpublish_page`, `delete_page`, `snapshot_page`, `revert_page`, `preview_page` (returns screenshots).

Block editing (every page-scoped tool takes a `page` argument): `query_blocks`, `read_block`, `update_block`, `update_blocks`, `add_block`, `remove_block`, `move_block`.

Scripts and settings: `set_page_script`, `update_script`, `get_page_scripts`, `set_page_settings`, `set_design_token`, `set_home_page`, `edit_global_settings`, `extract_component`.

Data: `list_doctypes`, `get_doctype_schema`, `query_records`, `get_document`, `write_page_data_script`, `create_doctype`, `seed_sample_data`, `connect_form`, `search_images`.

Destructive tools carry MCP annotations, so clients prompt before running them.

## Notes

- A page being edited by the in-app AI assistant is locked for the duration of that turn; MCP calls against it fail fast with a retry message.
- The `/mcp` path is reserved: a Builder Page routed `mcp` will not serve.
- The server is stateless (works with both the legacy streamable-HTTP handshake and stateless MCP clients); no session ids are issued.
