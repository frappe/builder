---
name: frappe-builder
description: Manage a website built with Frappe Builder on a Frappe site from outside the editor, through frappectl. Use to create or edit Builder pages, build or change Builder components (props, scripts, data), retheme a site, build data-driven or dynamic-route pages from the site's DocTypes, make forms that save, add page scripts, or publish, when the site runs the Builder app.
---

# Frappe Builder

A Builder site is a set of documents: `Builder Page` (a block tree in `blocks` = live and `draft_blocks` = draft), `Builder Component` (a block tree pages embed as instances), `Builder Token` (colour and font variables), `Builder Client Script` (page JS/CSS files) and `Builder Settings` (home page, site-wide code). Manage them with `frappectl`, and edit trees with `scripts/builder.py` in this skill's directory.

## 1. Connect

Start each session with `python3 <skill-dir>/scripts/builder.py connect <site URL or profile> [--bench <bench dir>]` and pass the profile it prints as `-s <p>`. It installs frappectl if needed, updates this skill (read this file again if it says so), signs in through the human's browser when the site has no profile (they click Allow), and warns when the site's Builder is too old. With `--bench` it also pulls a local bench's Frappe and Builder when they sit untouched on `develop`. The user needs the Website Manager role; creating a DocType (for forms) needs System Manager.

No site yet? Local setups run Frappe and Builder on `develop`; the `frappe-app-dev` skill (`npx skills add frappe/skills --skill frappe-app-dev`) covers bench basics. `bench find ~` lists existing benches: if one runs Frappe 16 or later, ask the human whether to reuse it, which skips the slow `bench init`.

```sh
bench init --frappe-branch develop frappe-bench && cd frappe-bench   # new bench only
bench get-app builder --branch develop                               # if apps/builder is missing
bench new-site <name>.localhost --admin-password admin --install-app builder
bench start   # not `bench serve` alone: publishing queues jobs that need its worker
```

Then `connect http://<name>.localhost:8000 --bench <bench dir>`; the human logs in as Administrator / admin before allowing. If `sites/common_site_config.json` sets `default_site`, bench serves only that site to every host; `bench use <name>.localhost` switches it.

Once it works, offer to share the site through a tunnel. It lives only while their machine and `bench start` run; Frappe Cloud is the permanent option. If they want it, set it up without more questions:

```sh
bench --site <site> set-admin-password <generated>    # the site becomes public; show the password once
cloudflared tunnel --url http://localhost:8000 --http-host-header <site>   # or: ngrok http 8000 --host-header=<site>
bench --site <site> set-config host_name https://<tunnel-host>:443   # :443, or developer mode appends :8000
bench --site <site> set-config host_name None          # once the tunnel is closed
```

- `frappectl doc create` and `doc update` read stdin whenever it isn't a terminal, and hang in an agent's shell: pass `--input <file>`, or `< /dev/null` with `--set`.
- frappectl refuses plain `http://` except for `localhost` and `*.localhost`.
- With no browser, `FRAPPE_SITE`, `FRAPPE_API_KEY` and `FRAPPE_API_SECRET` replace a profile; set them on each command rather than exporting them, since bench reads `FRAPPE_SITE` as its site.

## 2. Edit loop

```sh
B=<skill-dir>/scripts/builder.py
python3 $B -s <p> pull <page name | route | URL | component/<id>>   # .builder/<name>/
python3 $B outline .builder/<name>
# edit blocks.json (block.json for a component) with a script, data_script.py by hand
python3 $B -s <p> push .builder/<name>                     # lints first; refuses on errors
python3 $B -s <p> publish .builder/<name>                  # pages
python3 $B -s <p> create <id> --from <folder with block.json> # new component
python3 $B -s <p> instance <component-id> [--props JSON] [--overrides JSON]  # embed JSON to paste into a page
python3 $B -s <p> usage <component-id>
python3 $B -s <p> sync <component-id>
python3 $B -s <p> copy <page> --to <other profile>             # with its components, scripts, tokens, fonts, files
```

Only a page's block tree has a draft; visitors see it after publish. Everything else is live when saved: a page's data script and fields, client scripts, tokens, Builder Settings, and component saves (unpinned instances change at once; `sync` then rewrites the live blocks of every page that embeds the component).

- Ask the human to close editor tabs on the page before you push and reload them after: an open tab saves its old tree over your draft on its next edit.
- On a site that has pages, pull one first and reuse its tokens, fonts, widths and components.
- Build a section from blocks on the page. Make it a component only when the same tree repeats, on this page or across pages, and no existing one fits. A component gets props only for what editing its instances in place can't do (`reference/components.md`); lint warns on the rest.
- A new page: `doc create "Builder Page" --set page_title=... --set route=... < /dev/null`, then pull. Set page fields with `doc update --set` before you pull; push refuses a workdir that is behind.
- Preview a draft: `frappectl -s <p> api method/builder.api.get_page_preview_html -F page=<page>` renders it with the live data script and scripts. An error there is the error visitors would get.
- Roll back a page: the first push after a pull saves a snapshot labelled "Before agent edit"; `method call restore_snapshot --doctype "Builder Page" --name <page> -F snapshot=<id>` restores it into the draft. Roll back a component by pushing the `doc.json` you pulled.
- Lint errors in blocks you didn't touch: report them and push with `--force`.

Done when push reports no lint errors in what you changed, the preview (or the live route, for live writes) shows it, and the human knows what is live and what is still a draft.

## 3. Traps

- **All block text, attributes, component scripts and styles, `head_html` and `canonical_url` render through Jinja.** `{{ }}` and `{% %}` are evaluated live and shown raw in the editor. `{#` fails the page unless inside `{% raw %}`; `.__` fails it even there, so move such code into a client script file.
- **A data-script exception, a missing nested binding, or a dict where a repeater wants a list 500s the page.** `reference/data-and-scripts.md`.
- **Routes shadow everything.** A Builder route wins over every other website route; a root catch-all like `/:slug` captures `/login` and the editor at `/builder`.
- **Bound values render as raw HTML.** Strip or escape visitor-submitted text in the data script.

## Reference

- `reference/blocks.md`: block JSON, styles, breakpoints, tokens, bindings, repeaters, visibility.
- `reference/data-and-scripts.md`: data scripts on both executors, dynamic routes, client scripts and load order, forms that save.
- `reference/components.md`: building components, instances and overrides, the editor sandbox, pins and sync. `examples/tabs/` is a working component.
- `reference/live-and-cached.md`: when a live change doesn't show.
