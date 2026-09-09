<template>
	<div ref="arrayEditor" class="flex flex-col gap-2" @paste="pasteArray">
		<div v-for="(item, index) in arr" :key="index" class="flex gap-2">
			<ImageUploadInput
				v-if="itemType === 'image'"
				class="w-full"
				:placeholder="__('Enter image URL or upload one')"
				:modelValue="itemURL(item)"
				:imageFit="(itemFit(item) || 'cover') as 'contain' | 'cover' | 'fill'"
				:objectPosition="itemPosition(item)"
				:targetRatio="targetRatio"
				@update:modelValue="(val: string) => updateImageItem(index, { url: val })"
				@update:imageFit="(val: string) => updateImageItem(index, { fit: val })"
				@update:objectPosition="(val: string) => updateImageItem(index, { position: val })" />
			<BuilderInput
				v-else
				:placeholder="__('Enter value')"
				:modelValue="itemURL(item)"
				@input="(val: string) => updateItem(index, val)" />
			<Button
				class="flex-shrink-0 text-xs"
				variant="subtle"
				icon="lucide-x"
				@click="deleteItem(index)"></Button>
		</div>
		<Button variant="outline" class="w-full" :label="__('Add')" @click="addItem"></Button>
		<p class="rounded-sm bg-surface-gray-1 p-2 text-xs text-ink-gray-7" v-show="description">
			<span v-html="description"></span>
		</p>
	</div>
</template>
<script setup lang="ts">
import { nextTick, ref } from "vue";
import ImageUploadInput from "./ImageUploadInput.vue";

const props = defineProps<{
	arr: Array<ArrayPropItem>;
	description?: string;
	itemType?: "string" | "image";
	targetRatio?: number;
}>();

const emit = defineEmits({
	"update:arr": (arr: Array<ArrayPropItem>) => true,
});

const itemURL = (item: ArrayPropItem) => (typeof item === "string" ? item : item?.url || "");
const itemFit = (item: ArrayPropItem) => (typeof item === "string" ? "" : item?.fit || "");
const itemPosition = (item: ArrayPropItem) => (typeof item === "string" ? "" : item?.position || "");

const addItem = async () => {
	const newArr = [...props.arr, ""];
	emit("update:arr", newArr);
	await nextTick();
	const inputs = arrayEditor.value?.querySelectorAll("input:not([type='file'])");
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

const updateImageItem = (index: number, patch: { url?: string; fit?: string; position?: string }) => {
	const newArr = [...props.arr];
	const current = newArr[index];
	const url = patch.url ?? itemURL(current);
	const fit = patch.fit ?? itemFit(current);
	const position = patch.position ?? itemPosition(current);
	if (fit || position) {
		const image: ImageArrayItem = { url };
		if (fit) image.fit = fit;
		if (position) image.position = position;
		newArr[index] = image;
	} else {
		newArr[index] = url;
	}
	emit("update:arr", newArr);
};

const deleteItem = (index: number) => {
	const newArr = [...props.arr];
	newArr.splice(index, 1);
	emit("update:arr", newArr);
};

const arrayEditor = ref<HTMLElement | null>(null);

const pasteArray = (e: ClipboardEvent) => {
	const passedArr = props.arr.filter((item) => itemURL(item).trim() !== "");
	const text = e.clipboardData?.getData("text/plain");
	if (text) {
		e.preventDefault();
		try {
			// Try to parse as JSON array first
			const parsed = JSON.parse(text);
			if (Array.isArray(parsed)) {
				const stringArray = parsed.map((item) => String(item));
				emit("update:arr", [...passedArr, ...stringArray]);
				return;
			}
		} catch (e) {
			// If JSON parsing fails, try other formats
		}

		// Try to parse as comma-separated values
		if (text.includes(",")) {
			const items = text
				.split(",")
				.map((item) => item.trim())
				.filter((item) => item);
			emit("update:arr", [...passedArr, ...items]);
			return;
		}

		// Try to parse as line-separated values
		if (text.includes("\n")) {
			const items = text
				.split("\n")
				.map((item) => item.trim())
				.filter((item) => item);
			emit("update:arr", [...passedArr, ...items]);
			return;
		}

		// Single item
		emit("update:arr", [...passedArr, text.trim()]);
	}
};
</script>
