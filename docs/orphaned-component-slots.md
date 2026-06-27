# Deferred: Orphaned Component Slot Detection

## Concept

A component instance stores detached content under a named slot. If a later component version removes or renames that slot, the detached content still exists in the old instance but has no destination in the new component structure. That content is considered **orphaned slot content**.

Example:

1. A component exposes a `footer` slot.
2. A page instance contains detached blocks in `footer`.
3. The component author deletes or renames `footer`.
4. Updating the instance cannot place those blocks into the new component tree.

Empty removed slots are not meaningful orphans because no user content would be lost.

## Previous Implementation

The initial implementation performed an exact preflight before every update:

- Collect the slot names declared by the incoming component version, ignoring slots owned by nested components.
- Walk each existing component instance and collect filled slots whose names are absent from the incoming version.
- For a single-instance or page-wide update, aggregate the removed slot names and ask for confirmation before rebuilding anything.
- For “Sync in all pages,” scan matching pages on the server across both draft and published block trees, return an orphan summary through a preview endpoint, and require an explicit discard flag on the subsequent sync request.
- Preserve content when the same slot name exists in the new version, even if its container moved within the component tree.

This prevented silent data loss but required duplicate tree-walking logic in the frontend and backend, an additional sync-preview API, extra page scans, bulk-update coordination, and dedicated failure paths.

## Current Temporary Behavior

Component updates and global syncs now show one generic warning:

> Updating components may remove or rename slots. Detached content in those slots may be discarded.

No slot-tree preflight is performed. Content is still preserved whenever the incoming component contains a slot with the same name.

## Future Implementation Notes

When precise orphan handling becomes worthwhile:

- Build one shared conceptual reconciliation contract: slot names are identities; matching names preserve detached children; missing names create orphans.
- Perform the entire preflight before mutating any instance, especially for “Update all.”
- Return a structured impact summary containing component, page, slot name, and detached block count.
- Keep the server-side sync endpoint safe by requiring an explicit resolution when orphans exist.
- Decide whether resolution means discarding content, moving it outside the component, or letting users remap it to another slot.
- Ignore intentionally empty slots unless their empty state itself needs to survive the update.

The reconciliation code that preserves slots by matching names can remain; only the exact detection and resolution workflow needs to be added later.
