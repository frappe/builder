import tsParser from "@typescript-eslint/parser";
import prettier from "eslint-config-prettier";
import pluginVue from "eslint-plugin-vue";
import vueParser from "vue-eslint-parser";

export default [
	...pluginVue.configs["flat/recommended"],
	prettier,
	{
		files: ["**/*.js", "**/*.ts", "**/*.vue"],
		languageOptions: {
			parser: vueParser,
			ecmaVersion: 13,
			sourceType: "module",
			parserOptions: {
				parser: tsParser,
			},
		},
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
	},
];
