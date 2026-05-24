<template>
	<li>
		<button
			class="flex w-full items-center justify-between rounded px-2 py-1 text-left text-sm"
			:class="
				selected === node.path
					? 'bg-surface-gray-2 text-ink-gray-9'
					: 'text-ink-gray-7 hover:bg-surface-gray-1'
			"
			:style="{ paddingLeft: `${0.5 + depth * 0.75}rem` }"
			@click="$emit('select', node.path)">
			<span class="flex items-center gap-1">
				<span
					v-if="node.children.length"
					class="lucide-chevron-right h-3 w-3 transition-transform"
					:class="{ 'rotate-90': expanded }"
					@click.stop="expanded = !expanded"
					aria-hidden="true" />
				<span v-else class="w-3" aria-hidden="true" />
				{{ node.name }}
			</span>
			<span class="text-xs text-ink-gray-5">{{ node.count }}</span>
		</button>
		<ul v-if="expanded && node.children.length">
			<GroupNode
				v-for="child in node.children"
				:key="child.path"
				:node="child"
				:depth="depth + 1"
				:selected="selected"
				@select="(g: string) => $emit('select', g)" />
		</ul>
	</li>
</template>

<script setup lang="ts">
import { ref } from "vue";

interface TreeNode {
	name: string;
	path: string;
	count: number;
	children: TreeNode[];
}

defineProps<{
	node: TreeNode;
	depth: number;
	selected: string | null;
}>();

defineEmits<{
	select: [path: string];
}>();

const expanded = ref(true);
</script>
