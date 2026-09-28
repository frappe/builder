---
name: frappe-builder
description: Manage a website built with Frappe Builder on a Frappe site from outside the editor, through frappectl. Use to create or edit Builder pages, restyle or retheme a site, change shared header/footer components, build data-driven sections from the site's DocTypes, make forms that save, add page scripts, or publish, when the site runs the Builder app.
---

# Frappe Builder

A Builder site is a set of documents: `Builder Page` (a block tree in `blocks` = live and `draft_blocks` = unpublished draft), `Builder Component` (shared block trees), `Builder Token` (colour and font variables), `Builder Client Script` (page JS/CSS files) and `Builder Settings` (home page, site-wide code). You manage them over the REST API with `frappectl`, and edit block trees with `scripts/page.py` (in this skill's directory). The editor at `/builder` is the human's view of the same documents.

## 1. Connect

1. `frappectl --version`; if missing, `uv tool install frappectl` (or `pipx install frappectl`).
2. `frappectl auth list`. If the site has no profile, login is interactive: ask the human to run `frappectl auth login https://<site> --name <short-name>` themselves (OAuth in their browser). For CI or headless runs, `FRAPPE_SITE`, `FRAPPE_API_KEY` and `FRAPPE_API_SECRET` in the environment replace a profile.
3. `frappectl -s <profile> api method/frappe.utils.change_log.get_versions` must list `builder`. The user needs the Website Manager role; creating DocTypes (for forms) needs System Manager.

Pass `-s <profile>` on every call, frappectl and `page.py` alike; the default profile may be a different site. With the environment variables there is no profile: leave `-s` out. `frappectl doc create` and `doc update` read JSON from stdin whenever it is not a terminal, and an agent's shell leaves stdin open, so they hang: give them `--input <file>`, or `< /dev/null` when you only use `--set`.

frappectl refuses plain `http://` except for `localhost` and `*.localhost`. For a local bench site under another name, a `sites/<name>.localhost` symlink to its directory serves the API, though not its `/files`, so check pages in a browser at the site's real host.

Done when `frappectl -s <profile> auth whoami` names the user, and the versions list includes `builder`.

## 2. Orient: the site is the reference

A site's design lives in its pages, often with no tokens at all. Read before you decide anything about the look:

```sh
frappectl -s <p> doc list "Builder Page" --fields name,route,page_title,published,staging,modified --order-by "modified desc" --all
frappectl -s <p> doc get "Builder Settings" "Builder Settings"   # home_page (a route), site-wide style/script/head_html
frappectl -s <p> doc list "Builder Token" --fields name,token_name,type,value,dark_value --all
frappectl -s <p> doc list "Builder Component" --fields name,component_name --all
```

Then pull and outline the home page (or the page the human names) and take its exact font families, colours, token handles, section rhythm and header/footer components. Other apps on the site (`frappectl doctype list`) are the content source for data-driven sections: a blog, products, events and team members already live in DocTypes.

Done when you can name the site's fonts, palette, shared components, and the page you will match.

## 3. Edit loop

```sh
P=<skill-dir>/scripts/page.py
python3 $P -s <p> pull <page name | route | URL>   # .builder/<page>/{doc.json, blocks.json, data_script.py}
python3 $P outline .builder/<page>                 # blockId, element, name, classes, bindings, text
# edit blocks.json with a script (python/jq), never by retyping the tree; data_script.py by hand
python3 $P -s <p> lint .builder/<page>
python3 $P -s <p> push .builder/<page>             # lint, snapshot once, write draft_blocks (+ data script)
python3 $P -s <p> publish .builder/<page>          # only with the human's go-ahead
```

Only the block tree has a draft. The data script, page settings, attached scripts, tokens and component syncs change the live page the moment they are saved, so treat them like a publish on a live page.

- An editor tab open on the page keeps the tree it loaded, and its next edit saves that tree over your draft. Ask the human to close such tabs before you push, and to reload them after.
- Pages run to megabytes. Load `blocks.json`, change the blocks you target, write it back.
- Build every `--input` file with a short script that calls `json.dumps`. Scripts and HTML carry quotes and newlines that break hand-written JSON.
- A new page: `frappectl -s <p> doc create "Builder Page" --set page_title=... --set route=...`, then pull. It starts as `[]`; the root block shape is in `reference/blocks.md`.
- Page settings (`page_title`, `route`, `meta_description`, `meta_image`, `head_html`, `authenticated_access`) are plain fields: `frappectl doc update "Builder Page" <page> --set field=value < /dev/null`. Set them before you pull, or pull again after: any save moves the page's `modified`, and push refuses a workdir that is behind.
- Preview the draft: `frappectl -s <p> api method/builder.api.get_page_preview_html -F page=<page>` returns the rendered HTML (the data script runs too). Check that the copy you wrote is there, repeaters are filled, and there is no `{{` and no "error building this page". A human can open `/builder/page/<page>` to see it.
- After publishing, fetch `https://<site>/<route>` and check it the same way. If a live change doesn't show, read `reference/live-and-cached.md` before you change anything again.
- Roll back: the first push after each pull saves a manual snapshot labelled "Before agent edit". `frappectl doc list "Builder Snapshot" -f reference_name=<page> --order-by "creation desc"`, then `method call restore_snapshot --doctype "Builder Page" --name <page> -F snapshot=<id>` puts it back into the draft.

Lint errors in blocks you didn't change were there before you: name them to the human and push with `--force` rather than rewriting their work.

Done when lint shows no errors in what you changed, the preview or the live route shows your change, and you have told the human what changed and what is still unpublished.

## Rules the editor won't warn you about

`page.py lint` checks the mechanical rules. These need judgement:

- **Style lives on blocks**, in `baseStyles`/`tabletStyles`/`mobileStyles`, where the editor can retune it. Tokens are for colour and font only, referenced as `var(--<token doc name>)`; the `token_name` is just a label. Create a token with an explicit `name` (`{"name": "acme-ink", ...}`) so you know its handle in advance. Page CSS scripts are for interaction and motion, never a `:root` block of variables.
- **Reuse before you build.** Embed the site's header and footer components instead of rebuilding them. A change to shared chrome is an edit to the component; see `reference/components.md`.
- **Match, don't invent.** A new page on an existing site reuses the reference page's exact values. A fresh look is for an empty site or an explicit ask.
- **Pages ship still.** Add motion only when asked, or when the page you match already moves. Hover and focus transitions are fine.
- **Routes shadow.** A Builder route wins over every other website route on the site, including other apps' pages and Web Pages. Check the route is free (`doc list` plus a fetch of the URL) before you set it.
- **Site-wide writes need a yes**: publishing, the home page (`Builder Settings.home_page`), site-wide style/script, component edits, new DocTypes.
- **Never invent facts** about a real business. Take them from the site's own records or from the human.

## Reference

- `reference/blocks.md`: the raw block JSON: fields, styles, responsive, text, images, icons, raw HTML, bindings, repeaters, visibility.
- `reference/data-and-scripts.md`: page data scripts, dynamic routes, client scripts, forms that save, site-wide code.
- `reference/components.md`: component definitions, props, instances, and syncing a changed component into every page.
- `reference/live-and-cached.md`: which writes are draft and which are live, the caches between a save and a visitor, and how to tell which one is serving an old page.
