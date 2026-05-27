// Color conversion utilities (hex <-> HSV <-> rgb).
// Extracted from helpers.ts; re-exported there for backwards compatibility.

function HexToHSV(color: HashString): {
	h: number;
	s: number;
	v: number;
	a: number;
} {
	// Remove hash and normalize length
	let hex = color.replace("#", "").trim();

	// Expand short hex (#abc -> #aabbcc)
	if (hex.length === 3) {
		hex = hex
			.split("")
			.map((c) => c + c)
			.join("");
	}

	// Extract alpha from 8-digit hex (#RRGGBBAA)
	let a = 100;
	if (/^[0-9a-fA-F]{8}$/.test(hex)) {
		a = Math.round((parseInt(hex.slice(6, 8), 16) / 255) * 100);
		hex = hex.slice(0, 6);
	}

	// If not valid hex, return black
	if (!/^[0-9a-fA-F]{6}$/.test(hex)) {
		return { h: 0, s: 0, v: 0, a: 100 };
	}

	const r = parseInt(hex.slice(0, 2), 16);
	const g = parseInt(hex.slice(2, 4), 16);
	const b = parseInt(hex.slice(4, 6), 16);

	const max = Math.max(r, g, b);
	const min = Math.min(r, g, b);
	const v = max / 255;
	const d = max - min;
	const s = max === 0 ? 0 : d / max;

	let h = 0;
	if (d !== 0) {
		if (max === r) {
			h = (g - b) / d + (g < b ? 6 : 0);
		} else if (max === g) {
			h = (b - r) / d + 2;
		} else {
			h = (r - g) / d + 4;
		}
		h *= 60;
	}

	return { h, s, v, a };
}

function HSVToHex(h: number, s: number, v: number, a: number = 100): HashString {
	s /= 100;
	v /= 100;
	h /= 360;

	let r = 0,
		g = 0,
		b = 0;

	let i = Math.floor(h * 6);
	let f = h * 6 - i;
	let p = v * (1 - s);
	let q = v * (1 - f * s);
	let t = v * (1 - (1 - f) * s);

	switch (i % 6) {
		case 0:
			(r = v), (g = t), (b = p);
			break;
		case 1:
			(r = q), (g = v), (b = p);
			break;
		case 2:
			(r = p), (g = v), (b = t);
			break;
		case 3:
			(r = p), (g = q), (b = v);
			break;
		case 4:
			(r = t), (g = p), (b = v);
			break;
		case 5:
			(r = v), (g = p), (b = q);
			break;
	}
	r = Math.round(r * 255);
	g = Math.round(g * 255);
	b = Math.round(b * 255);
	const hex = `#${[r, g, b].map((x) => x.toString(16).padStart(2, "0")).join("")}` as HashString;
	const alphaByte = Math.round((a / 100) * 255);
	if (alphaByte < 255) {
		return `${hex}${alphaByte.toString(16).padStart(2, "0")}` as HashString;
	}
	return hex;
}

function getRandomColor() {
	return HSVToHex(Math.random() * 360, 25, 100);
}

function RGBToHex(rgb: RGBString): HashString {
	const [r, g, b] = rgb
		.replace("rgb(", "")
		.replace(")", "")
		.split(",")
		.map((x) => parseInt(x));
	return `#${[r, g, b].map((x) => x.toString(16).padStart(2, "0")).join("")}`;
}

function getRGB(color: HashString | RGBString | string | null): HashString | null {
	if (!color) {
		return null;
	}
	if (color.startsWith("rgba")) {
		const parts = color
			.replace("rgba(", "")
			.replace(")", "")
			.split(",")
			.map((x) => x.trim());
		const [r, g, b] = parts.map((x) => parseInt(x));
		const alphaHex = Math.round(parseFloat(parts[3]) * 255)
			.toString(16)
			.padStart(2, "0");
		return `#${[r, g, b].map((x) => x.toString(16).padStart(2, "0")).join("")}${alphaHex}` as HashString;
	}
	if (color.startsWith("rgb")) {
		return RGBToHex(color as RGBString);
	} else if (!color.startsWith("#") && color.match(/\b[a-fA-F0-9]{3,6}\b/g)) {
		return `#${color}` as HashString;
	}
	return color as HashString;
}

export { HexToHSV, HSVToHex, getRandomColor, RGBToHex, getRGB };
