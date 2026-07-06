<template>
	<!-- Ambient "Bob is building" layer over the canvas region. Pure decoration:
	     never intercepts pointer events, so the live preview stays interactive.
	     Rendered inside .page-builder (not teleported) so --toolbar-height resolves. -->
	<Transition name="build-fade">
		<div v-if="active" class="ai-build-overlay pointer-events-none absolute z-40" :style="regionStyle">
			<!-- Top aurora: a soft bloom behind the pill + a light beam that scans across -->
			<div class="ai-beam" />
			<!-- A gentle glowing frame around the whole work area -->
			<div class="ai-frame" />

			<!-- Narrating status pill. Docked top-center of the canvas region — clear
			     of the bottom-center zoom control it used to collide with. -->
			<div class="pointer-events-none absolute inset-x-0 top-5 flex justify-center px-6">
				<div class="ai-pill flex max-w-full items-center gap-2.5 rounded-full py-2 pl-2.5 pr-4">
					<span class="ai-orb">
						<span class="ai-orb-core" />
						<span class="ai-orb-ring" />
						<span class="ai-orb-ring ai-orb-ring--2" />
					</span>
					<Transition name="status-swap" mode="out-in">
						<span :key="statusItem.text" class="flex min-w-0 items-center gap-1.5">
							<span class="ai-phrase-icon" v-html="statusIconSvg" />
							<span class="ai-shine truncate text-p-sm font-medium">{{ statusItem.text }}</span>
						</span>
					</Transition>
				</div>
			</div>
		</div>
	</Transition>

	<!-- One-shot completion flourish: a ring that expands and fades once. -->
	<Transition name="flourish">
		<div v-if="showDone" class="ai-done pointer-events-none absolute z-40" :style="regionStyle">
			<div class="ai-done-ring" />
			<div class="pointer-events-none absolute inset-x-0 top-5 flex justify-center px-6">
				<div class="ai-pill ai-pill--done flex items-center gap-2 rounded-full py-2 pl-3 pr-4">
					<span class="text-ink-white lucide-sparkles size-4" />
					<span class="text-ink-white text-p-sm font-medium">Page ready</span>
				</div>
			</div>
		</div>
	</Transition>
</template>

<script setup lang="ts">
import { lucideSVG } from "@/components/ai/lucideIcon";
import useBuilderStore from "@/stores/builderStore";
import { computed, ref, watch } from "vue";

const builderStore = useBuilderStore();

const active = computed(() => builderStore.aiBuildingCanvas);

/** Only ever show what's actually true. `aiBuildStatus` is Bob's real per-round
 * line from the backend (his own words, "Thinking with …", "Now editing …", or
 * the generic "Building the page…" during the generation stream). We never invent
 * sub-steps — an honest fallback covers the gap before the first line arrives. */
function iconFor(msg: string): string {
	const m = msg.toLowerCase();
	if (m.includes("another page")) return "file-pen-line";
	if (m.includes("thinking")) return "sparkles";
	if (m.includes("building the page")) return "layout-template";
	return "sparkles";
}
const statusItem = computed<{ text: string; icon: string }>(() => {
	const text = (builderStore.aiBuildStatus || "").trim() || "Building your page…";
	return { text, icon: iconFor(text) };
});
// Inline SVG (from bundled lucide-static) — reliable regardless of the icon-class
// build scanner; stroke=currentColor, so it takes the pill's accent color.
const statusIconSvg = computed(() => lucideSVG(statusItem.value.icon, 2));

/** The overlay hugs the same rectangle the canvas occupies — between the panels,
 * below the toolbar. Mirrors the inline geometry the two BuilderCanvas mounts use. */
const regionStyle = computed(() => {
	const left = builderStore.showLeftPanel
		? builderStore.builderLayout.leftPanelWidth + builderStore.builderLayout.optionsPanelWidth
		: 0;
	const right = builderStore.showRightPanel ? builderStore.builderLayout.rightPanelWidth : 0;
	return {
		top: "var(--toolbar-height)",
		bottom: "0px",
		left: `${left}px`,
		right: `${right}px`,
	};
});

// Fire the completion flourish when a build settles (tick bumps), but only if a
// build was actually on screen — the tick also increments on quiet timeouts.
const showDone = ref(false);
let hideTimer: ReturnType<typeof setTimeout> | null = null;
watch(
	() => builderStore.aiBuildDoneTick,
	() => {
		showDone.value = true;
		if (hideTimer) clearTimeout(hideTimer);
		hideTimer = setTimeout(() => (showDone.value = false), 1600);
	},
);
</script>

<style scoped>
/* --- Top aurora bloom + scanning beam ------------------------------------- */
/* A soft colored bloom pooled at the top of the canvas, behind the pill —
   the visible "something is happening here" cue, reliable on any canvas color. */
