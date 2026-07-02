<template>
	<div
		class="absolute right-0 top-0 flex rounded-md border border-outline-gray-3 bg-surface-gray-1 shadow-lg"
		@keydown.esc.stop="closePanel">
		<div v-if="enableReplace" class="flex items-center border-r border-outline-gray-2">
			<Button
				variant="ghost"
				size="sm"
				class="h-full rounded-r-none"
				:tooltip="showReplace ? 'Hide Replace' : 'Show Replace'"
				@click="toggleReplace">
				<span
					:class="[showReplace ? 'lucide-chevron-down' : 'lucide-chevron-right', 'h-4 w-4']"
					aria-hidden="true" />
			</Button>
		</div>
		<div class="flex w-full max-w-lg flex-col divide-y divide-outline-gray-2">
			<!-- Find row -->
			<div class="flex items-center gap-1.5 px-1.5 py-1">
				<TextInput
					v-model="search"
					ref="inputRef"
					type="text"
					placeholder="Find"
					@update:modelValue="(val: string) => commit({ searchTerm: val })"
					@keydown.enter.prevent="enter" />
				<div class="flex shrink-0 items-center">
					<Button
						:variant="caseSensitive ? 'subtle' : 'ghost'"
						size="sm"
						icon="lucide-type"
						tooltip="Match Case"
						@click="toggleCaseSensitive" />
					<Button
						:variant="regexp ? 'subtle' : 'ghost'"
						size="sm"
						tooltip="Use Regular Expression"
						@click="toggleIsRegexp">
						<span class="font-mono text-xs">.*</span>
					</Button>
					<Button
						:variant="wholeWord ? 'subtle' : 'ghost'"
						size="sm"
						tooltip="Match Whole Word"
						@click="toggleWholeWord">
						<span class="font-mono text-xs">Ab</span>
					</Button>
				</div>
				<div class="flex shrink-0 items-center border-l border-outline-gray-2 pl-1">
					<Button
						size="sm"
						icon="lucide-chevron-up"
						variant="ghost"
						tooltip="Find Previous (Shift+Enter)"
						@click.prevent="findPrevious(view)" />
					<Button
						size="sm"
						variant="ghost"
						icon="lucide-chevron-down"
						tooltip="Find Next (Enter)"
						@click.prevent="findNext(view)" />
					<Button
						size="sm"
						variant="ghost"
						icon="lucide-align-justify"
						tooltip="Select All Matches (Alt+Enter)"
						@click.prevent="selectMatches(view)" />
					<Button
						size="sm"
						variant="ghost"
						icon="lucide-x"
						tooltip="Close (Esc)"
						@click.prevent="closePanel" />
				</div>
			</div>
			<!-- Replace row -->
			<div v-if="enableReplace && showReplace" class="flex items-center gap-1.5 px-1.5 py-1">
				<TextInput
					v-model="replaceWith"
					type="text"
					placeholder="Replace"
					@update:modelValue="(val: string) => commit({ replaceTerm: val })"
					@keydown.enter.prevent="enter" />
				<div class="flex shrink-0 items-center">
					<Button
						size="sm"
						variant="ghost"
						icon="lucide-corner-down-right"
						tooltip="Replace Next"
						@click.prevent="replaceNext(view)" />
					<Button
						size="sm"
						variant="ghost"
						icon="lucide-copy"
						tooltip="Replace All"
						@click.prevent="replaceAll(view)" />
				</div>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import {
	SearchQuery,
	closeSearchPanel,
	findNext,
	findPrevious,
	replaceAll,
	replaceNext,
	selectMatches,
	setSearchQuery,
} from "@codemirror/search";
import type { EditorView } from "@codemirror/view";
import { Button, TextInput } from "frappe-ui";
import { inject, nextTick, onMounted, ref } from "vue";

const view = inject<EditorView>("view")!;
const enableReplace = inject<boolean>("enableReplace", false);

const inputRef = ref<InstanceType<typeof TextInput> | null>(null);
const search = ref("");
const replaceWith = ref("");
const caseSensitive = ref(false);
const regexp = ref(false);
const wholeWord = ref(false);
const showReplace = ref(false);

function toggleReplace() {
	showReplace.value = !showReplace.value;
}

function commit(params?: { searchTerm?: string; replaceTerm?: string }) {
	const query = new SearchQuery({
		search: params?.searchTerm || search.value,
		replace: params?.replaceTerm || replaceWith.value,
		caseSensitive: caseSensitive.value,
		regexp: regexp.value,
		wholeWord: wholeWord.value,
	});
	if (params?.searchTerm) search.value = params.searchTerm;
	if (params?.replaceTerm) replaceWith.value = params.replaceTerm;
	view.dispatch({ effects: setSearchQuery.of(query) });
}

function enter(e: KeyboardEvent) {
	(e.shiftKey ? findPrevious : findNext)(view);
}

function toggleCaseSensitive() {
	caseSensitive.value = !caseSensitive.value;
	commit();
}

function toggleIsRegexp() {
	regexp.value = !regexp.value;
	commit();
}

function toggleWholeWord() {
	wholeWord.value = !wholeWord.value;
	commit();
}

function closePanel(e?: KeyboardEvent | Event) {
	const closestCmEditor = (e?.target as HTMLElement)?.closest(".cm-editor") as HTMLElement;
	const closestCmContent = closestCmEditor.querySelector(".cm-content") as HTMLElement;
	closestCmContent?.classList.remove("@md/editor:!pt-10", "!pt-20");
	closeSearchPanel(view);
}

onMounted(() => {
	nextTick(() => {
		inputRef.value?.el?.focus();
	});
});
</script>
