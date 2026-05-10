<template>
	<div class="path" :title="text">
		<span ref="start" class="start">{{ start }}</span>
		<span v-if="hasEllipsis">...</span>
		<span class="end">{{ end }}</span>
	</div>
</template>

<script setup>
import { computed, useTemplateRef } from "vue";

const props = defineProps({
	text: String,
});

const startSplitRef = useTemplateRef("start");

const splitIndex = computed(() => {
	return Math.floor(props.text.length - 16);
});

const start = computed(() => {
	return props.text.slice(0, splitIndex.value);
});

const end = computed(() => {
	return props.text.slice(splitIndex.value);
});

const hasEllipsis = computed(() => {
	if (startSplitRef.value) return startSplitRef.value.scrollWidth > startSplitRef.value.clientWidth;
	return false;
});
</script>

<style scoped>
.path {
	display: flex;
	overflow: hidden;
	white-space: nowrap;
	width: 100%;
}

.start {
	overflow: hidden;
	min-width: 0;
}

.end {
	flex-shrink: 0;
}
</style>
