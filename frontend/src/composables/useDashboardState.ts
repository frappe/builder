import { useStorage } from "@vueuse/core";
import { ref, Ref } from "vue";

// Module-level singletons shared across DashboardHead and DashboardContent
const searchFilter = ref("");
const selectionMode = ref(false);
const selectedPages = ref(new Set<string>());
const showFolderSelectorDialog = ref(false);
const treeExpanded = ref(true);

const displayType = useStorage("displayType", "grid") as Ref<"grid" | "list" | "tree">;
const typeFilter = useStorage("typeFilter", "") as Ref<"" | "draft" | "published" | "unpublished" | "all">;
const orderBy = useStorage("orderBy", "creation") as Ref<
	"creation" | "modified" | "alphabetically_a_z" | "alphabetically_z_a"
>;

// Callbacks registered by DashboardContent so DashboardHead can control the tree
const expandTreeFn = ref<(() => void) | null>(null);
const collapseTreeFn = ref<(() => void) | null>(null);

export function useDashboardState() {
	return {
		searchFilter,
		selectionMode,
		selectedPages,
		showFolderSelectorDialog,
		treeExpanded,
		displayType,
		typeFilter,
		orderBy,
		expandTreeFn,
		collapseTreeFn,
	};
}
