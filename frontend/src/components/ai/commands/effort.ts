import type { MenuItem, MenuLevel } from "@/components/ai/commandMenu";
import type { BobContext } from "@/components/ai/commands/shared";

/** The server's llm.Effort levels; "" leaves each step at its own default. */
export const EFFORTS = [
	{ value: "", label: "Auto", description: "Medium for edits, high for page builds" },
	{ value: "low", label: "Low", description: "Fastest, may miss things" },
	{ value: "medium", label: "Medium" },
	{ value: "high", label: "High", description: "Slower, more careful" },
	{ value: "xhigh", label: "Extra high", description: "Minutes per step" },
];

export function effortLabel(value: string): string {
	return EFFORTS.find((e) => e.value === value)?.label ?? "Auto";
}

export function effortLevel(ctx: BobContext): MenuLevel {
	return {
		title: "Thinking effort",
		items: () =>
			EFFORTS.map((effort): MenuItem => ({
				key: effort.value || "auto",
				label: effort.label,
				description: effort.description,
				selected: effort.value === ctx.chat.selectedEffort.value,
				run: () => {
					ctx.chat.selectedEffort.value = effort.value;
				},
			})),
	};
}
