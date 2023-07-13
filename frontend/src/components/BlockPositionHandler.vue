<template>
	<div>
		<h3 class="mb-1 text-xs font-bold uppercase text-gray-600">Position</h3>
		<div class="grid grid-cols-3 grid-rows-3 gap-2">
			<Input
				type="text"
				placeholder="top"
				v-model="top"
				class="col-span-1 col-start-2 h-8 w-16 self-end justify-self-center rounded-md text-center text-xs text-gray-800 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200 dark:focus:bg-zinc-700" />
			<Input
				type="text"
				placeholder="left"
				v-model="left"
				class="col-span-1 col-start-1 h-8 w-16 self-center justify-self-end rounded-md text-center text-xs text-gray-800 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200 dark:focus:bg-zinc-700" />
			<div
				class="grid-col-3 grid h-16 w-16 grid-rows-3 gap-1 self-center justify-self-center rounded bg-gray-50 p-2 dark:bg-zinc-800">
				<div
					class="col-span-3 row-start-1 h-2 w-[2px] self-center justify-self-center rounded bg-gray-400 dark:bg-zinc-900"></div>
				<div
					class="col-span-3 row-start-3 h-2 w-[2px] self-center justify-self-center rounded bg-gray-400 dark:bg-zinc-900"></div>
				<div
					class="h-5 w-5 self-center justify-self-center rounded bg-gray-400 shadow-md dark:bg-zinc-900"></div>
				<div
					class="col-span-1 col-start-1 row-start-2 h-[2px] w-2 self-center justify-self-center rounded bg-gray-400 dark:bg-zinc-900"></div>
				<div
					class="col-span-1 col-start-3 row-start-2 h-[2px] w-2 self-center justify-self-center rounded bg-gray-400 dark:bg-zinc-900"></div>
			</div>
			<Input
				type="text"
				placeholder="right"
				v-model="right"
				class="col-span-1 col-start-3 h-8 w-16 self-center justify-self-start rounded-md text-center text-xs text-gray-800 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200 dark:focus:bg-zinc-700" />
			<Input
				type="text"
				placeholder="bottom"
				v-model="bottom"
				class="col-span-1 col-start-2 h-8 w-16 self-start justify-self-center rounded-md text-center text-xs text-gray-800 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200 dark:focus:bg-zinc-700" />
		</div>
		<RadioGroup v-model="position" class="m-auto flex w-fit items-center justify-between">
			<div
				class="flex h-fit w-fit flex-row gap-x-1 rounded-md bg-gray-100 p-[4px] dark:bg-zinc-800 dark:text-zinc-300">
				<RadioGroupOption
					:value="pos.value"
					v-slot="{ active, checked }"
					v-for="pos in [
						{
							value: 'static',
							label: 'Auto',
						},
						{
							value: 'absolute',
							label: 'Free',
						},
						{
							value: 'fixed',
							label: 'Fixed',
						},
						{
							value: 'sticky',
							label: 'Sticky',
						},
					]">
					<span
						:class="{
							'bg-gray-300 font-medium dark:bg-zinc-700': active || checked,
							'text-gray-600': !(active || checked),
						}"
						class="block cursor-pointer rounded px-2 py-1 text-xs">
						{{ pos.label }}
					</span>
				</RadioGroupOption>
			</div>
		</RadioGroup>
	</div>
</template>
<script setup lang="ts">
import Block from "@/utils/block";
import blockController from "@/utils/blockController";
import { RadioGroup, RadioGroupOption } from "@headlessui/vue";
import { PropType, computed } from "vue";

const top = computed({
	get() {
		return blockController.getStyle("top");
	},
	set(value: string) {
		blockController.setStyle("top", value);
	},
});

const right = computed({
	get() {
		return blockController.getStyle("right");
	},
	set(value: string) {
		blockController.setStyle("right", value);
	},
});

const left = computed({
	get() {
		return blockController.getStyle("left");
	},
	set(value: string) {
		blockController.setStyle("left", value);
	},
});

const bottom = computed({
	get() {
		return blockController.getStyle("bottom");
	},
	set(value: string) {
		blockController.setStyle("bottom", value);
	},
});

const position = computed({
	get() {
		return blockController.getStyle("position") || "static";
	},
	set(value: string) {
		blockController.setStyle("position", value);
		const parentBlock = blockController.getParentBlock();
		if (parentBlock) {
			parentBlock.setStyle("position", "relative");
		}
	},
});
</script>
