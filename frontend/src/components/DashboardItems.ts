import { createRegistry, type RegistryItem } from "@/utils/createRegistry";
import type { Component } from "vue";

/** A view of the dashboard, beside All Pages. It opens at /dashboard/<name> and fills the area right of the sidebar. */
export type DashboardItem = RegistryItem & {
	label: string;
	/** a lucide class name, or a component, such as a plugin's `lucideIcon()` */
	icon: string | Component;
	component: Component;
	props?: () => Record<string, unknown>;
};

export const dashboardItems = createRegistry<DashboardItem>();
