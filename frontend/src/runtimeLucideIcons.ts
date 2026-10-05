const ICON_NAME = /^[a-z0-9-]+$/;
const iconCache = new Map<string, Promise<string | undefined>>();
const iconBaseUrl = "https://unpkg.com/lucide-static@1.16.0/icons/";

export const loadRuntimeLucideIcon = (name: string) => {
	if (!name.startsWith("lucide-")) return;

	const iconName = name.slice("lucide-".length);
	if (!ICON_NAME.test(iconName)) return;
	if (!iconCache.has(iconName)) {
		iconCache.set(iconName, fetch(`${iconBaseUrl}${iconName}.svg`).then((response) => (response.ok ? response.text() : undefined)));
	}
	return iconCache.get(iconName);
};

export const createLucideMaskImage = (svg: string) => {
	const normalizedSvg = svg.replace(/stroke-width="[^"]+"/g, "stroke-width=\"1.5\"").replace(/\s+/g, " ").trim();
	return `url("data:image/svg+xml;utf8,${encodeURIComponent(normalizedSvg)}")`;
};
