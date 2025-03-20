<template>
	<div>
		<div class="flex items-center justify-between text-sm font-medium">
			<h3 class="cursor-pointer text-base text-ink-gray-9" @click="toggleCollapsed">
				{{ sectionName }}
			</h3>
			<BuilderButton
				:icon="collapsed ? 'chevron-right' : 'chevron-down'"
				:variant="'ghost'"
				size="sm"
				@click="toggleCollapsed"></BuilderButton>
		</div>
		<div v-if="!collapsed">
			<div class="mb-4 mt-3 flex flex-col gap-3"><slot /></div>
		</div>
	</div>
</template>
<script lang="ts" setup>
import { toValue } from "@vueuse/core";
import { ref, watch } from "vue";

const props = withDefaults(
	defineProps<{
		sectionName: string;
		sectionCollapsed?: boolean;
	}>(),
	{
		sectionCollapsed: false,
	},
);

const collapsed = ref(false);

const toggleCollapsed = () => {
	collapsed.value = !collapsed.value;
};

watch(
	() => props.sectionCollapsed,
	() => {
		collapsed.value = toValue(props.sectionCollapsed);
	},
	{ immediate: true },
);
</script>
