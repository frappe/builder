export default {
	env: {
		browser: true,
		es2021: true,
	},
	globals: {
		convertHTMLToBlocks: true,
	},
	extends: ["plugin:vue/vue3-recommended", "prettier"],
	parser: "vue-eslint-parser",
	parserOptions: {
		parser: "@typescript-eslint/parser",
		ecmaVersion: 13,
		sourceType: "module",
	},
	plugins: ["vue"],
	rules: {
		quotes: ["error", "double"],
		indent: ["error", "tab"],
		"no-param-reassign": ["error", { props: false }],
		"vue/html-indent": [
			"error",
			"tab",
			{
				alignAttributesVertically: false,
				ignores: ["VAttribute"],
			},
		],
		"vue/html-closing-bracket-newline": [
			"error",
			{
				singleline: "never",
				multiline: "never",
			},
		],
		"vue/max-attributes-per-line": [
			"warn",
			{
				singleline: {
					max: 4,
				},
				multiline: {
					max: 3,
				},
			},
		],
		"vue/v-on-event-hyphenation": [
			"warn",
			"always",
			{
				autofix: true,
				ignore: [],
			},
		],
	},
};