.ai-beam {
	position: absolute;
	top: 0;
	left: 0;
	right: 0;
	height: 160px;
	overflow: hidden;
	border-top-left-radius: 16px;
	border-top-right-radius: 16px;
	background: radial-gradient(
		130% 150px at 50% -30px,
		rgb(139 92 246 / 0.3),
		rgb(236 72 153 / 0.12) 45%,
		transparent 72%
	);
	animation: ai-breathe-opacity 3.6s ease-in-out infinite;
}
/* A thin light beam that scans left→right across the top edge. */
.ai-beam::after {
	content: "";
	position: absolute;
	top: 0;
	left: -35%;
	width: 35%;
	height: 2px;
	background: linear-gradient(90deg, transparent, #a78bfa 40%, #ec4899 60%, transparent);
	filter: blur(0.3px);
	animation: ai-scan 2.6s cubic-bezier(0.45, 0, 0.55, 1) infinite;
}
@keyframes ai-scan {
	0% {
		left: -35%;
	}
	100% {
		left: 100%;
	}
}
@keyframes ai-breathe-opacity {
	0%,
	100% {
		opacity: 0.65;
	}
	50% {
		opacity: 1;
	}
}

/* A gentle glowing frame that hugs the whole work area. */
.ai-frame {
	position: absolute;
	inset: 8px;
	border-radius: 16px;
	box-shadow:
		inset 0 0 0 1.5px rgb(139 92 246 / 0.28),
		inset 0 0 44px rgb(139 92 246 / 0.08);
	animation: ai-breathe-opacity 3.6s ease-in-out infinite;
}

/* --- Status pill ---------------------------------------------------------- */
.ai-pill {
	background: rgb(24 24 27 / 0.92);
	backdrop-filter: blur(8px);
	box-shadow:
		0 8px 30px -6px rgb(0 0 0 / 0.35),
		0 0 0 1px rgb(255 255 255 / 0.08),
		0 0 24px -4px rgb(139 92 246 / 0.45);
}
.ai-pill--done {
	background: linear-gradient(120deg, #7c3aed, #ec4899);
	box-shadow:
		0 10px 34px -6px rgb(0 0 0 / 0.4),
		0 0 30px -2px rgb(236 72 153 / 0.5);
}

/* --- Orb ------------------------------------------------------------------ */
.ai-orb {
	position: relative;
	display: grid;
	place-items: center;
	width: 18px;
	height: 18px;
}
.ai-orb-core {
	width: 8px;
	height: 8px;
	border-radius: 999px;
	background: radial-gradient(circle at 30% 30%, #fff, #a78bfa 55%, #6366f1);
	box-shadow: 0 0 10px 1px rgb(167 139 250 / 0.9);
	animation: ai-breathe 1.8s ease-in-out infinite;
}
.ai-orb-ring {
	position: absolute;
	inset: 0;
	border-radius: 999px;
	border: 1.5px solid rgb(167 139 250 / 0.6);
	animation: ai-ripple 1.8s ease-out infinite;
}
.ai-orb-ring--2 {
	animation-delay: 0.9s;
}
@keyframes ai-breathe {
	0%,
	100% {
		transform: scale(0.85);
		opacity: 0.85;
	}
	50% {
		transform: scale(1.1);
		opacity: 1;
	}
}
@keyframes ai-ripple {
	0% {
		transform: scale(0.5);
		opacity: 0.7;
	}
	100% {
		transform: scale(1.5);
		opacity: 0;
	}
}

/* --- Per-phrase contextual icon ------------------------------------------- */
.ai-phrase-icon {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 14px;
	height: 14px;
	flex: none;
	color: #c4b5fd; /* the inline SVG uses stroke=currentColor */
}
.ai-phrase-icon :deep(svg) {
	width: 100%;
	height: 100%;
}

/* --- Shimmering status text ---------------------------------------------- */
.ai-shine {
	background: linear-gradient(100deg, #c4b5fd 20%, #ffffff 50%, #c4b5fd 80%);
	background-size: 200% auto;
	-webkit-background-clip: text;
	background-clip: text;
	-webkit-text-fill-color: transparent;
	animation: ai-shine 2.4s linear infinite;
}
@keyframes ai-shine {
	from {
		background-position: 200% center;
	}
	to {
		background-position: -200% center;
	}
}

/* --- Completion flourish -------------------------------------------------- */
.ai-done-ring {
	position: absolute;
	inset: 10px;
	border-radius: 18px;
	border: 2px solid rgb(236 72 153 / 0.7);
	box-shadow: 0 0 30px 2px rgb(236 72 153 / 0.35);
	animation: ai-done-pulse 1.2s ease-out forwards;
}
@keyframes ai-done-pulse {
	0% {
		opacity: 0;
		transform: scale(0.985);
	}
	30% {
		opacity: 1;
	}
	100% {
		opacity: 0;
		transform: scale(1.01);
	}
}

/* --- Transitions ---------------------------------------------------------- */
.build-fade-enter-active,
.build-fade-leave-active {
	transition: opacity 0.5s ease;
}
.build-fade-enter-from,
.build-fade-leave-to {
	opacity: 0;
}
.flourish-enter-active {
	transition: opacity 0.25s ease;
}
.flourish-leave-active {
	transition: opacity 0.6s ease;
}
.flourish-enter-from,
.flourish-leave-to {
	opacity: 0;
}

/* Gentle crossfade as the status line rotates */
.status-swap-enter-active,
.status-swap-leave-active {
	transition:
		opacity 0.3s ease,
		transform 0.3s ease;
}
.status-swap-enter-from {
	opacity: 0;
	transform: translateY(3px);
}
.status-swap-leave-to {
	opacity: 0;
	transform: translateY(-3px);
}

@media (prefers-reduced-motion: reduce) {
	.ai-beam,
	.ai-beam::after,
	.ai-frame,
	.ai-orb-core,
	.ai-orb-ring,
	.ai-shine,
	.ai-done-ring {
		animation: none;
	}
}
</style>
