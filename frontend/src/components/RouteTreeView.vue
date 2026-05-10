<template>
	<div>
		<template v-for="(node, idx) in visibleNodes" :key="node.id">
			<div
				class="group flex items-center gap-1.5 border-b border-outline-gray-1 px-1 py-1 hover:rounded-md hover:bg-surface-gray-1"
				:style="{ marginLeft: `${node.depth * 24 + 4}px` }">
				<Button
					v-if="node.hasChildren"
					variant="ghost"
					@click="toggleNode(node)"
					:icon="node.expanded ? 'chevron-down' : 'chevron-right'"></Button>
				<span v-else class="size-6 shrink-0"></span>
				<FeatherIcon
					v-if="node.hasChildren"
					name="hash"
					class="size-3.5 shrink-0"
					:class="node.depth === 0 ? 'text-ink-gray-7' : 'text-ink-gray-4'" />
				<FeatherIcon v-else name="file-minus" class="size-3.5 shrink-0 text-ink-gray-4" />

				<router-link
					v-if="node.page"
					:to="{ name: 'builder', params: { pageId: node.page.page_name } }"
					class="flex min-w-0 flex-1 items-center gap-2 py-0.5">
					<code class="shrink-0 px-1.5 py-0.5 font-mono text-xs font-medium text-ink-gray-8">
						/{{ node.label }}
					</code>
					<span
						v-if="node.page.page_title"
						class="truncate text-sm text-ink-gray-5"
						:title="node.page.page_title">
						{{ node.page.page_title }}
					</span>
				</router-link>

				<button v-else class="flex min-w-0 flex-1 items-center gap-1 py-0.5" @click="toggleNode(node)">
					<span
						class="font-mono text-sm font-semibold"
						:class="node.depth === 0 ? 'text-ink-gray-8' : 'text-ink-gray-6'">
						/{{ node.label }}
					</span>
				</button>

				<PageActionsDropdown v-if="node.page" :page="node.page" size="xs" placement="right">
					<template v-slot="{ open }">
						<BuilderButton
							icon="more-horizontal"
							size="sm"
							variant="subtle"
							class="invisible bg-surface-white !text-ink-gray-5 hover:!text-ink-gray-9 group-hover:visible"
							@click="open"></BuilderButton>
					</template>
				</PageActionsDropdown>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import PageActionsDropdown from "@/components/PageActionsDropdown.vue";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { computed, ref } from "vue";

interface TreeNode {
	id: string;
	label: string;
	fullPath: string;
	depth: number;
	page: BuilderPage | null;
	hasChildren: boolean;
	expanded: boolean;
	parentId: string | null;
}

type TrieNode = {
	page: BuilderPage | null;
	children: Map<string, TrieNode>;
};

const props = defineProps<{
	pages: BuilderPage[];
}>();

const collapsedNodes = ref(new Set<string>());

function buildTrie(pages: BuilderPage[]): Map<string, TrieNode> {
	const root: Map<string, TrieNode> = new Map();
	for (const page of pages) {
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

const visibleNodes = computed<TreeNode[]>(() => {
	const trie = buildTrie(props.pages);
	const result: TreeNode[] = [];

	function traverse(map: Map<string, TrieNode>, depth: number, parentPath: string, parentId: string | null) {
		for (const [label, trieNode] of map) {
			const fullPath = parentPath ? `${parentPath}/${label}` : label;
			const id = fullPath;
			const hasChildren = trieNode.children.size > 0;
			const expanded = !collapsedNodes.value.has(id);

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
	}

	traverse(trie, 0, "", null);
	return result;
});

function toggleNode(node: TreeNode) {
	const next = new Set(collapsedNodes.value);
	if (next.has(node.id)) {
		next.delete(node.id);
	} else {
		next.add(node.id);
	}
	collapsedNodes.value = next;
}

function getAllParentIds(): string[] {
	const trie = buildTrie(props.pages);
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

defineExpose({ expandAll, collapseAll });
</script>
