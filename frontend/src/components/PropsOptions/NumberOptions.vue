<template>
    <div class="flex items-center justify-between">
		<InputLabel>Min. Value</InputLabel>
		<Input placeholder="Enter min value"></Input>
	</div>
    <div class="flex items-center justify-between">
		<InputLabel>Max. Value</InputLabel>
		<Input placeholder="Enter max value"></Input>
	</div>
	<div class="flex items-center justify-between">
		<InputLabel>Default Value</InputLabel>
		<Input placeholder="Enter default value"></Input>
	</div>
</template>

<script setup lang="ts">
import InputLabel from "@/components/Controls/InputLabel.vue";
import Input from "@/components/Controls/Input.vue";
</script>
