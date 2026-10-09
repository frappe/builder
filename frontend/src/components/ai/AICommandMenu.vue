<template>
	<!-- mousedown.prevent throughout: the composer keeps focus, so typing keeps filtering -->
	<div
		class="absolute inset-x-0 bottom-full z-10 mb-1.5 overflow-hidden rounded-5 border border-outline-gray-2 bg-surface-base shadow-lg">
		<div v-if="level" class="flex items-center gap-1 pl-1 pr-2.5 pt-1">
			<button
				class="flex size-6 shrink-0 items-center justify-center rounded-4 text-ink-gray-5 hover:bg-surface-gray-2"
				aria-label="Back"
				@mousedown.prevent="menu.back()">
				<span class="lucide-chevron-left size-3.5" />
			</button>
			<span class="truncate text-xs font-medium text-ink-gray-7">{{ breadcrumb }}</span>
			<span v-if="busy" class="lucide-loader-circle ml-auto size-3.5 shrink-0 animate-spin text-ink-gray-4" />
		</div>

		<p v-if="note" class="px-2.5 pt-2 text-p-xs" :class="noteIsError ? 'text-ink-red-6' : 'text-ink-gray-6'">
			{{ note }}
		</p>

		<form v-if="level?.input" class="px-2 py-2" @submit.prevent="submitField">
			<input
				ref="field"
				v-model="fieldValue"
				:type="level.input.secret ? 'password' : 'text'"
				:placeholder="level.input.placeholder"
				autocomplete="off"
				class="w-full rounded-4 border border-outline-gray-2 bg-surface-gray-2 px-2 py-1 text-sm text-ink-gray-8 placeholder-ink-gray-4 focus:border-outline-gray-4 focus:bg-surface-base focus:ring-0"
				@keydown.esc.prevent.stop="menu.back()" />
		</form>

		<div v-if="items.length" role="listbox" class="max-h-72 overflow-y-auto py-1">
			<template v-for="(item, index) in items" :key="item.key">
				<div
					v-if="item.group && item.group !== items[index - 1]?.group"
					class="px-2.5 pb-0.5 pt-2 text-xs text-ink-gray-5">
					{{ item.group }}
				</div>
				<button
					role="option"
					:aria-selected="index === highlighted"
					class="flex w-full items-center gap-2 px-2.5 py-1.5 text-left"
					:class="index === highlighted ? 'bg-surface-gray-2' : ''"
					@mouseenter="activeIndex = index"
					@mousedown.prevent="menu.choose(item)">
					<span
						v-if="item.checked !== undefined"
						class="size-3.5 shrink-0 text-ink-gray-8"
						:class="item.checked ? 'lucide-check' : ''" />
					<span v-else :class="[item.icon, 'size-3.5 shrink-0 text-ink-gray-5']" />
					<span class="truncate text-sm" :class="item.danger ? 'text-ink-red-6' : 'text-ink-gray-8'">
						{{ item.label }}
					</span>
					<span v-if="item.hint" class="ml-auto max-w-[55%] shrink-0 truncate pl-2 text-xs text-ink-gray-5">
						{{ item.hint }}
					</span>
				</button>
			</template>
		</div>
		<p v-else-if="level && !level.input && !busy" class="px-2.5 py-2 text-p-xs text-ink-gray-5">
			{{ level.empty || "Nothing matches" }}
		</p>
	</div>
</template>

<script setup lang="ts">
import type { CommandMenu } from "@/components/ai/commandMenu";
import { computed, nextTick, ref, watch } from "vue";

const props = defineProps<{ menu: CommandMenu }>();
const { stack, level, visibleItems: items, note, noteIsError, busy, activeIndex } = props.menu;

const breadcrumb = computed(() => stack.value.map((l) => l.title).join(" › "));
// Enter belongs to the field on a level that has one, so no row may look like it would run
const highlighted = computed(() => (level.value?.input ? -1 : activeIndex.value));

const field = ref<HTMLInputElement | null>(null);
const fieldValue = ref("");

watch(level, async () => {
	fieldValue.value = "";
	await nextTick();
	field.value?.focus();
});

const submitField = () => props.menu.submit(fieldValue.value.trim());
</script>
