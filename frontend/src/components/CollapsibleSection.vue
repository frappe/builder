<template>
	<div>
		<div class="flex items-center justify-between text-sm font-medium dark:text-zinc-400">
			<h3 class="cursor-pointer text-base text-gray-900 dark:text-zinc-300" @click="toggleCollapsed">
				{{ sectionName }}
			</h3>
			<Button
				class="dark:text-zinc-400 dark:hover:bg-zinc-700"
				:icon="collapsed ? 'plus' : 'minus'"
				:variant="'ghost'"
				size="sm"
				@click="toggleCollapsed"></Button>
		</div>
		<div v-if="!collapsed">
			<div class="mb-4 mt-3 flex flex-col gap-3"><slot /></div>
		</div>
	</div>
</template>
<script lang="ts" setup>
import { ref, watch } from "vue";

const props = defineProps({
	sectionName: {
		type: String,
		required: true,
	},
	sectionCollapsed: {
		type: [Boolean, Object],
		default: false,
	},
});

const propCollapsed = ref(props.sectionCollapsed);
const collapsed = ref(false);

const toggleCollapsed = () => {
	collapsed.value = !collapsed.value;
};

watch(
	() => propCollapsed.value,
	(newVal) => {
		collapsed.value = newVal as boolean;
	},
	{ immediate: true },
);
</script>
