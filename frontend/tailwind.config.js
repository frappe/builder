import colors from "tailwindcss/colors";
import frappeUIPreset, { content as frappeUIContent } from "frappe-ui/tailwind";
import plugin from "tailwindcss/plugin";

export default {
	presets: [frappeUIPreset],
	content: [
		"./index.html",
		"./src/**/*.{vue,js,ts,jsx,tsx}",
		...frappeUIContent,
		// ListView is parked in experimental (frappe-ui#985) but sits outside
		// frappe-ui's published content globs; scan it while we still use it
		"../node_modules/frappe-ui/experimental/ListView/**/*.{vue,js,ts,jsx,tsx}",
	],
	plugins: [
		plugin(function ({ matchUtilities, theme }) {
			matchUtilities(
				{
					"auto-fill": (value) => ({
						gridTemplateColumns: `repeat(auto-fill, minmax(min(${value}, 100%), 1fr))`,
					}),
					"auto-fit": (value) => ({
						gridTemplateColumns: `repeat(auto-fit, minmax(min(${value}, 100%), 1fr))`,
					}),
				},
				{
					values: theme("width", {}),
				},
			);
		}),
		require("@tailwindcss/container-queries"),
	],
	theme: {
		extend: {
			transitionProperty: {
				size: "transform, border-radius",
			},
			colors: {
				zinc: colors.zinc,
			},
		},
	},
};
