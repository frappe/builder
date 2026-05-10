<template>
	<div>
		<div
			v-for="node in visibleNodes"
			:key="node.id"
			class="group flex items-center gap-1.5 rounded-md p-1 hover:bg-surface-gray-1"
			:style="{ paddingLeft: `${node.depth * 20 + 4}px` }">
			<!-- expand/collapse button or spacer -->
			<Button
				v-if="node.hasChildren"
				variant="ghost"
				@click="toggleNode(node)"
				:icon="node.expanded ? 'chevron-down' : 'chevron-right'"></Button>
			<span v-else class="size-4 shrink-0"></span>

			<!-- icon: slash for path segments, file for leaf pages only -->
			<FeatherIcon v-if="node.hasChildren" name="hash" class="size-3.5 shrink-0 text-ink-gray-4" />
			<FeatherIcon v-else name="file-text" class="size-3.5 shrink-0 text-ink-gray-4" />

			<!-- URL segment label + page title -->
			<router-link
				v-if="node.page"
				:to="{ name: 'builder', params: { pageId: node.page.page_name } }"
				class="flex min-w-0 flex-1 items-center gap-2">
				<span class="shrink-0 font-mono text-sm font-medium text-ink-gray-9">/{{ node.label }}</span>
				<span
					v-if="node.page.page_title"
					class="truncate text-sm text-ink-gray-5"
					:title="node.page.page_title">
					{{ node.page.page_title }}
				</span>
				<Badge
					v-if="node.page.published"
					theme="green"
					class="ml-auto shrink-0 text-xs dark:bg-green-900 dark:text-green-400">
					Published
				</Badge>
			</router-link>
			<button v-else class="flex min-w-0 flex-1 items-center gap-1" @click="toggleNode(node)">
				<span class="font-mono text-sm font-medium text-ink-gray-7">/{{ node.label }}</span>
			</button>

			<PageActionsDropdown v-if="node.page" :page="node.page" size="xs" placement="right">
				<template v-slot="{ open }">
					<BuilderButton
						icon="more-horizontal"
						size="sm"
						variant="subtle"
						class="bg-surface-white !text-ink-gray-5 hover:!text-ink-gray-9"
						@click="open"></BuilderButton>
				</template>
			</PageActionsDropdown>
		</div>
	</div>
</template>

<script setup lang="ts">
import PageActionsDropdown from "@/components/PageActionsDropdown.vue";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { Badge } from "frappe-ui";
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

// "collapsedNodes" set — nodes not in this set are expanded (default: all expanded)
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

			result.push({ id, label, fullPath, depth, page: trieNode.page, hasChildren, expanded, parentId });

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
</script>
