import { readFileSync, writeFileSync } from "fs";

const file = new URL("../../builder/public/reset.css", import.meta.url).pathname;
const css = readFileSync(file, "utf8")
	.replace(/\/\*![\s\S]*?\*\//g, "") // strip license comments
	.replace(/\n+/g, "") // collapse blank lines
	.trim();

writeFileSync(file, css);
