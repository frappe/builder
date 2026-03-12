<template>
	<Dialog
		v-model="showDialog"
		:options="{
			title: 'Keyboard Shortcuts',
			size: '4xl',
		}">
		<template #body-content>
			<div class="max-h-[70vh] columns-2 gap-8 overflow-y-auto">
				<div
					v-for="(shortcuts, group) in groupedShortcuts"
					:key="group"
					class="mb-4 break-inside-avoid last:mb-0">
					<h3 class="mb-1 text-xs font-semibold uppercase tracking-wider text-ink-gray-9">
						{{ group }}
					</h3>
					<div class="flex flex-col">
						<div
							v-for="shortcut in shortcuts"
							:key="shortcut.description"
							class="flex items-center justify-between rounded py-1.5">
							<span class="text-sm text-ink-gray-6">{{ shortcut.description }}</span>
							<div class="flex items-center gap-0.5">
								<kbd
									v-for="(part, i) in formatShortcutParts(shortcut)"
									:key="i"
									class="inline-flex min-w-[22px] items-center justify-center rounded border border-outline-gray-2 bg-surface-gray-1 px-1.5 py-0.5 font-medium text-ink-gray-7"
									:class="part.isSymbol ? 'text-base' : 'text-[11px]'">
									{{ part.label }}
								</kbd>
							</div>
						</div>
					</div>
				</div>
				<div v-if="!activeShortcuts.length" class="py-8 text-center text-sm text-ink-gray-5">
					No keyboard shortcuts available on this page.
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import Dialog from "@/components/Controls/Dialog.vue";
import { getActiveShortcuts, type RegisteredShortcut } from "@/utils/useShortcut";
import { computed, ref } from "vue";

const showDialog = ref(false);
const activeShortcuts = getActiveShortcuts();

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

const groupedShortcuts = computed(() => {
	const groups: Record<string, RegisteredShortcut[]> = {};
	for (const shortcut of activeShortcuts) {
		if (!groups[shortcut.group]) {
			groups[shortcut.group] = [];
		}
		groups[shortcut.group].push(shortcut);
	}
	return groups;
});

defineExpose({ showDialog });
</script>
