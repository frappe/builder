# Code Taste

Preferences for this codebase. Follow existing patterns first. Apply these unless a specific case has a stronger reason.

## General

- Keep changes small and focused.
- Look for existing patterns before adding new ones.
- Reuse or extend existing components/helpers when possible.
- Create abstractions only when similar patterns repeat.

## Python

- No `_` prefix for helper functions — they aren't truly private here and the prefix adds noise. Use plain `snake_case`.
- Keep functions/methods small (~10 lines when practical).
- Prefer OOP and keep logic close to the object it belongs to.
- Avoid comments that explain what the next line does.
- Add comments only for non-obvious reasons: constraints, workarounds, or important assumptions.
- Don't repeat docstrings in comments.

## Vue / TypeScript

- Use existing frappe-ui components before creating custom UI
- Keep page templates small.
- Move large/repeated UI pieces into feature-specific `.vue` components.
- Check for similar code before building something new. Extract common patterns when repetition appears.
