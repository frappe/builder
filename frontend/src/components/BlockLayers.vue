<template>
	<div>
		<div v-for="block in blocks">
			<div class="ml-2">
				{{ block.element }}
				<div v-if="block.children">
					<BlockLayers :blocks="block.children"></BlockLayers>
				</div>
			</div>
		</div>
	</div>
</template>
<script setup>
defineProps(["blocks"]);
</script>