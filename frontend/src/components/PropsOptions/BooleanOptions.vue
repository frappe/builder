<template>
	<div class="flex items-center justify-between">
		<InputLabel>True Option</InputLabel>
		<Input placeholder="Enter true option display"></Input>
	</div>
	<div class="flex items-center justify-between">
		<InputLabel>False Option</InputLabel>
		<Input placeholder="Enter false option display"></Input>
	</div>
	<div class="flex items-center justify-between">
		<InputLabel>Default Value</InputLabel>
		<Input type="select" :options="[
			{
				label: 'true',
				value: 'true'
			},
			{
				label: 'false',
				value: 'false'
			}
		]" placeholder="Enter default value"></Input>
	</div>
</template>

<script setup lang="ts">
import InputLabel from "@/components/Controls/InputLabel.vue";
import Input from "@/components/Controls/Input.vue";

</script>
