# When a live change doesn't show

A change that "didn't take" either went somewhere that isn't live (a page's `draft_blocks`, a pinned component instance), or it is live and a cache still serves the old copy. Find out which before changing anything again.

## The page cache

On production sites (not in developer mode), a page's rendered HTML is cached in Redis for 30 minutes. Pages with a data script, a dynamic route or a component data script are never cached.

The cache is cleared when the page's blocks, route or publish state change, and when a component it embeds, a client script it links or Builder Settings is saved.

```sh
curl -sI "https://<site>/<route>" | grep -i x-from-cache       # True: served from the cache
curl -s  "https://<site>/<route>?fresh=1" > fresh.html          # a query string skips the cache
```

- The fresh render is right and the plain URL isn't: it's the page cache; it expires within 30 minutes, or publishing the page again clears it (ask first; `builder.py publish` refuses if the draft holds someone else's edits).
- The fresh render is wrong too: the change never went live. Pages need publish; editor-dropped component instances need `sync`.

## A component save that never shows

Publishing a page queues background renders of it (preview image, search index). A component saved while one of those renders is running can be re-cached in its old version, and every unpinned instance then keeps rendering the old version with no expiry. Wait about 15 seconds after publishing a page before saving a component it uses. If it already happened, saving the component again (with any change) fixes it.

## Other places a write goes missing

- An editor tab open on the page saves its old tree over your draft on its next edit.
