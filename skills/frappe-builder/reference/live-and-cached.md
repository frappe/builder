# What is live, and what can serve a stale copy

A change that "didn't take" is almost always one of two things: it went to a place that isn't live yet, or it is live and a cache is still serving the old copy. Work out which before you change anything again.

## Draft or live

| You saved | Where it lands | Visitors see it |
|---|---|---|
| Blocks, via `page.py push` | `draft_blocks` | After publish |
| Blocks, via publish | `blocks` | Now, cache cleared |
| `page_data_script` | Live field | Now (pages with a data script are never cached) |
| Page fields (`page_title`, `meta_*`, `head_html`, `client_scripts`) | Live fields | Now, but see the page cache below |
| A `Builder Client Script` | Live file, new `?v=` URL | Now, but see the page cache below |
| A `Builder Token` | Live, `tokens.css` rebuilt | Now |
| A `Builder Component` | Live definition | Unpinned instances now (after a background job clears their pages); pinned ones after `sync_component` |
| `Builder Settings` style or script | Live file, new `?v=` URL | Now, but see the page cache below |
| `Builder Settings.home_page` | Live | Now |

The preview (`builder.api.get_page_preview_html`) renders `draft_blocks` with the live data script, scripts and tokens, uncached. It shows what publishing would ship, not what visitors see today.

## The caches

1. **Rendered page HTML**, 30 minutes, in Redis, keyed by path. Skipped for pages with a data script, dynamic routes, requests with a query string, and sites in developer mode, which is why a local bench never shows it. It is cleared only when a page's blocks, route or publish state change, or when a component it uses is saved. Saving a client script, a page's `head_html`/meta fields or its `client_scripts` list, or the site-wide style/script, leaves the old HTML (and the old `?v=` script URLs in it) in place.
2. **Cached documents.** The renderer reads client scripts and Builder Settings through Frappe's document cache, so a page can link a script's previous `public_url` for a moment after the save.
3. **Browser**: cached pages go out with `Cache-Control: private, max-age=300, stale-while-revalidate=10800`, so the human's own tab can show the old page for minutes after the server has the new one.
4. **CDN**, when the site sits behind one: its own TTL on pages and `/files` assets. Script files change URL on every save, so only the page HTML can go stale there.

Component saves clear their pages from a background job. On a site whose workers are down, those pages stay stale until something else clears them.

## Checking what visitors get

```sh
curl -sI "https://<site>/<route>" | grep -i x-from-cache      # True: this came from the page cache
curl -s  "https://<site>/<route>?fresh=1" > fresh.html          # a query string skips the cache: the render as of now
frappectl -s <p> doc list "Builder Client Script" -f name=<name> --fields public_url
```

- The fresh render is right and the plain URL isn't: it's the page cache. It expires within 30 minutes. Publishing the page again clears it at once. `page.py publish` refuses while the site's draft differs from your workdir, so it can't ship someone else's pending edits by accident; still ask the human, since it is a publish.
- The fresh render links an older `?v=` than the script's `public_url`: it's the document cache. Save the script once more through `doc update`.
- Both are right and the human still sees the old page: it's their browser or the CDN. A hard reload settles the browser.
- The fresh render is wrong too: the change never went live. Go back to the table above.

## Other places a write goes missing

- **An open editor tab** keeps the tree it loaded, and its next edit saves that tree over your draft (see SKILL.md).
- **Pages duplicated on older Builder versions can share script files**: their client scripts carry the same `public_url`, so saving one rewrites the file both pages load. Before editing a script, check no other `Builder Client Script` has its `public_url` (`doc list "Builder Client Script" -f public_url=<url>`); if one does, give the page a new script.
- **Deep trees** on sites created before blocks became Long Text can hit an old database CHECK constraint (`json_valid`) that rejects stored JSON deeper than 31. Each block level adds two (the block and its `children` list), so that is about 15 levels of blocks. The save fails, and the editor's autosave fails silently. `page.py lint` warns near the limit; keep the nesting shallow, or ask the human to drop the constraint.
