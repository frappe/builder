<template>
	<details class="mt-2">
		<summary class="cursor-pointer select-none text-[11px] text-ink-gray-5 hover:text-ink-gray-6">
			Updated {{ totalCount }} block{{ totalCount !== 1 ? "s" : "" }}
		</summary>
		<div class="mt-1.5 flex flex-col gap-0.5">
			<button
				v-for="block in affectedBlocks"
				:key="block.block_id"
				class="flex w-full flex-col items-start rounded px-1.5 py-0.5 text-left hover:bg-surface-gray-2"
				@click="$emit('select-block', block.block_id)">
				<span class="text-[12px] font-medium text-ink-gray-7">{{ block.blockName || block.element }}</span>
				<span v-if="block.changedProps.length" class="text-[10px] text-ink-gray-4">
					{{ block.changedProps.join(", ") }}
				</span>
			</button>
			<button
				v-for="script in affectedScripts"
				:key="script.script_name"
				class="flex w-full flex-col items-start rounded px-1.5 py-0.5 text-left hover:bg-surface-gray-2"
				@click="$emit('open-script', script.script_name)">
				<span class="text-[12px] font-medium text-ink-gray-7">{{ script.script_name }}</span>
				<span v-if="script.changedProps.length" class="text-[10px] text-ink-gray-4">
					{{ script.changedProps.join(", ") }}
				</span>
			</button>
		</div>
	</details>
</template>

<script setup lang="ts">
import type { AffectedBlock, AffectedScript } from "@/components/AIChatController";
import { computed } from "vue";

const props = defineProps<{
	affectedBlocks: AffectedBlock[];
	affectedScripts: AffectedScript[];
}>();

defineEmits<{
	"select-block": [blockId: string];
	"open-script": [scriptName: string];
}>();

const totalCount = computed(() => props.affectedBlocks.length + props.affectedScripts.length);
</script>
