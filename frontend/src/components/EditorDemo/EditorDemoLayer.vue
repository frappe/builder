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
import useCanvasStore from "@/stores/canvasStore";
import { __ } from "@/translation";
import { onLauncherMessage, postToLauncher } from "@/utils/editorDemo";
import { onMounted, onUnmounted, ref, watch } from "vue";

const canvasStore = useCanvasStore();
const showTip = ref(false);
let stopListening = () => {};

watch(
	() => canvasStore.activeCanvas,
	(canvas) => canvas && editorDemoStage.matchLauncherWidth(),
	{ immediate: true },
);

let welcomed = false;

async function welcome() {
	if (welcomed) return;
	welcomed = true;
	showTip.value = true;
	await new Promise((resolve) => setTimeout(resolve, 9000));
	showTip.value = false;
}

onMounted(() => {
	editorDemoStage.start();
	if (!editorDemoStage.framed) {
		editorDemoStage.isOpen.value = true;
		welcome();
		return;
	}
	stopListening = onLauncherMessage(async (message) => {
		if (message.type === "prepare") {
			await editorDemoStage.prepare(message.scrollY, message.target ?? null);
		} else if (message.type === "play") {
			await editorDemoStage.play();
			welcome();
		} else if (message.type === "close") {
			editorDemoStage.exit();
		}
	});
	postToLauncher({ type: "booted" });
});

onUnmounted(() => stopListening());
</script>
