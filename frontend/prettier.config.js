module.exports = {
	useTabs: true,
	bracketSameLine: true,
	bracketSpacing: true,
	htmlWhitespaceSensitivity: "ignore",
	singleAttributePerLine: false,
	printWidth: 110,
	plugins: [require("prettier-plugin-tailwindcss")],
	tailwindConfig: "./tailwind.config.js",
};
