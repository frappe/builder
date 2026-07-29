<template>
	<div ref="host" class="flex h-full min-h-[inherit] w-full">
		<Teleport :to="mountPoint" v-if="mountPoint">
			<slot />
		</Teleport>
	</div>
</template>
<script setup lang="ts">
/**
 * Renders one breakpoint inside a shadow root.
 *
 * The slot content stays in the parent render scope, so provide/inject, stores,
 * and the block tree work as before. Only the rendered nodes move across the
 * boundary. This does not affect editor overlays: BuilderBlock already teleports
 * BlockEditor to the light DOM overlay element.
 */
import { registerCanvasShadowRoot } from "@/utils/canvasShadowDom";
import { ShadowStyleSync } from "@/utils/canvasShadowStyles";
import { Ref, onBeforeUnmount, onMounted, ref } from "vue";

const emit = defineEmits<{ ready: [ShadowRoot]; teardown: [] }>();

const host = ref(null) as Ref<HTMLElement | null>;
const mountPoint = ref(null) as Ref<HTMLElement | null>;

let styleSync: ShadowStyleSync | null = null;
let unregisterShadowRoot = () => {};

onMounted(() => {
	const shadowRoot = host.value?.attachShadow({ mode: "open" });
	if (!shadowRoot) return;
	styleSync = new ShadowStyleSync(shadowRoot);
	styleSync.start();
	unregisterShadowRoot = registerCanvasShadowRoot(shadowRoot);
	mountPoint.value = shadowRoot.appendChild(createMountPoint());
	emit("ready", shadowRoot);
});

onBeforeUnmount(() => {
	emit("teardown");
	styleSync?.stop();
	unregisterShadowRoot();
});

/**
 * Mirrors the canvas box so the block tree keeps the layout it had as a direct
 * child of .canvas. display:contents looks tidier, but it breaks the
 * min-height:inherit chain the root block relies on. It also breaks
 * getBoundingClientRect for any code that reads a block's parentElement.
 */
function createMountPoint() {
	const element = document.createElement("div");
	element.style.cssText = "display: flex; width: 100%; height: 100%; min-height: inherit;";
	return element;
}
</script>
