<template>
	<div class="isolate">
		<div v-if="pagesResource.loading && !pages.length" class="px-3 py-6 text-center text-sm text-ink-gray-4">
			Loading pages…
		</div>
		<div
			v-else-if="!pagesResource.loading && !pages.length"
			class="px-3 py-6 text-center text-sm text-ink-gray-4">
			No pages found.
		</div>

		<div
			v-else
			ref="treeRef"
			tabindex="0"
			@focus="isFocused = true"
			@blur="isFocused = false"
			class="focus:outline-none">
			<RouteTreeNode
				v-if="treeNodes.length"
				:nodes="treeNodes"
				:focused-node-id="focusedNodeId"
				:sticky-row-height="STICKY_ROW_HEIGHT"
				:on-select="selectNode"
				:on-toggle="toggleNode"
				:on-activate="activateNode"
				:on-load-more="loadMore"
				:set-node-ref="setNodeRef"
				:is-home-page="isHomePage" />

			<div
				v-if="rootLoadMore.hasMore"
				class="flex items-center pt-2"
				:style="{ marginLeft: `${STICKY_ROW_HEIGHT}px` }">
				<button
					class="flex items-center gap-1 text-xs text-ink-gray-4 hover:text-ink-gray-7"
					@click="loadMore('__root__', rootLoadMore.loadedCount)">
					<span class="lucide-more-horizontal size-3" aria-hidden="true" />
					Load {{ Math.min(PAGE_LIMIT_PER_NODE, rootLoadMore.totalCount - rootLoadMore.loadedCount) }} more
					<span class="ml-0.5 text-ink-gray-3">
						({{ rootLoadMore.totalCount - rootLoadMore.loadedCount }} remaining)
					</span>
				</button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
// TODO: Refactor to meke it generic, this has lots of unnecessary coupling, props usage and hacky implementation
import RouteTreeNode from "@/components/RouteTreeNode.vue";
import { builderSettings } from "@/data/builderSettings";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { useShortcut } from "@/utils/useShortcut";
import { createListResource } from "frappe-ui";
import { computed, onBeforeUpdate, ref, watch, watchEffect } from "vue";
import { useRouter } from "vue-router";

const props = withDefaults(
	defineProps<{
		searchFilter?: string;
		activeFolder?: string;
	}>(),
	{ searchFilter: "", activeFolder: "" },
);

const PAGE_LIMIT_PER_NODE = 50;
const AUTO_COLLAPSE_THRESHOLD = 100;
const STICKY_ROW_HEIGHT = 36;

const router = useRouter();

interface Node {
	id: string;
	label: string;
	fullPath: string;
	depth: number;
	stickyStackDepth: number;
	page: BuilderPage | null;
	hasChildren: boolean;
	expanded: boolean;
	parentId: string | null;
	children: Node[];
	hasMore: boolean;
	loadedCount: number;
	totalCount: number;
}

interface RootLoadMore {
	hasMore: boolean;
	loadedCount: number;
	totalCount: number;
}

type TrieNode = {
	page: BuilderPage | null;
	children: Map<string, TrieNode>;
};

const pagesResource = createListResource({
	method: "GET",
	doctype: "Builder Page",
	fields: ["name", "route", "page_name", "page_title", "published", "authenticated_access", "project_folder"],
	filters: { is_template: 0 },
	orderBy: "route asc",
	pageLength: 9999,
	auto: true,
});

const pages = computed<BuilderPage[]>(() => {
	let result: BuilderPage[] = pagesResource.data ?? [];
	if (props.activeFolder) {
		result = result.filter((p) => p.project_folder === props.activeFolder);
	}
	if (props.searchFilter) {
		const q = props.searchFilter.toLowerCase();
		result = result.filter(
			(p) => p.page_title?.toLowerCase().includes(q) || p.route?.toLowerCase().includes(q),
		);
	}
	return result;
});

