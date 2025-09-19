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
		class="border-gray text-gray12 focus-visible:border-gray6 placeholder-gray10 w-full rounded border border-transparent bg-transparent text-xs focus:border-transparent focus:outline-none focus:ring-0" />
</template>
