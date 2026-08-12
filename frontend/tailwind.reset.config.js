import forms from "@tailwindcss/forms";

// Config for the published-page reset stylesheet (built via `npm run build:reset`).
//
// Published Builder pages get Preflight + @tailwindcss/forms (so native form
// controls render consistently) + the base font rules in src/reset.css.
//
// It deliberately does NOT use the frappe-ui preset. The preset's theme plugin
// dumps its entire design-token set onto every page — `:root { --surface-*, --ink-*,
// --focus-*, … }` plus a matching `[data-theme="dark"] { … }` block — which published
// pages never reference (they use inline styles, not frappe-ui components). That token
// dump was ~90% of the file. Core plugins stay enabled so the `--tw-ring-*`/`--tw-shadow`
// vars that @tailwindcss/forms' focus styles depend on are still emitted.
export default {
	content: ["./src/reset.css"],
	plugins: [forms],
};
