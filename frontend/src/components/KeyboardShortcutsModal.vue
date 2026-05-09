<template>
	<Dialog
		v-model="showDialog"
		:options="{
			title: 'Keyboard Shortcuts',
			size: '6xl',
		}">
		<template #body-content>
			<div class="flex max-h-[70vh] flex-col">
				<div v-if="shouldShowSearch" class="mb-5 w-fit">
					<Input
						v-model.trim="searchQuery"
						@input="searchQuery = $event"
						type="text"
						placeholder="Search shortcuts" />
				</div>
				<div class="grid grid-cols-1 gap-x-5 gap-y-4 overflow-y-auto pr-1 md:grid-cols-2 xl:grid-cols-3">
					<div v-for="(shortcuts, group) in filteredGroupedShortcuts" :key="group" class="space-y-1.5">
						<h3 class="text-sm font-semibold tracking-wide text-ink-gray-8">
							{{ group }}
						</h3>
						<div
							v-for="shortcut in shortcuts"
							:key="shortcut.id"
							class="flex items-start justify-between gap-3 rounded py-0.5">
							<span class="text-p-base text-ink-gray-6">{{ shortcut.description }}</span>
							<div class="flex shrink-0 items-center gap-1.5">
								<div
									v-for="(variant, variantIndex) in formatShortcutVariants(shortcut)"
									:key="`${shortcut.id.toString()}-${variantIndex}`"
									class="flex items-center gap-1">
									<kbd
										v-for="(part, i) in variant"
										:key="`${variantIndex}-${i}`"
										class="inline-flex h-5 min-w-5 items-center justify-center rounded border bg-surface-gray-2 px-1.5 text-[11px] font-medium text-ink-gray-7"
										:class="{
											'text-xs': !part.isSymbol,
										}">
										{{ part.label }}
									</kbd>
									<span v-if="variantIndex < shortcut.keys.length - 1" class="px-0.5 text-xs text-ink-gray-5">
										/
									</span>
								</div>
							</div>
						</div>
					</div>
				</div>

				<div v-if="!activeShortcuts.length" class="py-8 text-center text-sm text-ink-gray-5">
					No keyboard shortcuts available on this page.
				</div>
				<div
					v-else-if="shouldShowSearch && !hasVisibleShortcuts"
					class="py-8 text-center text-sm text-ink-gray-5">
					No shortcuts match your search.
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import Dialog from "@/components/Controls/Dialog.vue";
import { getActiveShortcuts, type ActiveShortcut } from "@/utils/useShortcut";
import { computed, ref } from "vue";

const showDialog = ref(false);
const activeShortcuts = getActiveShortcuts();
const searchQuery = ref("");

const isMac = navigator.platform.toUpperCase().indexOf("MAC") >= 0;

const keyMap: Record<string, string> = {
	arrowup: "↑",
	arrowdown: "↓",
	arrowleft: "←",
	arrowright: "→",
	escape: "Esc",
	backspace: "⌫",
	delete: "Del",
	enter: "↵",
	" ": "Space",
	"\\": "\\",
	"=": "+",
	"-": "−",
};

function formatShortcutParts(config: {
	key: string;
	ctrl?: boolean;
	shift?: boolean;
}): { label: string; isSymbol: boolean }[] {
	const parts: { label: string; isSymbol: boolean }[] = [];
	if (config.ctrl) parts.push({ label: isMac ? "⌘" : "Ctrl", isSymbol: isMac });
	if (config.shift) parts.push({ label: isMac ? "⇧" : "Shift", isSymbol: isMac });
	const displayKey = keyMap[config.key.toLowerCase()] ?? config.key.toUpperCase();
	const isSymbolKey = /^[↑↓←→⌫↵−]$/.test(displayKey);
	parts.push({ label: displayKey, isSymbol: isSymbolKey });
	return parts;
}

function formatShortcutVariants(shortcut: ActiveShortcut): { label: string; isSymbol: boolean }[][] {
	return shortcut.keys.map((key) =>
		formatShortcutParts({
			key,
			ctrl: shortcut.ctrl,
			shift: shortcut.shift,
		}),
	);
}

const groupedShortcuts = computed(() => {
	const groups: Record<string, ActiveShortcut[]> = {};
	for (const shortcut of activeShortcuts.value) {
		if (!groups[shortcut.group]) {
			groups[shortcut.group] = [];
		}
		groups[shortcut.group].push(shortcut);
	}
	return groups;
});

const shouldShowSearch = computed(() => activeShortcuts.value.length > 20);

const filteredGroupedShortcuts = computed(() => {
	if (!shouldShowSearch.value || !searchQuery.value) {
		return groupedShortcuts.value;
	}

	const query = searchQuery.value.toLowerCase();
	const filtered: Record<string, ActiveShortcut[]> = {};

	for (const [group, shortcuts] of Object.entries(groupedShortcuts.value)) {
		const groupMatches = group.toLowerCase().includes(query);
		const matchingShortcuts = groupMatches
			? shortcuts
			: shortcuts.filter((shortcut) => {
					const keyParts = formatShortcutVariants(shortcut)
						.flat()
						.map((part) => part.label.toLowerCase())
						.join(" ");
					return shortcut.description.toLowerCase().includes(query) || keyParts.includes(query);
				});

		if (matchingShortcuts.length) {
			filtered[group] = matchingShortcuts;
		}
	}

	return filtered;
});

const hasVisibleShortcuts = computed(() => Object.keys(filteredGroupedShortcuts.value).length > 0);

defineExpose({ showDialog });
</script>
