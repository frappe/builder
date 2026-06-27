# Named Component Slots

## Summary

Allow component authors to mark container blocks as named slots. Component structure remains locked in page instances, while users can add, remove, and reorder normal blocks inside exposed slots.

## Implementation Changes

- Add block metadata:
  - `slotName?: string` declares a slot in a component definition.
  - `slotFilled?: boolean` distinguishes fallback content from custom—even intentionally empty—content.
- Add a “Component Slot” property section in component-editing mode. Require non-empty, trimmed, unique names.
- In page mode:
  - Keep slot containers fixed and component-owned.
  - Permit normal blocks and components to be dropped, pasted, moved, reordered, or deleted within slots.
  - Materialize component-authored slot children as detached instance content so they can immediately be edited, reordered, or deleted.
  - Keep an emptied slot intentionally empty; fallback content returns only through “Reset slot to fallback.”
  - Provide “Reset slot to fallback” to discard custom content and create fresh detached copies of component-authored children.
  - Continue rejecting structural edits or drops elsewhere inside component instances.
- Update frontend and server reconciliation to preserve filled slots by exact `slotName`, even when the slot moves within the component tree. Renaming therefore behaves as removing one slot and adding another.
- During component updates and “Sync in all pages,” show a generic warning that removed or renamed slots may discard detached content. Precise orphan detection is deferred to `docs/orphaned-component-slots.md`.
- Make server rendering explicitly choose custom slot children when `slotFilled`, including an empty list, and otherwise render fallback children.
- Include slot fields in Python block serialization, copy/paste, component snapshots, detach/reset flows, and nested-component traversal. Existing components remain valid without migration.

## Test Plan

- New instances receive detached copies of authored slot content.
- Deleting any or every slot child leaves the slot partially filled or empty without restoring content.
- Resetting restores fallback content.
- Multiple slots retain independent content and ordering.
- Slot content survives component updates, slot movement, version pinning, page save/reload, and server rendering.
- Component updates and “Sync in all pages” require generic confirmation before mutation.
- Static component descendants still cannot be reordered, deleted, or used as drop targets.
- Duplicate or blank slot names are rejected.
- Run targeted backend component/rendering tests and the frontend production build.

## Assumptions

- Slot names are exact, case-sensitive identifiers.
- Slots may be declared on ordinary container blocks, including the component root.
- Slots inside repeaters and nested slot containers are excluded initially to avoid ambiguous repeated ownership.
- Slot content accepts the same blocks and nested components as a normal page container.
