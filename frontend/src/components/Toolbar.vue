<template>
	<div class="toolbar bg-gray-300 p-4 flex justify-between">
		<span>MakeIt</span>
		<Button appearance="primary" @click="publish">Publish</Button>
	</div>
</template>
<script setup>

let publish = () => {
	console.log('publish');
}
</script>