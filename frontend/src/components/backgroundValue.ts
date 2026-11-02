import { cssUrl } from "@/utils/helpers";

export function parseBackgroundValue(value: string, resolvedValue: string) {
	const input = value.trim();
	if (!input) return null;
	const color = /^([0-9A-F]{3}){1,2}$/i.test(input) ? `#${input}` : input;
	if (!input.startsWith("var(") && CSS.supports("color", color)) return { color };
	if (resolvedValue !== input && CSS.supports("color", resolvedValue)) return { color: input };
	const url = input.match(/^url\(\s*(['"]?)(.*?)\1\s*\)$/i);
	if (url) return { image: cssUrl(url[2]) };
	if (/^(https?:\/\/|\/|data:)/.test(input)) return { image: cssUrl(input) };
	if (input.includes("gradient(") && CSS.supports("background-image", input)) return { image: input };
	return CSS.supports("background", input) ? { background: input } : null;
}
