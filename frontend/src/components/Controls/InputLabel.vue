<template>
	<span class="flex w-[88px] min-w-16 items-center truncate text-xs leading-5 text-ink-gray-6">
		<span class="truncate"><slot /></span>
		<Tooltip v-if="description" side="top">
			<span class="lucide-info ml-1 h-[12px] w-[12px] text-gray-500" aria-hidden="true" />
			<template #content>
				<slot name="body">
					<div class="max-w-52 text-center text-p-xs" v-html="description"></div>
				</slot>
			</template>
		</Tooltip>
	</span>
</template>
<script lang="ts" setup>
import { Tooltip } from "frappe-ui";
const props = withDefaults(
	defineProps<{
		description?: string;
	}>(),
	{
		description: "",
	},
);
</script>
