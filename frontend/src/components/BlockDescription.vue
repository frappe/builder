<template>
	<div></div>
</template>
<script lang="ts" setup>
import Block from "@/utils/block";

const props = defineProps({
	block: {
		type: Block,
		required: true,
	},
});
</script>