const collapsedNodes = ref(new Set<string>());
const loadedCounts = ref(new Map<string, number>());
const focusedNodeId = ref<string | null>(null);
const treeRef = ref<HTMLElement | null>(null);
const nodeEls = ref(new Map<string, HTMLElement>());
const initialized = ref(false);
const isFocused = ref(false);

onBeforeUpdate(() => {
	nodeEls.value.clear();
});

function buildTrie(pageList: BuilderPage[]): Map<string, TrieNode> {
	const root: Map<string, TrieNode> = new Map();
	for (const page of pageList) {
		const segments = (page.route || "").split("/").filter(Boolean);
		let current = root;
		for (let i = 0; i < segments.length; i++) {
			const seg = segments[i];
			if (!current.has(seg)) {
				current.set(seg, { page: null, children: new Map() });
			}
			const node = current.get(seg)!;
			if (i === segments.length - 1) {
				node.page = page;
			}
			current = node.children;
		}
	}
	return root;
}

function getLimit(nodeId: string): number {
	return loadedCounts.value.get(nodeId) ?? PAGE_LIMIT_PER_NODE;
}

const treeState = computed(() => {
	const trie = buildTrie(pages.value);

	function buildNodes(
		map: Map<string, TrieNode>,
		depth: number,
		parentPath: string,
		parentId: string | null,
		stickyStackDepth: number,
	): Node[] {
		const entries = Array.from(map.entries());
		const limitKey = parentId ?? "__root__";
		const limit = getLimit(limitKey);
		const visible = entries.slice(0, limit);

		return visible.map(([label, trieNode]) => {
			const fullPath = parentPath ? `${parentPath}/${label}` : label;
			const hasChildren = trieNode.children.size > 0;
			const expanded = !!props.searchFilter || !collapsedNodes.value.has(fullPath);
			const children =
				hasChildren && expanded
					? buildNodes(trieNode.children, depth + 1, fullPath, fullPath, stickyStackDepth + 1)
					: [];

			return {
				id: fullPath,
				label,
				fullPath,
				depth,
				stickyStackDepth,
				page: trieNode.page,
				hasChildren,
				expanded,
				parentId,
				children,
				hasMore: hasChildren && trieNode.children.size > getLimit(fullPath),
				loadedCount: hasChildren ? Math.min(getLimit(fullPath), trieNode.children.size) : 0,
				totalCount: hasChildren ? trieNode.children.size : 0,
			};
		});
	}

	const rootEntries = Array.from(trie.entries());
	const rootLimit = getLimit("__root__");
	return {
		nodes: buildNodes(trie, 0, "", null, 0),
		rootLoadMore: {
			hasMore: rootEntries.length > rootLimit,
			loadedCount: Math.min(rootLimit, rootEntries.length),
			totalCount: rootEntries.length,
		} satisfies RootLoadMore,
	};
});

const treeNodes = computed(() => treeState.value.nodes);
const rootLoadMore = computed(() => treeState.value.rootLoadMore);

function flattenNodes(nodes: Node[], result: Node[] = []): Node[] {
	for (const node of nodes) {
		result.push(node);
		if (node.hasChildren && node.expanded) {
			flattenNodes(node.children, result);
		}
	}
	return result;
}

function selectNode(node: Node) {
	focusedNodeId.value = node.id;
	treeRef.value?.focus({ preventScroll: true });
}

function activateNode(node: Node) {
	if (node.page?.page_name) {
		router.push({ name: "builder", params: { pageId: node.page.page_name } });
	} else if (node.hasChildren) {
		toggleNode(node);
	}
}

function toggleNode(node: Node) {
	const next = new Set(collapsedNodes.value);
	if (next.has(node.id)) {
		next.delete(node.id);
	} else {
		next.add(node.id);
	}
	collapsedNodes.value = next;
}

function loadMore(targetNodeId: string, loadedCount: number) {
	const next = new Map(loadedCounts.value);
	next.set(targetNodeId, loadedCount + PAGE_LIMIT_PER_NODE);
	loadedCounts.value = next;
}

