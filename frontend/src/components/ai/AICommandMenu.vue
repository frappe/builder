<template>
	<!-- mousedown.prevent throughout: the composer keeps focus, so typing keeps filtering -->
	<div
		class="absolute inset-x-0 bottom-full z-10 mb-1.5 divide-y divide-outline-elevation-2 overflow-hidden rounded-6 bg-surface-elevation-2 shadow-2xl ring-1 ring-black ring-opacity-5">
		<div v-if="level" class="flex items-center gap-1 p-1.5">
			<Button
				variant="ghost"
				size="sm"
				icon="lucide-chevron-left"
				label="Back"
				@mousedown.prevent="menu.back()" />
			<span class="truncate text-sm font-medium text-ink-gray-7">{{ breadcrumb }}</span>
			<LoadingIndicator v-if="busy" class="ml-auto mr-1 size-4 shrink-0 text-ink-gray-4" />
		</div>

		<div v-if="note || level?.input" class="flex flex-col gap-2 p-2">
			<p v-if="note" class="text-p-sm" :class="noteIsError ? 'text-ink-red-6' : 'text-ink-gray-6'">
				{{ note }}
			</p>
			<form v-if="level?.input" @submit.prevent="submitField" @keydown.esc.prevent.stop="menu.back()">
				<component
					:is="level.input.secret ? Password : TextInput"
					ref="field"
					v-model="fieldValue"
					:placeholder="level.input.placeholder"
					autocomplete="off" />
			</form>
		</div>

		<div
			v-if="sections.length"
			ref="list"
			role="listbox"
			class="relative max-h-72 divide-y divide-outline-elevation-2 overflow-y-auto">
			<div v-for="section in sections" :key="section.key" class="p-1.5">
				<div
					v-if="section.group"
					class="flex h-7 items-center px-2 text-sm font-medium leading-tighter text-ink-gray-4">
					{{ section.group }}
				</div>
				<ItemListRow
					v-for="{ item, index } in section.rows"
					:key="item.key"
					role="option"
					class="cursor-pointer"
					:aria-selected="index === highlighted"
					:active="index === highlighted"
					@mouseenter="hover(index)"
					@mousedown.prevent="menu.choose(item)">
					<!-- the same row frappe-ui's Dropdown draws (MenuItemContent): the icon slot is
					     kept for the whole section once any row has an icon, so labels line up -->
					<template v-if="section.hasIcons" #prefix>
						<span
							:class="[
								item.icon,
								'size-4 shrink-0',
								item.theme === 'red' ? 'text-ink-red-7' : 'text-ink-gray-6',
							]" />
					</template>
					<div class="min-w-0">
						<div
							class="truncate leading-tighter"
							:class="item.theme === 'red' ? 'text-ink-red-7' : 'text-ink-gray-7'">
							{{ item.label }}
						</div>
						<div v-if="item.description" class="truncate text-p-sm text-ink-gray-5">
							{{ item.description }}
						</div>
					</div>
					<template v-if="item.switchValue !== undefined || item.selected || item.submenu" #suffix>
						<!-- the row toggles it, so the switch only shows the state -->
						<Switch
							v-if="item.switchValue !== undefined"
							class="pointer-events-none"
							tabindex="-1"
							:modelValue="item.switchValue" />
						<span v-else-if="item.selected" class="lucide-check ml-1 size-4 text-ink-gray-6" />
						<span v-else class="lucide-chevron-right size-4 shrink-0 text-ink-gray-6" />
					</template>
				</ItemListRow>
			</div>
		</div>
		<p v-else-if="level && !level.input && !busy" class="px-3.5 py-3 text-base text-ink-gray-5">
			{{ level.empty || "Nothing matches" }}
		</p>
	</div>
</template>

<script setup lang="ts">
import type { CommandMenu, MenuItem } from "@/components/ai/commandMenu";
import { Button, ItemListRow, LoadingIndicator, Password, Switch, TextInput } from "frappe-ui";
import { computed, nextTick, ref, watch } from "vue";

const props = defineProps<{ menu: CommandMenu }>();
const { stack, level, visibleItems: items, note, noteIsError, busy, activeIndex } = props.menu;

const breadcrumb = computed(() => stack.value.map((l) => l.title).join(" › "));
// Enter belongs to the field on a level that has one, so no row may look like it would run
const highlighted = computed(() => (level.value?.input ? -1 : activeIndex.value));

// consecutive rows that share a group render as one Dropdown-style group
const sections = computed(() => {
	const out: { key: string; group?: string; hasIcons: boolean; rows: { item: MenuItem; index: number }[] }[] =
		[];
	items.value.forEach((item, index) => {
		let section = out.at(-1);
		if (!section || section.group !== item.group) {
			section = { key: `${index}-${item.group ?? ""}`, group: item.group, hasIcons: false, rows: [] };
			out.push(section);
		}
		section.rows.push({ item, index });
		section.hasIcons ||= !!item.icon;
	});
	return out;
});

const field = ref<{ focus: () => void } | null>(null);
const fieldValue = ref("");

watch(level, async () => {
	fieldValue.value = "";
	await nextTick();
	field.value?.focus();
});

const submitField = () => props.menu.submit(fieldValue.value.trim());

const list = ref<HTMLElement | null>(null);
let pointed = false;

// the row under the pointer is already in view, and scrolling to it would fight the wheel
function hover(index: number) {
	if (activeIndex.value === index) return;
	pointed = true;
	activeIndex.value = index;
}

watch(highlighted, async (index) => {
	if (pointed) return void (pointed = false);
	await nextTick();
	const option = list.value?.querySelectorAll<HTMLElement>("[role=option]")[index];
	if (list.value && option) keepInView(list.value, option);
});

// the first row of a group brings the group's label and padding along
function keepInView(list: HTMLElement, option: HTMLElement) {
	const section = option.parentElement;
	const opensSection = section?.querySelector("[role=option]") === option;
	const top = opensSection && section ? section.offsetTop : option.offsetTop;
	const bottom = option.offsetTop + option.offsetHeight;
	if (top < list.scrollTop) list.scrollTop = top;
	else if (bottom > list.scrollTop + list.clientHeight) list.scrollTop = bottom - list.clientHeight;
}
</script>
