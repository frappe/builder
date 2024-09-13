<template>
	<Switch
		v-model="value"
		class="[&>span>[id^=headlessui-description]]:text-text-icons-gray-5 [&>span>[id^=headlessui-label]]:text-text-icons-gray-9"
		:class="{
			'[&>button]:bg-surface-gray-1': !value,
			'[&>button]:bg-surface-gray-4': value,
		}" />
</template>
<script setup lang="ts">
import { useVModel } from "@vueuse/core";
import { Switch } from "frappe-ui";

const props = defineProps<{
	modelValue: string;
}>();
const emit = defineEmits(["update:modelValue"]);
const value = useVModel(props, "modelValue", emit);
</script>
