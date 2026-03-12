<template>
	<Teleport to="body">
		<Transition name="shortcuts-fade">
			<div
				v-if="show"
				class="fixed inset-0 z-[10000] flex items-center justify-center"
				@click.self="close"
				@keydown.esc="close">
				<!-- Backdrop -->
				<div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="close" />

				<!-- Panel -->
				<div
					class="relative z-10 w-[640px] max-w-[90vw] max-h-[80vh] overflow-y-auto rounded-2xl border border-outline-gray-2 bg-surface-white shadow-2xl"
					role="dialog"
					aria-modal="true"
					aria-label="Keyboard shortcuts">
					<!-- Header -->
					<div class="sticky top-0 flex items-center justify-between border-b border-outline-gray-2 bg-surface-white px-6 py-4">
						<h2 class="text-p-lg font-semibold text-ink-gray-9">Keyboard Shortcuts</h2>
						<button
							@click="close"
							class="rounded-md p-1 text-ink-gray-5 transition-colors hover:bg-surface-gray-2 hover:text-ink-gray-8"
							aria-label="Close shortcuts panel">
							<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
								<line x1="18" y1="6" x2="6" y2="18" />
								<line x1="6" y1="6" x2="18" y2="18" />
							</svg>
						</button>
					</div>

					<!-- Shortcuts grid -->
					<div class="grid grid-cols-2 gap-x-8 gap-y-6 px-6 py-6">
						<div v-for="group in shortcutGroups" :key="group.title">
							<h3 class="mb-3 text-xs font-semibold uppercase tracking-wider text-ink-gray-4">{{ group.title }}</h3>
							<ul class="space-y-2">
								<li
									v-for="shortcut in group.shortcuts"
									:key="shortcut.label"
									class="flex items-center justify-between gap-4">
									<span class="text-p-sm text-ink-gray-7">{{ shortcut.label }}</span>
									<span class="flex shrink-0 items-center gap-1">
										<kbd
											v-for="key in shortcut.keys"
											:key="key"
											class="inline-flex min-w-[1.5rem] items-center justify-center rounded-md border border-outline-gray-3 bg-surface-gray-1 px-1.5 py-0.5 text-xs font-medium text-ink-gray-7 shadow-sm">
											{{ key }}
										</kbd>
									</span>
								</li>
							</ul>
						</div>
					</div>

					<!-- Footer hint -->
					<div class="border-t border-outline-gray-2 px-6 py-3 text-center">
						<span class="text-xs text-ink-gray-4">Press <kbd class="inline-flex items-center justify-center rounded border border-outline-gray-3 bg-surface-gray-1 px-1 text-xs font-medium text-ink-gray-6">?</kbd> to toggle this panel</span>
					</div>
				</div>
			</div>
		</Transition>
	</Teleport>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ show: boolean }>();
const emit = defineEmits<{ (e: "update:show", value: boolean): void }>();

const close = () => emit("update:show", false);

const isMac = computed(() => /Mac|iPhone|iPod|iPad/.test(navigator.userAgent));
const cmd = computed(() => (isMac.value ? "⌘" : "Ctrl"));

const shortcutGroups = computed(() => [
	{
		title: "Tools",
		shortcuts: [
			{ label: "Select tool", keys: ["V"] },
			{ label: "Move / Pan tool", keys: ["H"] },
			{ label: "Container block", keys: ["C"] },
			{ label: "Text block", keys: ["T"] },
			{ label: "Image block", keys: ["I"] },
		],
	},
	{
		title: "Canvas",
		shortcuts: [
			{ label: "Zoom in", keys: [cmd.value, "+"] },
			{ label: "Zoom out", keys: [cmd.value, "−"] },
			{ label: "Reset zoom (100%)", keys: [cmd.value, "0"] },
			{ label: "Fit page to screen", keys: [cmd.value, "⇧", "0"] },
			{ label: "Pan canvas", keys: ["← ↑ → ↓"] },
		],
	},
	{
		title: "Editing",
		shortcuts: [
			{ label: "Undo", keys: [cmd.value, "Z"] },
			{ label: "Redo", keys: [cmd.value, "⇧", "Z"] },
			{ label: "Save", keys: [cmd.value, "S"] },
			{ label: "Duplicate block", keys: [cmd.value, "D"] },
			{ label: "Copy styles", keys: [cmd.value, "⇧", "C"] },
			{ label: "Delete block", keys: ["⌫"] },
		],
	},
	{
		title: "Panels",
		shortcuts: [
			{ label: "Toggle right panel", keys: [cmd.value, "\\"] },
			{ label: "Toggle both panels", keys: [cmd.value, "⇧", "\\"] },
			{ label: "Focus property search", keys: [cmd.value, "F"] },
			{ label: "Preview page", keys: [cmd.value, "P"] },
			{ label: "Show keyboard shortcuts", keys: ["?"] },
		],
	},
]);
</script>

<style scoped>
.shortcuts-fade-enter-active,
.shortcuts-fade-leave-active {
	transition: opacity 0.15s ease;
}
.shortcuts-fade-enter-from,
.shortcuts-fade-leave-to {
	opacity: 0;
}

.shortcuts-fade-enter-active .relative,
.shortcuts-fade-leave-active .relative {
	transition: transform 0.15s ease;
}
.shortcuts-fade-enter-from .relative {
	transform: scale(0.97) translateY(8px);
}
.shortcuts-fade-leave-to .relative {
	transform: scale(0.97) translateY(8px);
}
</style>
