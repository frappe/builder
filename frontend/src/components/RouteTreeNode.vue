<template>
	<template v-for="node in nodes" :key="node.id">
		<section class="relative">
			<div
				class="group flex cursor-pointer select-none items-center gap-1.5 border-b border-outline-gray-1 px-1 hover:rounded-md hover:bg-surface-gray-1"
				:class="[
					node.hasChildren ? 'sticky bg-surface-base shadow-[0_1px_0_var(--border-color)]' : '',
					{ 'rounded-md !bg-surface-gray-2': focusedNodeId === node.id },
				]"
				:ref="
					(el) => {
						setNodeRef(node.id, el as HTMLElement | null);
					}
				"
				:style="{
					marginLeft: `${node.depth * 24}px`,
					height: `${stickyRowHeight}px`,
					top: node.hasChildren ? `${node.stickyStackDepth * stickyRowHeight}px` : undefined,
					zIndex: node.hasChildren ? String(100 - node.stickyStackDepth) : undefined,
				}"
				@click="onSelect(node)"
				@dblclick="onActivate(node)">
				<Button
					v-if="node.hasChildren"
					variant="ghost"
					class="!text-ink-gray-5"
					@click.stop="onToggle(node)"
					:icon="node.expanded ? 'lucide-chevron-down' : 'lucide-chevron-right'"></Button>
				<span v-else class="size-6 w-7 shrink-0"></span>

				<div v-if="node.page" class="flex min-w-0 flex-1 items-center gap-1.5 py-0.5">
					<code class="shrink-0 py-0.5 font-mono text-sm text-ink-gray-6 group-hover:text-ink-gray-9">
						/{{ node.label }}
					</code>
					<span
						v-if="node.page.page_title"
						class="truncate text-sm text-ink-gray-4"
						:title="node.page.page_title">
						{{ node.page.page_title }}
					</span>
					<span class="ml-auto mr-1 flex shrink-0 items-center gap-1">
						<Tooltip v-if="isHomePage(node.page)" text="Home page" :hoverDelay="0.5">
							<HomeIcon class="size-3.5 text-ink-green-6" />
						</Tooltip>
						<Tooltip
							v-if="node.page.authenticated_access"
							text="This page has limited access"
							:hoverDelay="0.5">
							<span class="lucide-shield-user size-3.5 text-ink-amber-6" />
						</Tooltip>
						<Tooltip v-if="!node.page.published" text="Not published" :hoverDelay="0.5">
							<span class="lucide-globe-x size-3.5 text-ink-gray-4" />
						</Tooltip>
					</span>
				</div>

				<div v-else class="flex min-w-0 flex-1 items-center gap-1 py-0.5">
					<span class="font-mono text-sm text-ink-gray-6 group-hover:text-ink-gray-9">/{{ node.label }}</span>
				</div>

				<PageActionsDropdown v-if="node.page" :page="node.page" size="xs" placement="right">
					<Button
						icon="lucide-more-horizontal"
						size="sm"
						variant="ghost"
						class="bg-surface-base !text-ink-gray-5 hover:!text-ink-gray-9"
						@click.stop></Button>
				</PageActionsDropdown>
			</div>

			<RouteTreeBranch
				v-if="node.hasChildren && node.expanded"
				:nodes="node.children"
				:focused-node-id="focusedNodeId"
				:sticky-row-height="stickyRowHeight"
				:on-select="onSelect"
				:on-toggle="onToggle"
				:on-activate="onActivate"
				:on-load-more="onLoadMore"
				:set-node-ref="setNodeRef"
				:is-home-page="isHomePage" />
			<div
				v-if="node.hasChildren && node.expanded && node.hasMore"
				class="flex items-center pt-2"
				:style="{ marginLeft: `${node.depth * 24 + 8 + 32}px` }">
				<button
					class="flex items-center gap-1 text-xs text-ink-gray-4 hover:text-ink-gray-7"
					@click="onLoadMore(node.id, node.loadedCount)">
					<span class="lucide-more-horizontal size-3" aria-hidden="true" />
					Load {{ Math.min(PAGE_LIMIT_PER_NODE, node.totalCount - node.loadedCount) }} more
					<span class="ml-0.5 text-ink-gray-3">({{ node.totalCount - node.loadedCount }} remaining)</span>
				</button>
			</div>
		</section>
	</template>
</template>

<script setup lang="ts">
import PageActionsDropdown from "@/components/PageActionsDropdown.vue";
import { BuilderPage } from "@/types/doctypes";
import { Tooltip } from "frappe-ui";
import HomeIcon from "~icons/lucide/house";

defineOptions({ name: "RouteTreeBranch" });

const PAGE_LIMIT_PER_NODE = 50;

interface TreeNode {
	id: string;
	label: string;
	fullPath: string;
	depth: number;
	stickyStackDepth: number;
	page: BuilderPage | null;
	hasChildren: boolean;
	expanded: boolean;
	parentId: string | null;
	children: TreeNode[];
	hasMore: boolean;
	loadedCount: number;
	totalCount: number;
}

defineProps<{
	nodes: TreeNode[];
	focusedNodeId: string | null;
	stickyRowHeight: number;
	onSelect: (node: TreeNode) => void;
	onToggle: (node: TreeNode) => void;
	onActivate: (node: TreeNode) => void;
	onLoadMore: (targetNodeId: string, loadedCount: number) => void;
	setNodeRef: (nodeId: string, element: HTMLElement | null) => void;
	isHomePage: (page: BuilderPage) => boolean;
}>();
</script>
