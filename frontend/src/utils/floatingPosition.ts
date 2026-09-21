import { Position, clamp } from "@vueuse/core";

interface Box {
	left: number;
	top: number;
	right: number;
	bottom: number;
	width: number;
	height: number;
}

/**
 * Where a floating element goes inside `bounds`: the given position if there is
 * one, else centered at the top. The result always stays inside the bounds.
 */
export function placeWithinBounds(
	bounds: Box,
	size: Pick<Box, "width" | "height">,
	position: Position | null,
	margin = 12,
): Position {
	const target = position || {
		x: bounds.left + (bounds.width - size.width) / 2,
		y: bounds.top + margin,
	};
	return {
		x: clamp(target.x, bounds.left + margin, bounds.right - size.width - margin),
		y: clamp(target.y, bounds.top + margin, bounds.bottom - size.height - margin),
	};
}
