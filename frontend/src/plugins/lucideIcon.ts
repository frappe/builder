import { defineComponent, h, markRaw, type Component } from "vue";
import RuntimeLucideIcon from "./RuntimeLucideIcon.vue";

const iconComponents = new Map<string, Component>();

/**
 * A lucide icon by name, as a component, for any surface that takes an icon.
 * Builder's build holds only the icons it uses, so a plugin's icon loads at runtime.
 */
export const lucideIcon = (name: string): Component => {
	if (!iconComponents.has(name)) {
		iconComponents.set(
			name,
			markRaw(defineComponent({ name: "LucideIcon", render: () => h(RuntimeLucideIcon, { name }) })),
		);
	}
	return iconComponents.get(name) as Component;
};
