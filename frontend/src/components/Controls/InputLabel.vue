<template>
	<span class="inline-flex w-1/2 min-w-20 max-w-40 items-center text-xs leading-5 text-ink-gray-6">
		<slot />
		<Popover trigger="hover" v-if="description" placement="top">
			<template #target>
				<FeatherIcon name="info" class="ml-1 h-[12px] w-[12px] text-gray-500" />
			</template>
			<template #body>
				<slot name="body">
					<div
						class="my-4 w-fit max-w-52 rounded bg-gray-800 p-2 text-center text-p-xs text-white shadow-xl"
						v-html="description"></div>
				</slot>
			</template>
		</Popover>
	</span>
</template>
<script lang="ts" setup>
import { FeatherIcon, Popover } from "frappe-ui";
const props = withDefaults(
	defineProps<{
		description?: string;
	}>(),
	{
		description: "",
	},
);
</script>
