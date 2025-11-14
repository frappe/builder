<template>
	<div class="flex items-center justify-between">
		<InputLabel>Min. Items</InputLabel>
		<Input placeholder="Enter min number of items"></Input>
	</div>
	<div class="flex items-center justify-between">
		<InputLabel>Max. Items</InputLabel>
		<Input placeholder="Enter max number of items"></Input>
	</div>
	<div class="flex flex-col gap-3">
		<InputLabel>Default Items</InputLabel>
		<ObjectEditor :obj="obj" @update:obj="(newObj) => (obj = newObj)" />
	</div>
</template>

<script setup lang="ts">
import InputLabel from "@/components/Controls/InputLabel.vue";
import Input from "@/components/Controls/Input.vue";
import { ref } from "vue";
import ObjectEditor from "../ObjectEditor.vue";

const obj = ref<Record<string, any>>({});
</script>
