export interface GradientStop {
	color: any;
	position: number;
}

export interface Gradient {
	type: "linear-gradient" | "radial-gradient";
	angle: string;
	stops: GradientStop[];
}

export function parseGradient(gradientStr: string): Gradient | null {
	if (!gradientStr || !gradientStr.includes("gradient")) return null;

	const typeMatch = gradientStr.match(/^(linear|radial)-gradient/);
	if (!typeMatch) return null;

	const type = (typeMatch[0] + "") as Gradient["type"];
	const content = gradientStr.substring(gradientStr.indexOf("(") + 1, gradientStr.lastIndexOf(")"));

	const parts = tokenizeGradientContent(content);
	let angle = type === "linear-gradient" ? "180deg" : "circle";
	let stopsStartIdx = 0;

	if (parts[0]) {
		const firstPart = parts[0].trim();
		const isAngle = /^(-?\d+(\.\d+)?deg|to\s+(top|bottom|left|right)(\s+(top|bottom|left|right))?)/i.test(firstPart);
		const isRadialConfig = /^(circle|ellipse|at\s+|closest-side|farthest-side|closest-corner|farthest-corner)/i.test(firstPart);

		if (isAngle || isRadialConfig) {
			angle = firstPart;
			stopsStartIdx = 1;
		}
	}

	const stops: GradientStop[] = [];
	for (let i = stopsStartIdx; i < parts.length; i++) {
		const part = parts[i].trim();
		if (!part) continue;

		const stopMatch = part.match(/(.+?)\s+(-?[0-9.]+%|-?[0-9.]+px)?$/);
		if (stopMatch && stopMatch[2]) {
			const color = stopMatch[1].trim();
			const posStr = stopMatch[2].trim();
			let position = 0;
			if (posStr.endsWith("%")) {
				position = parseFloat(posStr);
			} else {
				// Fallback for px or other units - simple linear distribution for now
				position = (i - stopsStartIdx) * (100 / (parts.length - stopsStartIdx - 1 || 1));
			}
			stops.push({ color, position });
		} else {
			// Just color or invalid match
			stops.push({
				color: part,
				position: (i - stopsStartIdx) * (100 / (parts.length - stopsStartIdx - 1 || 1)),
			});
		}
	}

	return { type, angle, stops };
}

function tokenizeGradientContent(content: string): string[] {
	const tokens: string[] = [];
	let current = "";
	let parenDepth = 0;

	for (let i = 0; i < content.length; i++) {
		const char = content[i];
		if (char === "(") parenDepth++;
		if (char === ")") parenDepth--;

		if (char === "," && parenDepth === 0) {
			tokens.push(current.trim());
			current = "";
		} else {
			current += char;
		}
	}
	if (current) tokens.push(current.trim());
	return tokens;
}

export function stringifyGradient(gradient: Gradient): string {
	const stopsStr = [...gradient.stops]
		.sort((a, b) => a.position - b.position)
		.map((s) => `${s.color} ${s.position}%`)
		.join(", ");

	return `${gradient.type}(${gradient.angle}, ${stopsStr})`;
}
