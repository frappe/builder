<template>
	<article
		class="flex min-w-0 flex-1 flex-col overflow-hidden rounded-8 border bg-surface-white transition-colors"
		:class="selected ? 'border-outline-gray-4' : 'border-outline-gray-2'"
		:aria-label="label">
		<div class="flex items-start justify-between gap-2 px-3 pb-2 pt-3">
			<h3 class="min-w-0 break-words text-p-sm font-medium leading-snug text-ink-gray-9">{{ label }}</h3>
			<span v-if="selected" class="flex shrink-0 items-center gap-1 text-p-xs text-ink-gray-6">
				<span class="lucide-check size-3" aria-hidden="true" />
				Selected
			</span>
		</div>
		<AIDesignPreview class="px-2" :label="label" :image="direction.image" @expand="openPreview" />
		<div class="flex flex-1 flex-col gap-3 p-3">
			<p v-if="direction.description" class="line-clamp-2 text-p-xs leading-relaxed text-ink-gray-6">
				{{ direction.description }}
			</p>
			<p v-if="direction.stale" class="text-p-xs leading-relaxed text-ink-orange-5">
				The brief changed. Ask Bob to refresh this direction.
			</p>
			<div class="mt-auto flex items-center gap-2">
				<Button
					class="flex-1"
					variant="subtle"
					:disabled="disabled || direction.stale"
					:aria-pressed="selected"
					@click="choose">
					{{ actionLabel || (selected ? "Selected" : "Use this direction") }}
				</Button>
				<Button variant="ghost" :disabled="disabled" @click="openRefinement">Tweak</Button>
			</div>
		</div>
	</article>
	<Dialog v-model="expanded" :title="label" size="6xl" @after-leave="restoreFocus">
		<template #default>
			<AIDesignPreview
				expanded
				:label="label"
				:image="direction.image"
				:details="direction.detail_previews" />
			<p v-if="direction.description" class="mt-4 text-p-sm leading-relaxed text-ink-gray-6">
				{{ direction.description }}
			</p>
		</template>
		<template #actions>
			<form v-if="refining" ref="refineForm" class="space-y-3" @submit.prevent="refine">
				<FormControl
					v-model="changes"
					type="textarea"
					label="What would you change?"
					placeholder="Warmer colors, a bigger headline, a simpler contact section…"
					:rows="3"
					:maxlength="1200"
					:disabled="disabled" />
				<div class="flex flex-wrap items-center justify-between gap-3">
					<p class="text-p-xs text-ink-gray-5">Bob will show an updated preview before you choose.</p>
					<div class="flex gap-2">
						<Button variant="ghost" @click="refining = false">Cancel</Button>
						<Button type="submit" variant="solid" :disabled="disabled || !changes.trim()">
							Update preview
						</Button>
					</div>
				</div>
			</form>
			<div v-else class="flex flex-wrap items-center justify-between gap-3">
				<p class="text-p-xs text-ink-gray-5">
					{{
						direction.stale
							? "The brief changed. Ask Bob to refresh this direction."
							: "Choose this direction, or tweak it first."
					}}
				</p>
				<div class="flex gap-2">
					<Button variant="ghost" :disabled="disabled" @click="startRefining">Tweak</Button>
					<Button
						variant="solid"
						:disabled="disabled || direction.stale"
						:aria-pressed="selected"
						@click="choose">
						{{ actionLabel || (selected ? "Selected" : "Use this direction") }}
					</Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { Button, Dialog, FormControl } from "frappe-ui";
import { computed, nextTick, ref } from "vue";
import AIDesignPreview from "./AIDesignPreview.vue";

const props = defineProps<{
	direction: {
		label?: string;
		image?: string;
		detail_previews?: { label: string; image: string }[];
		description?: string;
		stale?: boolean;
	};
	selected?: boolean;
	disabled?: boolean;
	actionLabel?: string;
}>();
const emit = defineEmits<{ select: []; refine: [changes: string] }>();
const label = computed(() => props.direction.label || "Design direction");
const expanded = ref(false);
const refining = ref(false);
const changes = ref("");
const refineForm = ref<HTMLFormElement | null>(null);
let previewTrigger: HTMLElement | null = null;

function openPreview(event: MouseEvent) {
	previewTrigger = event.currentTarget as HTMLElement;
	refining.value = false;
	expanded.value = true;
}

function openRefinement(event: MouseEvent) {
	openPreview(event);
	startRefining();
}

async function startRefining() {
	refining.value = true;
	await nextTick();
	refineForm.value?.querySelector("textarea")?.focus();
}

function refine() {
	if (props.disabled || !changes.value.trim()) return;
	expanded.value = false;
	emit("refine", changes.value.trim());
}

function restoreFocus() {
	if (previewTrigger?.isConnected) previewTrigger.focus({ preventScroll: true });
}

function choose() {
	if (props.disabled || props.direction.stale) return;
	expanded.value = false;
	emit("select");
}
</script>
