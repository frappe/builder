<template>
	<Transition
		enter-active-class="transition duration-300 ease-out"
		enter-from-class="-translate-y-2 opacity-0"
		leave-active-class="transition duration-200 ease-in"
		leave-to-class="-translate-y-2 opacity-0">
		<div
			v-if="showTip && editorDemoStage.isOpen.value"
			class="pointer-events-none fixed left-1/2 top-[calc(var(--toolbar-height)+12px)] z-20 flex -translate-x-1/2 items-center gap-2 rounded-full bg-surface-gray-7 py-1.5 pl-4 pr-1.5 text-sm text-ink-white shadow-xl">
			<span class="lucide-mouse-pointer-click size-4" aria-hidden="true" />
			<span>{{ __("Double-click any text to edit it, or drag blocks around. Nothing is saved.") }}</span>
			<button
				class="pointer-events-auto grid size-6 place-items-center rounded-full hover:bg-white/15"
				:aria-label="__('Dismiss')"
				@click="showTip = false">
				<span class="lucide-x size-3.5" aria-hidden="true" />
			</button>
		</div>
	</Transition>
</template>
<script setup lang="ts">
import { editorDemoStage } from "@/components/EditorDemo/editorDemoStage";
import { __ } from "@/translation";
import { onLauncherMessage, postToLauncher } from "@/utils/editorDemo";
import { onMounted, ref } from "vue";

const showTip = ref(false);
let welcomed = false;

function welcome() {
	if (welcomed) return;
	welcomed = showTip.value = true;
	setTimeout(() => (showTip.value = false), 9000);
}

onMounted(() => {
	editorDemoStage.start();
	if (!editorDemoStage.framed) {
		editorDemoStage.isOpen.value = true;
		return welcome();
	}
	onLauncherMessage(async ({ type, scrollY = 0, target, dark = false }) => {
		if (type === "prepare") editorDemoStage.prepare(scrollY, target, dark);
		if (type === "play") editorDemoStage.play().then(welcome);
		if (type === "close") editorDemoStage.exit();
	});
	postToLauncher({ type: "booted" });
});
</script>
