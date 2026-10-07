import frappeUIPreset from "frappe-ui/tailwind";

export default {
	presets: [frappeUIPreset],
	content: ["./src/**/*.{vue,ts}", "./node_modules/frappe-ui/src/**/*.{vue,js,ts}"],
};
