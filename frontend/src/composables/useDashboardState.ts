import useBuilderStore from "@/stores/builderStore";
import { useStorage } from "@vueuse/core";
import { ref, Ref } from "vue";

const searchFilter = ref("");
const treeExpanded = ref(true);
const showTemplatesDialog = ref(false);

// remembers the template group the picker was last drilled into ("" = gallery)
const lastTemplateGroup = useStorage("lastTemplateGroup", "") as Ref<string>;

// active category filter in the template gallery ("" = All)
const templateCategoryFilter = useStorage("templateCategoryFilter", "") as Ref<string>;

const displayType = useStorage("displayType", "grid") as Ref<"grid" | "list" | "tree">;
// a fresh key: values saved under the old "typeFilter" key (published/unpublished) no longer exist
const statusFilter = useStorage("pageStatusFilter", "") as Ref<"" | "all" | "live" | "staging" | "draft">;
const orderBy = useStorage("orderBy", "modified") as Ref<
	"creation" | "modified" | "alphabetically_a_z" | "alphabetically_z_a"
>;

export type DashboardView = "all" | "folder";
const dashboardView = useStorage("dashboardView", "all") as Ref<DashboardView>;

// activeFolder still drives the page query and new-page placement, so a view sets both
function openDashboardView(view: DashboardView, folder = "") {
	dashboardView.value = view;
	searchFilter.value = "";
	useBuilderStore().activeFolder = view === "folder" ? folder : "";
}

const expandTreeFn = ref<(() => void) | null>(null);
const collapseTreeFn = ref<(() => void) | null>(null);

export function useDashboardState() {
	return {
		searchFilter,
		treeExpanded,
		showTemplatesDialog,
		lastTemplateGroup,
		templateCategoryFilter,
		displayType,
		statusFilter,
		orderBy,
		expandTreeFn,
		collapseTreeFn,
		dashboardView,
		openDashboardView,
	};
}
