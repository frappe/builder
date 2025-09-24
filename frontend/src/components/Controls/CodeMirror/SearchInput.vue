<script setup lang="ts">
import { ref } from "vue";

const value = defineModel<string>();
const inputRef = ref<HTMLInputElement | null>(null);

function select() {
	inputRef.value?.focus();
	inputRef.value?.select();
}

defineExpose({
	select,
});
</script>

<template>
	<input
		ref="inputRef"
		v-model="value"
		type="text"
		class="px-2.5 focus-visible:border-gray-6 w-full rounded border border-transparent bg-transparent text-xs text-ink-gray-8 placeholder-ink-gray-6 focus:border-transparent focus:outline-none focus:ring-0" />
</template>
