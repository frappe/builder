<template>
	<div class="min-w-0 space-y-3">
		<div
			class="group relative block w-full rounded-4 border border-outline-gray-1 bg-surface-gray-2"
			:class="expanded ? 'max-h-[50vh] overflow-auto' : 'aspect-[8/5] overflow-hidden'">
			<img
				v-if="source && !failed"
				:key="source"
				:src="source"
				:alt="`${label}, ${activePreview.label}`"
				class="block w-full"
				:class="expanded ? 'h-auto' : 'absolute inset-0 h-full object-cover object-top'"
				:loading="expanded ? 'eager' : 'lazy'"
				@error="failed = true" />
			<div v-else class="flex h-full min-h-40 flex-col items-center justify-center gap-2 p-4 text-ink-gray-5">
				<span class="lucide-image-off size-5" aria-hidden="true" />
				<p class="text-p-sm">Preview unavailable</p>
			</div>
			<button
				v-if="!expanded"
				type="button"
				:aria-label="`Preview ${label}`"
				class="absolute inset-0 rounded-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-outline-gray-4"
				@click="$emit('expand', $event)">
				<span
					class="absolute bottom-2 right-2 flex items-center gap-1.5 rounded-4 bg-black/70 px-2 py-1 text-p-xs text-white shadow-sm group-hover:bg-black/80">
					<span class="lucide-maximize-2 size-3" aria-hidden="true" />
					Preview
				</span>
			</button>
		</div>
		<div
			v-if="expanded && previews.length > 1"
			class="flex gap-2 overflow-x-auto pb-1"
			role="group"
			aria-label="Page and section previews">
			<button
				v-for="(preview, index) in previews"
				:key="preview.image || index"
				type="button"
				:aria-pressed="active === index"
				:aria-label="preview.label"
				class="w-28 shrink-0 overflow-hidden rounded-5 border p-1 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-4"
				:class="
					active === index
						? 'border-outline-gray-4 bg-surface-gray-2'
						: 'border-outline-gray-2 hover:border-outline-gray-3'
				"
				@click="active = index">
				<img
					v-if="safeImage(preview.image)"
					:src="preview.image"
					class="h-14 w-full rounded-3 bg-surface-gray-2 object-contain"
					alt=""
					loading="lazy" />
				<span class="mt-1 block truncate px-1 text-p-xs text-ink-gray-7" :title="preview.label">
					{{ preview.label }}
				</span>
			</button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";

const props = defineProps<{
	label: string;
	image?: string;
	details?: { label: string; image: string }[];
	expanded?: boolean;
}>();
defineEmits<{ expand: [event: MouseEvent] }>();
const active = ref(0);
const failed = ref(false);
const previews = computed(() => [
	{ label: "Full page", image: props.image },
	...(Array.isArray(props.details)
		? props.details.filter((detail) => safeImage(detail.image)).slice(0, 4)
		: []),
]);
const activePreview = computed(() => previews.value[props.expanded ? active.value : 0] || previews.value[0]);
const source = computed(() => safeImage(activePreview.value.image));

function safeImage(value?: string) {
	return typeof value === "string" && (/^\/(?![\\/])/.test(value) || value.startsWith("https://"))
		? value
		: "";
}

watch(source, () => (failed.value = false));
watch(
	() => props.image,
	() => (active.value = 0),
);
</script>
