<template>
	<template v-for="node in nodes" :key="node.id">
		<section class="relative">
			<!-- runs from the folder row down past its last child, so nesting stays readable -->
			<span
				v-if="node.hasChildren && node.expanded"
				class="absolute bottom-0 w-0 border-l border-outline-gray-2"
				:style="{ top: `${stickyRowHeight}px`, left: `${node.depth * 24 + 18}px` }" />
			<div
				class="group flex cursor-pointer select-none items-center gap-1.5 rounded-5 px-1 hover:bg-surface-gray-1"
				:class="[
					node.hasChildren ? 'sticky bg-surface-base shadow-[0_1px_0_var(--border-color)]' : '',
					{ 'rounded-5 !bg-surface-gray-2': focusedNodeId === node.id },
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
					<!-- capped rather than shrinkable, so the title gives up room before the route does -->
					<code
						class="max-w-[50%] shrink-0 truncate py-0.5 font-mono text-sm text-ink-gray-8"
						:title="`/${node.label}`">
						/{{ node.label }}
					</code>
					<span
						v-if="node.page.page_title"
						class="truncate text-sm text-ink-gray-5"
						:title="node.page.page_title">
						{{ node.page.page_title }}
					</span>
					<span class="ml-auto flex shrink-0 items-center gap-2 pl-3">
						<Tooltip v-if="isHomePage(node.page)" :text="__('Home page')" :hoverDelay="500">
							<HomeIcon class="size-3.5 text-ink-gray-5" />
						</Tooltip>
						<Tooltip
							v-if="node.page.authenticated_access"
							:text="__('This page has limited access')"
							:hoverDelay="500">
							<span class="lucide-shield-user size-3.5 text-ink-amber-6" />
						</Tooltip>
						<!-- fixed width so the dots line up into a rail down the tree -->
						<span class="flex w-36 shrink-0 items-center">
							<UseTimeAgo v-slot="{ timeAgo }" :time="node.page.modified">
								<PageStatusLine :page="node.page" :time="timeAgo" />
							</UseTimeAgo>
						</span>
					</span>
				</div>

				<div v-else class="flex min-w-0 flex-1 items-center gap-1 py-0.5">
					<span class="truncate font-mono text-sm text-ink-gray-8">/{{ node.label }}</span>
				</div>

				<PageActionsDropdown v-if="node.page" :page="node.page" size="xs" align="end" v-slot="{ open }">
					<Button
						icon="lucide-more-horizontal"
						size="sm"
						variant="ghost"
						class="!text-ink-gray-5 opacity-0 hover:!text-ink-gray-9 focus-visible:opacity-100 group-hover:opacity-100"
						:class="{ '!opacity-100': focusedNodeId === node.id || open }"
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
					{{ __("Load {0} more", [Math.min(PAGE_LIMIT_PER_NODE, node.totalCount - node.loadedCount)]) }}
					<span class="ml-0.5 text-ink-gray-3">
						{{ __("({0} remaining)", [node.totalCount - node.loadedCount]) }}
					</span>
				</button>
			</div>
		</section>
	</template>
</template>

<script setup lang="ts">
import PageActionsDropdown from "@/components/PageActionsDropdown.vue";
import PageStatusLine from "@/components/PageStatusLine.vue";
import { __ } from "@/translation";
import { BuilderPage } from "@/types/doctypes";
import { UseTimeAgo } from "@vueuse/components";
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
