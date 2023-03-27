<template>
	<div>
		<div class="x fixed top-0 bottom-0 w-[1px] bg-green-600 z-10" v-if="store.guides.showX" :style="{
			left: store.guides.x + 'px'
		}">
		</div>
		<div class="y fixed left-0 right-0 h-[1px] bg-green-600 z-10" v-if="store.guides.showY" :style="{
			top: store.guides.y + 'px'
		}"></div>
	</div>
</template>
<script setup>
import useStore from "../store";
const store = useStore();
</script>