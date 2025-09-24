<script setup lang="ts">
import {
	SearchQuery,
	closeSearchPanel,
	findNext,
	findPrevious,
	selectMatches,
	setSearchQuery,
	replaceNext,
	replaceAll,
} from "@codemirror/search";
import type { EditorView } from "@codemirror/view";
import SearchInput from "./SearchInput.vue";
import { inject, ref, onMounted, nextTick } from "vue";
import { Button } from "frappe-ui";

const view = inject<EditorView>("view")!;
const enableReplace = inject<boolean>("enableReplace", false);

const inputRef = ref<InstanceType<typeof SearchInput> | null>(null);
const search = ref("");
const replaceWith = ref("");
const caseSensitive = ref(false);
const regexp = ref(false);
const wholeWord = ref(false);
const showReplace = ref(false);

function toggleReplace() {
	showReplace.value = !showReplace.value;
	if (showReplace.value) {
		nextTick(() => {
			inputRef.value?.select();
		});
	}
}

function commit(e: KeyboardEvent) {
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
	commit(new KeyboardEvent("change"));
}

function toggleIsRegexp() {
	regexp.value = !regexp.value;
	commit(new KeyboardEvent("change"));
}

function toggleWholeWord() {
	wholeWord.value = !wholeWord.value;
	commit(new KeyboardEvent("change"));
}

onMounted(() => {
	// Hack to focus custom input
	// https://discuss.codemirror.net/t/automatic-search-input-focus-only-works-when-panel-already-exists/5628/2
	nextTick(() => {
		inputRef.value?.select();
	});
});
</script>

<template>
	<div class="flex w-full justify-between bg-surface-gray-1" @keydown.esc.stop="closeSearchPanel(view)">
		<div v-if="enableReplace" class="flex items-center justify-center px-2 py-1.5">
			<Button id="matchCase" variant="ghost" size="sm" class="h-full" @click="toggleReplace">
				<LucideChevronRight v-if="!showReplace" class="h-4 w-4 cursor-pointer outline-none" />
				<LucideChevronDown v-else class="h-4 w-4 cursor-pointer outline-none" />
			</Button>
		</div>
		<div class="flex w-full max-w-lg flex-col">
			<div class="relative flex flex-col items-center gap-2 px-2.5 py-2 @md:flex-row">
				<div class="flex w-full gap-1 rounded border border-gray-500">
					<SearchInput
						ref="inputRef"
						v-model="search"
						placeholder="Find"
						@onchange="commit"
						@keyup="commit"
						@keydown.enter.prevent="enter" />
					<div class="flex shrink-0 items-center gap-1">
						<div class="flex items-center text-ink-gray-8">
							<Button
								id="matchCase"
								:variant="caseSensitive ? 'outline' : 'ghost'"
								size="sm"
								@click="toggleCaseSensitive">
								<LucideCaseSensitive class="h-4 w-4 cursor-pointer outline-none" />
							</Button>
						</div>
						<div class="flex items-center text-ink-gray-8">
							<Button id="isRegexp" :variant="regexp ? 'outline' : 'ghost'" size="sm" @click="toggleIsRegexp">
								<LucideRegex class="h-4 w-4 cursor-pointer outline-none" />
							</Button>
						</div>
						<div class="flex items-center text-ink-gray-8">
							<Button
								id="wholeWord"
								:variant="wholeWord ? 'outline' : 'ghost'"
								size="sm"
								@click="toggleWholeWord">
								<LucideWholeWord class="h-4 w-4 cursor-pointer outline-none" />
							</Button>
						</div>
					</div>
				</div>
				<div class="flex w-full items-center justify-between gap-1 @md:w-auto">
					<Button size="sm" variant="ghost" @click.prevent="findNext(view)" title="Find Next (Enter)">
						<LucideArrowUp class="h-4 w-4 cursor-pointer text-ink-gray-8 outline-none" />
					</Button>
					<Button
						size="sm"
						variant="ghost"
						@click.prevent="findPrevious(view)"
						title="Find Previous (Shift + Enter)">
						<LucideArrowDown class="h-4 w-4 cursor-pointer text-ink-gray-8 outline-none" />
					</Button>
					<Button
						size="sm"
						variant="ghost"
						@click.prevent="selectMatches(view)"
						title="Select All Matches (Alt + Enter)">
						<LucideTextSelect class="h-4 w-4 cursor-pointer text-ink-gray-8 outline-none" name="layers" />
					</Button>
					<Button
						size="sm"
						variant="ghost"
						@click.prevent="closeSearchPanel(view)"
						title="Close Search (Esc)">
						<LucideX class="h-4 w-4 cursor-pointer text-ink-gray-8 outline-none" name="layers" />
					</Button>
				</div>
			</div>
			<div v-if="enableReplace && showReplace" class="relative flex items-center gap-2 px-2.5 py-2 @md:pr-20">
				<div class="flex w-full rounded border border-gray-500">
					<SearchInput
						ref="inputRef"
						v-model="replaceWith"
						placeholder="Replace"
						@onchange="commit"
						@keyup="commit"
						@keydown.enter.prevent="enter" />
				</div>
				<div class="flex items-center gap-1">
					<Button size="sm" variant="ghost" @click.prevent="replaceNext(view)" title="Find Next (Enter)">
						<LucideReplace class="h-4 w-4 cursor-pointer text-ink-gray-8 outline-none" />
					</Button>
					<Button
						size="sm"
						variant="ghost"
						@click.prevent="replaceAll(view)"
						title="Find Previous (Shift + Enter)">
						<LucideReplaceAll class="h-4 w-4 cursor-pointer text-ink-gray-8 outline-none" />
					</Button>
				</div>
			</div>
		</div>
	</div>
</template>
