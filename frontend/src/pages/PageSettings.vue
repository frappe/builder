<template>
	<div class="h-screen w-full overflow-hidden bg-gray-200">
		<div
			class="toolbar relative z-10 flex h-14 items-center justify-center bg-white p-2 shadow-sm dark:border-b-[1px] dark:border-gray-800 dark:bg-zinc-900">
			<div class="absolute left-3 flex items-center gap-3">
				<!-- go back -->
				<FeatherIcon
					name="chevron-left"
					class="h-6 w-6 cursor-pointer !text-gray-700 dark:!text-gray-200"
					@click="$router.back()"></FeatherIcon>
			</div>
		</div>
		<div class="flex h-full flex-1">
			<div class="h-full w-72 bg-white shadow-sm"></div>
			<div class="m-auto mt-10 h-full w-2/4 max-w-4xl rounded bg-white p-5 shadow-sm">
				<span class="text-xl font-semibold">Page settings</span>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import useStore from "@/store";
import { ref } from "vue";

const store = useStore();
const isDark = ref(false);
</script>
