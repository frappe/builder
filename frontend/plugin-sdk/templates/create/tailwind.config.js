import frappeUIPreset from "frappe-ui/tailwind";

export default {
	presets: [frappeUIPreset],
	content: ["./src/**/*.{vue,ts}"],
	// the editor already applies the base styles. A second reset would restyle the editor
	corePlugins: { preflight: false },
};
