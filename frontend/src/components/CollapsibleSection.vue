<template>
	<div>
		<div
			class="flex cursor-pointer items-center justify-between text-sm dark:text-zinc-400"
			@click="toggleCollapsed">
			<h3 class="text-2xs font-bold uppercase text-gray-600">{{ sectionName }}</h3>
			<Button
				class="dark:text-zinc-400 dark:hover:bg-zinc-700"
				:icon="collapsed ? 'minus' : 'plus'"
				:variant="'ghost'"
				size="sm"></Button>
		</div>
		<div v-if="collapsed">
			<div class="mb-4 mt-3 flex flex-col gap-3"><slot /></div>
		</div>
	</div>
</template>
<script lang="ts" setup>
import { ref } from "vue";

const props = defineProps({
	sectionName: {
		type: String,
		required: true,
	},
	sectionCollapsed: {
		type: Boolean,
		default: true,
	},
});

const emit = defineEmits(["update:sectionCollapsed"]);
const collapsed = ref(props.sectionCollapsed);

const toggleCollapsed = () => {
	collapsed.value = !collapsed.value;
	emit("update:sectionCollapsed", collapsed.value);
};
</script>
