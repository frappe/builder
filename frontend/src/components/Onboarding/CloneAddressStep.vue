<template>
	<form class="flex flex-col gap-5" @submit.prevent="emit('next')">
		<TextInput
			v-model="address"
			type="text"
			size="md"
			variant="subtle"
			placeholder="yourbusiness.com"
			autofocus />
		<Button
			type="submit"
			variant="solid"
			size="md"
			class="w-full"
			:label="__('Next')"
			:disabled="!address.trim()" />
	</form>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import { Button, TextInput } from "frappe-ui";

const address = defineModel<string>({ required: true });
const emit = defineEmits<{ next: [] }>();
</script>
