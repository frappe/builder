<template>
	<div>
		<div
			class="x fixed top-0 bottom-0 z-10 w-[1px] bg-pink-600"
			v-if="store.guides.showX"
			:style="{
				left: store.guides.x + 'px',
			}"></div>
		<div
			class="y fixed left-0 right-0 z-10 h-[1px] bg-pink-600"
			v-if="store.guides.showY"
			:style="{
				top: store.guides.y + 'px',
			}"></div>
	</div>
</template>
<script setup lang="ts">
import useStore from "../store";
const store = useStore();
</script>
