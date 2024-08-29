import colors from "tailwindcss/colors";
import tailwindConfig from "frappe-ui/src/utils/tailwind.config";
import plugin from "tailwindcss/plugin";
import espressoColors from "./espresso_colors";

module.exports = {
	darkMode: "class",
	presets: [tailwindConfig],
	content: [
		"./index.html",
		"./src/**/*.{vue,js,ts,jsx,tsx}",
		"./node_modules/frappe-ui/src/components/**/*.{vue,js,ts,jsx,tsx}",
		"../node_modules/frappe-ui/src/components/**/*.{vue,js,ts,jsx,tsx}",
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
	],
	theme: {
		extend: {
			transitionProperty: {
				size: "transform, border-radius",
			},
			colors: {
				zinc: colors.zinc,
				...espressoColors,
			},
		},
	},
};
