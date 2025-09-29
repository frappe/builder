<template>
	<div
		class="absolute right-0 top-0 flex rounded-md border border-outline-gray-3 bg-surface-gray-1 shadow-lg"
		@keydown.esc.stop="(e) => closePanel(e)">
		<div v-if="enableReplace" class="flex items-center justify-center">
			<Button variant="ghost" size="sm" class="h-full" @click="toggleReplace">
				<FeatherIcon :name="showReplace ? 'chevron-down' : 'chevron-right'" class="h-4 w-4" />
			</Button>
		</div>
		<div class="flex w-full max-w-lg flex-col">
			<div class="relative flex flex-col items-center gap-2 px-2.5 py-2 @md:flex-row">
				<div class="flex gap-1">
					<Input
						v-model="search"
						ref="inputRef"
						type="text"
						placeholder="Find"
						@input="(e: string) => commit({ searchTerm: e })"
						@keyup="commit"
						@keydown.enter.prevent="enter" />
					<div class="flex shrink-0 items-center gap-1">
						<Button
							:variant="caseSensitive ? 'outline' : 'ghost'"
							size="sm"
							icon="type"
							@click="toggleCaseSensitive"
							title="Match Case"></Button>
						<Button
							:variant="regexp ? 'outline' : 'ghost'"
							size="sm"
							@click="toggleIsRegexp"
							title="Use Regular Expression">
							<span class="font-mono text-xs">.*</span>
						</Button>
						<Button
							:variant="wholeWord ? 'outline' : 'ghost'"
							size="sm"
							@click="toggleWholeWord"
							title="Match Whole Word">
							<span class="font-mono text-xs">Ab</span>
						</Button>
					</div>
				</div>
				<div class="flex w-full justify-between gap-1 @md:w-auto @md:justify-normal">
					<Button
						size="sm"
						icon="chevron-up"
						variant="ghost"
						@click.prevent="findNext(view)"
						title="Find Next (Enter)"></Button>
					<Button
						size="sm"
						variant="ghost"
						icon="chevron-down"
						@click.prevent="findPrevious(view)"
						title="Find Previous (Shift + Enter)"></Button>
					<Button
						size="sm"
						variant="ghost"
						icon="layers"
						@click.prevent="selectMatches(view)"
						title="Select All Matches (Alt + Enter)"></Button>
					<Button
						size="sm"
						variant="ghost"
						icon="x"
						@click.prevent="(e: Event) => closePanel(e)"
						title="Close Search (Esc)"></Button>
				</div>
			</div>
			<div v-if="enableReplace && showReplace" class="relative flex items-center gap-2 px-2.5 py-2">
				<div class="flex">
					<Input
						v-model="replaceWith"
						type="text"
						placeholder="Replace"
						@input="(e: string) => commit({ replaceTerm: e })"
						@keyup="commit"
						@keydown.enter.prevent="enter" />
				</div>
				<div class="flex items-center gap-1">
					<Button
						size="sm"
						variant="ghost"
						@click.prevent="replaceNext(view)"
						icon="corner-down-right"
						title="Replace Next"></Button>
					<Button
						size="sm"
						variant="ghost"
						@click.prevent="replaceAll(view)"
						icon="copy"
						title="Replace All"></Button>
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
import { Button, FeatherIcon, Input } from "frappe-ui";
import { inject, nextTick, onMounted, ref } from "vue";

const view = inject<EditorView>("view")!;
const enableReplace = inject<boolean>("enableReplace", false);

const inputRef = ref<InstanceType<typeof Input> | null>(null);
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
		inputRef.value?.$el.querySelector("input")?.focus();
	});
});
</script>
