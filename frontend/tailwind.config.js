const plugin = require('tailwindcss/plugin')

module.exports = {
	presets: [require("frappe-ui/src/utils/tailwind.config")],
	content: [
		"./index.html",
		"./src/**/*.{vue,js,ts,jsx,tsx}",
		"./node_modules/frappe-ui/src/components/**/*.{vue,js,ts,jsx,tsx}",
		"../node_modules/frappe-ui/src/components/**/*.{vue,js,ts,jsx,tsx}",
	],
	theme: {
		extend: {
			transitionProperty: {
				size: "transform, border-radius",
			},
		},
	},
	plugins: [
		plugin(function({ addUtilities }) {
			addUtilities({
				".no-scrollbar::-webkit-scrollbar" : {
					"display": "none"
				},
				".no-scrollbar": {
					"-ms-overflow-style": "none",
					"scrollbar-width": "none"
				},
			})
		})
	],
};
