<template>
	<div class="flex w-full justify-between bg-surface-gray-1" @keydown.esc.stop="closeSearchPanel(view)">
		<div v-if="enableReplace" class="flex items-center justify-center">
			<Button variant="ghost" size="sm" class="h-full" @click="toggleReplace">
				<FeatherIcon :name="showReplace ? 'chevron-down' : 'chevron-right'" class="h-4 w-4" />
			</Button>
		</div>
		<div class="flex w-full max-w-lg flex-col">
			<div class="relative flex flex-col items-center gap-2 px-2.5 py-2 @md:flex-row">
				<div class="flex">
					<Input
						v-model="search"
						type="text"
						placeholder="Find"
						@input="commit"
						@keyup="commit"
						@keydown.enter.prevent="enter"
						autofocus />
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
				<div class="flex">
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
						@click.prevent="closeSearchPanel(view)"
						title="Close Search (Esc)"></Button>
				</div>
			</div>
			<div v-if="enableReplace && showReplace" class="relative flex items-center gap-2">
				<div class="flex">
					<Input
						v-model="replaceWith"
						type="text"
						placeholder="Replace"
						@input="commit"
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
import { inject, ref } from "vue";

const view = inject<EditorView>("view")!;
const enableReplace = inject<boolean>("enableReplace", false);

const search = ref("");
const replaceWith = ref("");
const caseSensitive = ref(false);
const regexp = ref(false);
const wholeWord = ref(false);
const showReplace = ref(false);

function toggleReplace() {
	showReplace.value = !showReplace.value;
}

function commit(e?: Event | KeyboardEvent) {
	const query = new SearchQuery({
		search: search.value,
		replace: replaceWith.value,
		caseSensitive: caseSensitive.value,
		regexp: regexp.value,
		wholeWord: wholeWord.value,
	});
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
</script>