function getAllParentIds(): string[] {
	const trie = buildTrie(pages.value);
	const ids: string[] = [];
	function collect(map: Map<string, TrieNode>, parentPath: string) {
		for (const [label, trieNode] of map) {
			const fullPath = parentPath ? `${parentPath}/${label}` : label;
			if (trieNode.children.size > 0) {
				ids.push(fullPath);
				collect(trieNode.children, fullPath);
			}
		}
	}
	collect(trie, "");
	return ids;
}

function expandAll() {
	collapsedNodes.value = new Set();
}

function collapseAll() {
	collapsedNodes.value = new Set(getAllParentIds());
}

function isHomePage(page: BuilderPage): boolean {
	return builderSettings.doc?.home_page === page.route;
}

function refresh() {
	pagesResource.reload();
}

function setNodeRef(nodeId: string, element: HTMLElement | null) {
	if (element) {
		nodeEls.value.set(nodeId, element);
	} else {
		nodeEls.value.delete(nodeId);
	}
}

watchEffect(() => {
	if (!initialized.value && pages.value.length > 0) {
		initialized.value = true;
		if (pages.value.length > AUTO_COLLAPSE_THRESHOLD) {
			collapseAll();
		}
	}
});

watch([() => props.searchFilter, () => props.activeFolder], () => {
	if (props.searchFilter) return; // search force-expands nodes in the trie traversal
	if (pages.value.length > AUTO_COLLAPSE_THRESHOLD) {
		collapseAll();
	} else {
		expandAll();
	}
});

function regularNodes(): Node[] {
	return flattenNodes(treeNodes.value);
}

function currentNodes() {
	const nodes = regularNodes();
	const idx = focusedNodeId.value ? nodes.findIndex((n) => n.id === focusedNodeId.value) : -1;
	return { nodes, idx };
}

function focusNode(idx: number, nodes: Node[]) {
	if (idx < 0 || idx >= nodes.length) return;
	focusedNodeId.value = nodes[idx].id;
	nodeEls.value.get(nodes[idx].id)?.scrollIntoView({ block: "nearest" });
}

const treeActive = () => regularNodes().length > 0;

useShortcut([
	{
		key: "ArrowDown",
		description: "Move down in page tree",
		group: "Page Tree",
		condition: treeActive,
		handler: () => {
			const { nodes, idx } = currentNodes();
			focusNode(idx === -1 ? 0 : idx + 1, nodes);
		},
	},
	{
		key: "ArrowUp",
		description: "Move up in page tree",
		group: "Page Tree",
		condition: treeActive,
		handler: () => {
			const { nodes, idx } = currentNodes();
			focusNode(Math.max(0, idx - 1), nodes);
		},
	},
	{
		key: "ArrowRight",
		description: "Expand node or move down in page tree",
		group: "Page Tree",
		condition: treeActive,
		handler: () => {
			const { nodes, idx } = currentNodes();
			const node = nodes[idx];
			if (!node) {
				focusNode(0, nodes);
				return;
			}
			if (node.hasChildren && collapsedNodes.value.has(node.id)) {
				toggleNode(node);
			} else {
				focusNode(idx + 1, nodes);
			}
		},
	},
	{
		key: "ArrowLeft",
		description: "Collapse node or move up in page tree",
		group: "Page Tree",
		condition: treeActive,
		handler: () => {
			const { nodes, idx } = currentNodes();
			const node = nodes[idx];
			if (!node) return;
			if (node.hasChildren && !collapsedNodes.value.has(node.id)) {
				toggleNode(node);
			} else {
				focusNode(idx - 1, nodes);
			}
		},
	},
	{
		key: "Enter",
		description: "Open page or toggle folder in page tree",
		group: "Page Tree",
		condition: treeActive,
		handler: () => {
			const { nodes, idx } = currentNodes();
			const node = nodes[idx];
			if (!node) return;
			activateNode(node);
		},
	},
]);

defineExpose({ expandAll, collapseAll, refresh });
</script>
