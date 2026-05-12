<template>
	<div>
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
			<template v-for="node in visibleNodes" :key="node.id">
				<!-- Load more row -->
				<div
					v-if="node.isLoadMore"
					class="flex items-center pt-2"
					:style="{ marginLeft: `${node.depth * 24 + 8 + 32}px` }">
					<button
						class="flex items-center gap-1 text-xs text-ink-gray-4 hover:text-ink-gray-7"
						@click="loadMore(node)">
						<FeatherIcon name="more-horizontal" class="size-3" />
						Load {{ Math.min(PAGE_LIMIT_PER_NODE, node.totalCount - node.loadedCount) }} more
						<span class="ml-0.5 text-ink-gray-3">({{ node.totalCount - node.loadedCount }} remaining)</span>
					</button>
				</div>

				<!-- Regular tree node -->
				<div
					v-else
					class="group flex cursor-pointer items-center gap-1.5 border-b border-outline-gray-1 px-1 py-1 hover:rounded-md hover:bg-surface-gray-1"
					:class="{ 'rounded-md !bg-surface-gray-2 ': focusedNodeId === node.id }"
					:ref="
						(el) => {
							if (el) nodeEls.set(node.id, el as HTMLElement);
						}
					"
					:style="{ marginLeft: `${node.depth * 24}px` }"
					@click="selectNode(node)"
					@dblclick="activateNode(node)">
					<Button
						v-if="node.hasChildren"
						variant="ghost"
						class="!text-ink-gray-5"
						@click.stop="toggleNode(node)"
						:icon="node.expanded ? 'chevron-down' : 'chevron-right'"></Button>
					<span v-else class="size-6 w-7 shrink-0"></span>

					<!-- Page node label row -->
					<div v-if="node.page" class="flex min-w-0 flex-1 items-center gap-1.5 py-0.5">
						<code
							class="shrink-0 py-0.5 font-mono text-sm text-ink-gray-6 group-hover:text-ink-gray-9"
							:class="{
								'font-semibold': node.hasChildren,
							}">
							/{{ node.label }}
						</code>
						<span
							v-if="node.page.page_title"
							class="truncate text-sm text-ink-gray-4"
							:title="node.page.page_title">
							{{ node.page.page_title }}
						</span>
						<span class="ml-auto flex shrink-0 items-center gap-1">
							<Tooltip v-if="isHomePage(node.page)" text="Home page" :hoverDelay="0.5">
								<HomeIcon class="size-3.5 text-ink-green-3" />
							</Tooltip>
							<Tooltip
								v-if="node.page.authenticated_access"
								text="This page has limited access"
								:hoverDelay="0.5">
								<AuthenticatedUserIcon class="size-3.5 text-ink-amber-3" />
							</Tooltip>
							<Tooltip v-if="!node.page.published" text="Not published" :hoverDelay="0.5">
								<GlobeOffIcon class="size-3.5 text-ink-gray-4" />
							</Tooltip>
						</span>
					</div>

					<!-- Folder node label -->
					<div v-else class="flex min-w-0 flex-1 items-center gap-1 py-0.5">
						<span
							class="font-mono text-sm text-ink-gray-6 group-hover:text-ink-gray-9"
							:class="{
								'font-semibold': node.hasChildren,
							}">
							/{{ node.label }}
						</span>
					</div>

					<PageActionsDropdown v-if="node.page" :page="node.page" size="xs" placement="right">
						<template v-slot="{ open }">
							<BuilderButton
								icon="more-horizontal"
								size="sm"
								variant="subtle"
								class="bg-surface-white !text-ink-gray-5 hover:!text-ink-gray-9"
								@click.stop></BuilderButton>
						</template>
					</PageActionsDropdown>
				</div>
			</template>
		</div>
	</div>
</template>

<script setup lang="ts">
import AuthenticatedUserIcon from "@/components/Icons/AuthenticatedUser.vue";
import GlobeOffIcon from "@/components/Icons/GlobeOff.vue";
import PageActionsDropdown from "@/components/PageActionsDropdown.vue";
import { builderSettings } from "@/data/builderSettings";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { useShortcut } from "@/utils/useShortcut";
import { createListResource, Tooltip } from "frappe-ui";
import { computed, onBeforeUpdate, ref, watch, watchEffect } from "vue";
import { useRouter } from "vue-router";
import HomeIcon from "~icons/lucide/house";

const props = withDefaults(
	defineProps<{
		searchFilter?: string;
		activeFolder?: string;
	}>(),
	{ searchFilter: "", activeFolder: "" },
);

const PAGE_LIMIT_PER_NODE = 50;
const AUTO_COLLAPSE_THRESHOLD = 100;

const router = useRouter();

interface Node {
	id: string;
	label: string;
	fullPath: string;
	depth: number;
	page: BuilderPage | null;
	hasChildren: boolean;
	expanded: boolean;
	parentId: string | null;
	isLoadMore?: false;
}

interface LoadMoreNode {
	id: string;
	depth: number;
	parentId: string | null;
	isLoadMore: true;
	targetNodeId: string;
	loadedCount: number;
	totalCount: number;
}

type TreeNode = Node | LoadMoreNode;

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

const visibleNodes = computed<TreeNode[]>(() => {
	const trie = buildTrie(pages.value);
	const result: TreeNode[] = [];

	function traverse(map: Map<string, TrieNode>, depth: number, parentPath: string, parentId: string | null) {
		const entries = Array.from(map.entries());
		const limitKey = parentId ?? "__root__";
		const limit = getLimit(limitKey);
		const visible = entries.slice(0, limit);

		for (const [label, trieNode] of visible) {
			const fullPath = parentPath ? `${parentPath}/${label}` : label;
			const id = fullPath;
			const hasChildren = trieNode.children.size > 0;
			const expanded = !!props.searchFilter || !collapsedNodes.value.has(id);

			result.push({
				id,
				label,
				fullPath,
				depth,
				page: trieNode.page,
				hasChildren,
				expanded,
				parentId,
			});

			if (hasChildren && expanded) {
				traverse(trieNode.children, depth + 1, fullPath, id);
			}
		}

		if (entries.length > limit) {
			result.push({
				id: `__load_more__${limitKey}`,
				depth,
				parentId,
				isLoadMore: true,
				targetNodeId: limitKey,
				loadedCount: limit,
				totalCount: entries.length,
			});
		}
	}

	traverse(trie, 0, "", null);
	return result;
});

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

function loadMore(node: LoadMoreNode) {
	const next = new Map(loadedCounts.value);
	next.set(node.targetNodeId, node.loadedCount + PAGE_LIMIT_PER_NODE);
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
	return visibleNodes.value.filter((n): n is Node => !n.isLoadMore);
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
