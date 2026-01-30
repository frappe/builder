<template>
	<Switch v-model="value" class="!px-0" />
</template>
<script setup lang="ts">
import { useVModel } from "@vueuse/core";
import { Switch } from "frappe-ui";

const props = defineProps<{
	modelValue: boolean;
}>();
const emit = defineEmits(["update:modelValue"]);
const value = useVModel(props, "modelValue", emit);
</script>
