import { createRegistry, type RegistryItem } from "@/utils/createRegistry";
import type { Component } from "vue";

/**
 * A view of the dashboard, beside All Pages. It opens at /dashboard/<name> and fills the area right of the sidebar.
 * Its component gets `DashboardItemProps`, so the URL after /dashboard/<name>/ can keep where the user is.
 */
export type DashboardItem = RegistryItem & {
	label: string;
	/** a lucide class name, or a component, such as a plugin's `lucideIcon()` */
	icon: string | Component;
	component: Component;
	props?: () => Record<string, unknown>;
};

export type DashboardItemProps = {
	/** the URL segments after /dashboard/<name>/ */
	path: string[];
	/** goes to /dashboard/<name>/<path>. Replace keeps the browser history as it is */
	navigate: (path: string[], options?: { replace?: boolean }) => void;
};

export const dashboardItems = createRegistry<DashboardItem>();
