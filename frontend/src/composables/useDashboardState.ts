import { useStorage } from "@vueuse/core";
import { ref, Ref } from "vue";

const searchFilter = ref("");
const selectionMode = ref(false);
const selectedPages = ref(new Set<string>());
const treeExpanded = ref(true);
const showTemplatesDialog = ref(false);

// remembers the template group the picker was last drilled into ("" = gallery)
const lastTemplateGroup = useStorage("lastTemplateGroup", "") as Ref<string>;

// active category filter in the template gallery ("" = All)
const templateCategoryFilter = useStorage("templateCategoryFilter", "") as Ref<string>;

const displayType = useStorage("displayType", "grid") as Ref<"grid" | "list" | "tree">;
const typeFilter = useStorage("typeFilter", "") as Ref<"" | "draft" | "published" | "unpublished" | "all">;
const orderBy = useStorage("orderBy", "creation") as Ref<
	"creation" | "modified" | "alphabetically_a_z" | "alphabetically_z_a"
>;

const expandTreeFn = ref<(() => void) | null>(null);
const collapseTreeFn = ref<(() => void) | null>(null);

export function useDashboardState() {
	return {
		searchFilter,
		selectionMode,
		selectedPages,
		treeExpanded,
		showTemplatesDialog,
		lastTemplateGroup,
		templateCategoryFilter,
		displayType,
		typeFilter,
		orderBy,
		expandTreeFn,
		collapseTreeFn,
	};
}
