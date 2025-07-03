<template>
	<div class="flex min-h-36 flex-col justify-between gap-2">
		<ul class="m-0 list-none p-0">
			<li v-for="(item, index) in dataArray" :key="index">
				<div
					class="w-full truncate rounded p-2 text-left text-base text-ink-gray-7 hover:bg-surface-gray-2"
					:class="{ 'bg-surface-gray-3 text-ink-gray-9': selectedKey === item }"
					@click.stop="selectKey(item)">
					{{ item }}
					<p class="truncate text-sm text-ink-gray-5" :class="{ italic: pageStore.pageData[item] == null }">
						{{ pageStore.pageData[item] == null ? "No Value Set" : pageStore.pageData[item] }}
					</p>
				</div>
			</li>
			<li
				v-if="dataArray.length === 0"
				class="flex flex-col items-center justify-center p-10 text-center text-sm text-ink-gray-5">
				<div>
					No dynamic values found. Please add using
					<a
						href="#"
						@click="builderStore.showDataScriptDialog = true"
						class="text-ink-gray-5 underline hover:text-ink-gray-7">
						Data Script
					</a>
				</div>
			</li>
		</ul>
		<div class="flex items-center justify-between gap-2" v-if="dataArray.length !== 0">
			<span
				class="text-sm text-ink-gray-5"
				:class="{
					invisible: !selectedKey,
				}">
				Selected: {{ selectedKey }}
			</span>
			<div class="flex gap-2">
				<Button variant="subtle" @click="builderStore.showDataScriptDialog = true">Edit Code</Button>
				<Button variant="solid" @click="saveSelection" :disabled="!selectedKey">Set</Button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import { computed, ref } from "vue";

const pageStore = usePageStore();
const builderStore = useBuilderStore();

const props = defineProps<{
	selectedValue?: string;
}>();

const emit = defineEmits(["setDynamicValue"]);

const dataArray = computed(() => {
	// filter all keys from pageStore whose values are not array or object
	return Object.keys(pageStore.pageData).filter((key) => {
		const value = pageStore.pageData[key];
		return ["string", "number", "boolean"].includes(typeof value);
	});
});

const selectedKey = ref<string | null>(props.selectedValue || null);

function selectKey(key: string) {
	selectedKey.value = key;
}

function saveSelection() {
	if (selectedKey.value) {
		emit("setDynamicValue", selectedKey.value);
		selectedKey.value = null;
	}
}
</script>
