<template>
	<Popover :offset="20" placement="left">
		<template #target="{ open }">
			<div class="relative flex w-full gap-2">
				<div class="flex w-[88px] shrink-0 items-center">
					<InputLabel class="truncate">
						{{ label }}
					</InputLabel>
				</div>
				<div class="relative w-full">
					<BuilderButton class="w-full" variant="subtle" icon="edit-2" @click.stop="open()" />
				</div>
			</div>
		</template>
		<template #body="{ open, close }">
			<div
				@click.stop
				@mousedown.stop
				class="flex max-h-60 w-60 flex-col gap-3 overflow-auto rounded-lg bg-surface-white p-4 shadow-lg">
				<div class="text-sm text-ink-gray-8">Object Items:</div>
				<ObjectEditor :obj @update:obj="updateModelValue" />
			</div>
		</template>
	</Popover>
</template>

<script setup lang="ts">
import { ref } from "vue";
import ObjectEditor from "./ObjectEditor.vue";
import InputLabel from "./Controls/InputLabel.vue";
import { Popover } from "frappe-ui";
import BuilderButton from "./Controls/BuilderButton.vue";

const props = defineProps<{
	label: string;
	getModelValue: () => string;
	setModelValue: (value: string) => void;
}>();

const emit = defineEmits({
	"update:modelValue": (value: string) => true,
});

const getPassedObject = () => {
	try {
		const value = props.getModelValue();
		const parsed = JSON.parse(value);
		if (typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)) {
			return parsed;
		}
		return {};
	} catch {
		return {};
	}
};

const obj = ref<Record<string, string>>(getPassedObject());

const updateModelValue = (value: Record<string, string>) => {
	obj.value = value;
	props.setModelValue(JSON.stringify(value));
	emit("update:modelValue", JSON.stringify(value));
};
</script>
