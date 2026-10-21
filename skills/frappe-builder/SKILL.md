---
name: frappe-builder
description: Manage a website built with Frappe Builder on a Frappe site from outside the editor. Use to create or edit Builder pages, build or change Builder components (props, scripts, data), retheme a site, build data-driven or dynamic-route pages from the site's DocTypes, make forms that save, add page scripts, or publish, when the site runs the Builder app.
---

# Frappe Builder

A Builder site is a set of documents: `Builder Page` (a block tree in `blocks` = live and `draft_blocks` = draft), `Builder Component` (a block tree pages embed as instances), `Builder Token` (colour and font variables), `Builder Client Script` (page JS/CSS files) and `Builder Settings` (home page, site-wide code). Every step here is a document read or write, or a whitelisted method, so it works the same from the site's assistant, MCP or frappectl. The user needs the Website Manager role; creating a DocType (for forms) needs System Manager.

With a shell, read `reference/cli.md` first: `scripts/builder.py` in this skill's directory signs in, lints and pushes trees, builds component instances and copies pages between sites.

## 1. Edit loop

- A page's tree is `draft_blocks`, or `blocks` while the draft is empty; a component's is `block`. Each is JSON stored as a string: write the whole tree back to `draft_blocks` (or `block`) together with the `modified` value you read. If someone saved in between, the write fails instead of overwriting them: read again and merge.
- Before a page's first edit, call its `create_manual_snapshot` method with a `label`. To roll back, call `restore_snapshot` with that `Builder Snapshot`'s name: it puts the tree back into the draft.
- Ask the human to close editor tabs on the page before you write and reload them after: an open tab saves its old tree over your draft on its next edit.
- On a site that has pages, read one first and reuse its tokens, fonts, widths and components.
- Build a section from blocks on the page. Make it a component only when the same tree repeats, on this page or across pages, and no existing one fits. A component gets a prop only for what the editor can't edit on an instance or a script reads (`reference/components.md`).
- A new page: create a `Builder Page` with `page_title` and `route`.
- Preview a draft: `builder.api.get_page_preview_html` with `page` renders it with the live data script and scripts. An error there is the error visitors would get.
- Publish a page with its `publish` method; it returns the route.

Only a page's block tree has a draft; visitors see it after publish. Everything else is live when saved: a page's data script and fields, client scripts, tokens, Builder Settings, and component saves (unpinned instances change at once; `builder.api.sync_component` then rewrites the live blocks of every page that embeds the component).

Done when the preview (or the live route, for live writes) shows the change, and the human knows what is live and what is still a draft.

## 2. Traps

- **All block text, attributes, component scripts and styles, `head_html` and `canonical_url` render through Jinja.** `{{ }}` and `{% %}` are evaluated live and shown raw in the editor. `{#` fails the page unless inside `{% raw %}`; `.__` fails it even there, so move such code into a client script file.
- **A data-script exception, a missing nested binding, or a dict where a repeater wants a list 500s the page.** `reference/data-and-scripts.md`.
- **Routes shadow everything.** A Builder route wins over every other website route; a root catch-all like `/:slug` captures `/login` and the editor at `/builder`.
- **Bound values render as raw HTML.** Strip or escape visitor-submitted text in the data script.

## Reference

- `reference/blocks.md`: block JSON, styles, breakpoints, tokens, bindings, repeaters, visibility.
- `reference/data-and-scripts.md`: data scripts on both executors, dynamic routes, client scripts and load order, forms that save.
- `reference/components.md`: building components, instances and overrides, the editor sandbox, pins and sync. `examples/tabs/` is a working component.
- `reference/live-and-cached.md`: when a live change doesn't show.
- `reference/cli.md`: working from a shell: signing in, `scripts/builder.py`, local benches and tunnels.
