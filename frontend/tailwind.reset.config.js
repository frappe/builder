// Config for the published-page reset stylesheet (built via `npm run build:reset`).
//
// Published Builder pages use inline styles — never Tailwind utilities or frappe-ui
// components. So this build deliberately omits the frappe-ui preset and enables only
// the `preflight` core plugin. That keeps reset.css to Preflight + the base rules
// authored in src/reset.css, and drops the two things the full app config would
// otherwise dump onto every published page:
//   - Tailwind's `--tw-*` utility variable defaults (*, ::before, ::after, ::backdrop)
//   - frappe-ui's design-token :root set (--surface-*, --ink-*, --focus-*, …)
// Neither is referenced by published pages.
export default {
	content: ["./src/reset.css"],
	corePlugins: ["preflight"],
};
