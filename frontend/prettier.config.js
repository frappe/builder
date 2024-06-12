module.exports = {
	useTabs: true,
	bracketSameLine: true,
	bracketSpacing: true,
	htmlWhitespaceSensitivity: "ignore",
	singleAttributePerLine: false,
	printWidth: 110,
	trailingComma: "all",
	plugins: [require("prettier-plugin-tailwindcss")],
	tailwindConfig: "./tailwind.config.js",
};
