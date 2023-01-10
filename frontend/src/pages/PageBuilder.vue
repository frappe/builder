<template>
	<div class="flex-col bg-gray-100">
		<Toolbar class="z-10 relative"></Toolbar>
		<div class="flex justify-center">
			<Widgets></Widgets>
			<Canvas></Canvas>
			<div class="bg-gray-200 w-1/5 z-10 relative p-5"></div>
		</div>
	</div>
</template>

<script setup>
import Canvas from '../components/Canvas.vue';
import Toolbar from '../components/Toolbar.vue';
import Widgets from '../components/Widgets.vue';
</script>