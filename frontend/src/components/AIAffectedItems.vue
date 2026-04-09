<template>
	<div class="mt-2">
		<button
			class="flex items-center gap-1 text-[11px] text-ink-gray-4 hover:text-ink-gray-6"
			@click="open = !open">
			<FeatherIcon
				name="chevron-right"
				class="size-3 transition-transform duration-150"
				:class="open ? 'rotate-90' : ''" />
			{{ totalCount }} {{ totalCount === 1 ? "block" : "blocks" }} updated
		</button>
		<div v-if="open" class="mt-1 flex flex-col gap-px">
			<button
				v-for="block in affectedBlocks"
				:key="block.block_id"
				class="flex w-full flex-col rounded px-1.5 py-1 text-left hover:bg-surface-gray-2"
				@click="$emit('select-block', block.block_id)">
				<span class="text-[11px] font-medium text-ink-gray-7">{{ block.blockName || block.element }}</span>
				<span v-if="block.changedProps.length" class="truncate text-[10px] text-ink-gray-4">
					{{ block.changedProps.join(", ") }}
				</span>
			</button>
			<button
				v-for="script in affectedScripts"
				:key="script.script_name"
				class="flex w-full flex-col rounded px-1.5 py-1 text-left hover:bg-surface-gray-2"
				@click="$emit('open-script', script.script_name)">
				<span class="text-xs font-medium text-ink-gray-7">{{ script.script_name }}</span>
				<span v-if="script.changedProps.length" class="truncate text-[10px] text-ink-gray-4">
					{{ script.changedProps.join(", ") }}
				</span>
			</button>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { AffectedBlock, AffectedScript } from "@/components/AIChatController";
import { computed, ref } from "vue";

const props = defineProps<{
	affectedBlocks: AffectedBlock[];
	affectedScripts: AffectedScript[];
}>();

defineEmits<{
	"select-block": [blockId: string];
	"open-script": [scriptName: string];
}>();

const totalCount = computed(() => props.affectedBlocks.length + props.affectedScripts.length);
const open = ref(false);
</script>
