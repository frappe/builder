<template>
	<div class="flex items-start justify-between gap-2">
		<InputLabel class="h-7 w-1/3 min-w-[88px] shrink-0" :description="description">{{ label }}</InputLabel>
		<div ref="list" class="flex w-full min-w-0 flex-col gap-1.5">
			<BuilderInput
				v-for="(option, index) in options"
				:key="index"
				:modelValue="option"
				hideClearButton
				@input="(value: string) => emit('rename', index, value)"
				@paste="(event: ClipboardEvent) => pasteOptions(event, index)"
				@keydown.stop>
				<template v-if="!renameOnly" #suffix>
					<button
						type="button"
						class="text-ink-gray-4 hover:text-ink-gray-7"
						tabindex="-1"
						:title="__('Remove option')"
						@click="emit('remove', index)">
						<span class="lucide-x size-3.5" aria-hidden="true" />
					</button>
				</template>
			</BuilderInput>
			<Button
				v-if="!renameOnly"
				variant="subtle"
				icon-left="lucide-plus"
				:label="__('Add option')"
				class="w-full"
				@click="addOption" />
		</div>
	</div>
</template>

<script setup lang="ts">
import InputLabel from "@/components/Controls/InputLabel.vue";
import { __ } from "@/translation";
import { nextTick, ref } from "vue";

const props = defineProps<{
	label: string;
	options: string[];
	description?: string;
	// options can be renamed but not added or removed
	renameOnly?: boolean;
}>();

const emit = defineEmits<{
	rename: [index: number, label: string];
	remove: [index: number];
	add: [label: string, index?: number];
}>();

const list = ref<HTMLElement | null>(null);

// a pasted list becomes an option per line, in place of the option it is pasted into
const pasteOptions = (event: ClipboardEvent, index: number) => {
	const lines = (event.clipboardData?.getData("text") || "")
		.split(/\r?\n/)
		.map((line) => line.trim())
		.filter(Boolean);
	if (lines.length < 2 || props.renameOnly) return;
	event.preventDefault();
	emit("rename", index, lines[0]);
	lines.slice(1).forEach((line, i) => emit("add", line, index + 1 + i));
};

// focusing selects the new option's text, so typing replaces it
const addOption = async () => {
	emit("add", __("New option"));
	await nextTick();
	const inputs = list.value?.querySelectorAll("input");
	inputs?.[inputs.length - 1]?.focus();
};
</script>
