<template>
	<div ref="arrayEditor" class="flex flex-col gap-2" @paste="pasteArray">
		<div v-for="(item, index) in arr" :key="index" class="flex gap-2">
			<BuilderInput
				placeholder="Enter value"
				:modelValue="item"
				@input="(val: string) => updateItem(index, val)" />
			<BuilderButton
				class="flex-shrink-0 text-xs"
				variant="subtle"
				icon="x"
				@click="deleteItem(index)"></BuilderButton>
		</div>
		<BuilderButton variant="subtle" class="w-full" label="Add" @click="addItem"></BuilderButton>
		<p class="rounded-sm bg-surface-gray-1 p-2 text-xs text-ink-gray-7" v-show="description">
			<span v-html="description"></span>
		</p>
	</div>
</template>
<script setup lang="ts">
import { nextTick, ref } from "vue";

const props = defineProps<{
	arr: Array<string>;
	description?: string;
}>();

const emit = defineEmits({
	"update:arr": (arr: Array<string>) => true,
});

const addItem = async () => {
	const newArr = [...props.arr, ""];
	emit("update:arr", newArr);
	await nextTick();
	const inputs = arrayEditor.value?.querySelectorAll("input");
	if (inputs) {
		const lastInput = inputs[inputs.length - 1];
		lastInput.focus();
	}
};

const updateItem = (index: number, value: string) => {
	const newArr = [...props.arr];
	newArr[index] = value;
	emit("update:arr", newArr);
};

const deleteItem = (index: number) => {
	const newArr = [...props.arr];
	newArr.splice(index, 1);
	emit("update:arr", newArr);
};

const arrayEditor = ref<HTMLElement | null>(null);

const pasteArray = (e: ClipboardEvent) => {
	const passedArr = props.arr.filter(item => item.trim() !== "");
	const text = e.clipboardData?.getData("text/plain");
	if (text) {
		e.preventDefault();
		try {
			// Try to parse as JSON array first
			const parsed = JSON.parse(text);
			if (Array.isArray(parsed)) {
				const stringArray = parsed.map(item => String(item));
				emit("update:arr", [...passedArr, ...stringArray]);
				return;
			}
		} catch (e) {
			// If JSON parsing fails, try other formats
		}
		
		// Try to parse as comma-separated values
		if (text.includes(",")) {
			const items = text.split(",").map(item => item.trim()).filter(item => item);
			emit("update:arr", [...passedArr, ...items]);
			return;
		}
		
		// Try to parse as line-separated values
		if (text.includes("\n")) {
			const items = text.split("\n").map(item => item.trim()).filter(item => item);
			emit("update:arr", [...passedArr, ...items]);
			return;
		}
		
		// Single item
		emit("update:arr", [...passedArr, text.trim()]);
	}
};
</script>
