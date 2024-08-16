<template>
	<div
		class="toolbar flex h-14 items-center justify-center bg-white p-2 shadow-sm dark:border-b-[1px] dark:border-gray-800 dark:bg-zinc-900">
		<div class="absolute left-3 flex items-center gap-3">
			<!-- go back -->
			<FeatherIcon
				name="chevron-left"
				class="h-6 w-6 cursor-pointer !text-gray-700 dark:!text-gray-200"
				@click="$router.back()"></FeatherIcon>
		</div>
	</div>
</template>
<script setup lang="ts">
import useStore from "@/store";
import { ref } from "vue";

const store = useStore();
const isDark = ref(false);
</script>
