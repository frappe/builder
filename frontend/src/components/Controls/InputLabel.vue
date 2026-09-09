<template>
	<span class="flex min-w-0 items-center truncate text-xs leading-5 text-ink-gray-6">
		<span class="truncate"><slot /></span>
		<Tooltip v-if="description" placement="top">
			<span class="lucide-info ml-1 h-[12px] w-[12px] text-gray-500" aria-hidden="true" />
			<template #body>
				<slot name="body">
					<div
						class="my-4 w-fit max-w-52 rounded bg-gray-800 p-2 text-center text-p-xs text-white shadow-xl"
						v-html="description"></div>
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
