---
name: frappe-builder
description: Manage a website built with Frappe Builder on a Frappe site from outside the editor, through frappectl. Use to create or edit Builder pages, build or change Builder components (props, scripts, data), retheme a site, build data-driven or dynamic-route pages from the site's DocTypes, make forms that save, add page scripts, or publish, when the site runs the Builder app.
---

# Frappe Builder

A Builder site is a set of documents: `Builder Page` (a block tree in `blocks` = live and `draft_blocks` = draft), `Builder Component` (a block tree pages embed as instances), `Builder Token` (colour and font variables), `Builder Client Script` (page JS/CSS files) and `Builder Settings` (home page, site-wide code). Manage them with `frappectl`, and edit trees with `scripts/builder.py` in this skill's directory.

## 1. Connect

1. `frappectl --version`; if missing, `uv tool install frappectl`.
2. `frappectl auth list`. If the site has no profile, ask the human to run `frappectl auth login https://<site> --name <short-name>` (it opens their browser). Headless: `FRAPPE_SITE`, `FRAPPE_API_KEY` and `FRAPPE_API_SECRET` in the environment replace a profile, and then you leave `-s` out.
3. `frappectl -s <p> api method/frappe.utils.change_log.get_versions` must list `builder`. The user needs the Website Manager role; creating a DocType (for forms) needs System Manager.

No site yet? Install bench's prerequisites ([docs](https://docs.frappe.io/framework/user/en/installation)); the `frappe-app-dev` skill (`npx skills add frappe/skills --skill frappe-app-dev`) covers bench and site basics. Local setups use the `develop` branch of both Frappe and Builder:

```sh
bench init --frappe-branch develop frappe-bench && cd frappe-bench   # or reuse a bench on develop
bench get-app builder --branch develop
bench new-site <name>.localhost --admin-password admin --install-app builder
bench --site <name>.localhost execute frappe.core.doctype.user.user.generate_keys --args '["Administrator"]'
export FRAPPE_SITE=http://<name>.localhost:8000 FRAPPE_API_KEY=<api_key> FRAPPE_API_SECRET=<api_secret>
```

With `bench start` running, the editor is at `http://<name>.localhost:8000/builder` (Administrator / admin).

- `frappectl doc create` and `doc update` read stdin whenever it isn't a terminal, and hang in an agent's shell: pass `--input <file>`, or `< /dev/null` with `--set`.
- frappectl refuses plain `http://` except for `localhost` and `*.localhost`. For a local bench site under another name, a `sites/<name>.localhost` symlink to its folder serves the API but not its `/files`; check pages in a browser at the site's real host.

## 2. Edit loop

```sh
B=<skill-dir>/scripts/builder.py
python3 $B -s <p> pull <page name | route | URL | component/<id>>   # .builder/<name>/
python3 $B outline .builder/<name>
# edit blocks.json (block.json for a component) with a script, data_script.py by hand
python3 $B -s <p> lint .builder/<name>
python3 $B -s <p> push .builder/<name>
python3 $B -s <p> publish .builder/<name>                  # pages
python3 $B -s <p> create <id> --from <folder with block.json> # new component
python3 $B -s <p> instance <component-id> --props '{...}'   # embed JSON to paste into a page
python3 $B -s <p> usage <component-id>
python3 $B -s <p> sync <component-id>
```

Only a page's block tree has a draft; visitors see it after publish. Everything else is live when saved: a page's data script and fields, client scripts, tokens, Builder Settings, and component saves (unpinned instances change at once; `sync` then rewrites the live blocks of every page that embeds the component).

- Close editor tabs on the page before you push, and reload them after: an open tab saves its old tree over your draft on its next edit.
- Build `--input` files with `json.dumps`, never by hand.
- A new page: `doc create "Builder Page" --set page_title=... --set route=... < /dev/null`, then pull. Page fields (`page_title`, `route`, `meta_description`, `meta_image`, `head_html`, `canonical_url`, `authenticated_access`) are set with `doc update --set` before you pull; push refuses a workdir that is behind.
- Preview a draft: `frappectl -s <p> api method/builder.api.get_page_preview_html -F page=<page>` renders it with the live data script and scripts. An error there is the error visitors would get.
- Roll back a page: the first push after a pull saves a snapshot labelled "Before agent edit"; `method call restore_snapshot --doctype "Builder Page" --name <page> -F snapshot=<id>` restores it into the draft. Roll back a component by pushing the `doc.json` you pulled.
- Lint errors in blocks you didn't touch: report them and push with `--force`.

Done when lint is clean for what you changed, the preview (or the live route, for live writes) shows it, and the human knows what is live and what is still a draft.

## 3. Traps

- **All block text, attributes, component scripts and styles, `head_html` and `canonical_url` render through Jinja.** `{{ }}` and `{% %}` are evaluated live and shown raw in the editor. `{#` fails the page unless inside `{% raw %}`; `.__` fails it even there, so move such code into a client script file.
- **A data-script exception, a missing nested binding, or a dict where a repeater wants a list 500s the page.** `reference/data-and-scripts.md`.
- **Routes shadow everything.** A Builder route wins over every other website route; a root catch-all like `/:slug` captures `/login` and the editor at `/builder`. Route variables are `[A-Za-z0-9_]` only: one hyphenated variable breaks every dynamic page published before it.
- **Bound values render as raw HTML.** Strip or escape visitor-submitted text in the data script.
- **Style key order is not kept.** Sync and snapshot restore sort every page's style keys, so a shorthand with its own longhand (`borderWidth` with `borderLeft`) flips. Use longhands.

## Reference

- `reference/blocks.md`: block JSON, styles, breakpoints, tokens, bindings, repeaters, visibility.
- `reference/data-and-scripts.md`: data scripts on both executors, dynamic routes, client scripts and load order, forms that save.
- `reference/components.md`: building components, instances and overrides, the editor sandbox, pins and sync. `examples/tabs/` is a working component.
- `reference/live-and-cached.md`: when a live change doesn't show.
