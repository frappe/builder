import {
	autocompletion,
	closeBrackets,
	closeBracketsKeymap,
	completionKeymap,
} from "@codemirror/autocomplete";
import {
	defaultKeymap,
	history,
	historyKeymap,
	indentWithTab,
} from "@codemirror/commands";
import {
	bracketMatching,
	defaultHighlightStyle,
	foldGutter,
	foldKeymap,
	indentOnInput,
	syntaxHighlighting,
} from "@codemirror/language";
import { highlightSelectionMatches, searchKeymap, search } from "@codemirror/search";
import { EditorState, Extension } from "@codemirror/state";
import {
	crosshairCursor,
	drawSelection,
	dropCursor,
	highlightActiveLine,
	highlightActiveLineGutter,
	highlightSpecialChars,
	keymap,
	lineNumbers,
	rectangularSelection,
	ViewUpdate,
} from "@codemirror/view";
import { EditorView } from "codemirror";
import jsCompletionsFromGlobalScope from "./jsGlobalCompletion";
import customPythonCompletions from "./pythonCustomCompletion";

import { createApp } from "vue";
import CustomSearchPanel from "@/components/Controls/CodeMirror/CustomSearchPanel.vue";

interface CreateStateParams {
	props: any;
	extraExtensions?: Extension[];
	pythonCompletions: any;
	onSaveCallback: any;
	onChangeCallback: any;
	onBlurCallback?: any;
	initialValue?: string;
}

export const createStartingState = async ({
	props,
	extraExtensions = [], // to add extra extensions without recreating state (eg: linting)
	pythonCompletions,
	onSaveCallback,
	onChangeCallback,
	onBlurCallback,
	initialValue = "", // to override initial value without recreating state (eg: when resetting)
}: CreateStateParams) => {
	const updateEmitter = EditorView.updateListener.of((update: ViewUpdate) => {
		if (update.docChanged) onChangeCallback();
	});

	// Create blur event listener if callback is provided
	const blurListener = onBlurCallback
		? EditorView.domEventHandlers({
				blur: (event, view) => {
					onBlurCallback(view.state.doc.toString());
					return false; // Don't prevent default
				},
			})
		: [];
	// collection of basic extensions: https://github.com/codemirror/basic-setup/blob/main/src/codemirror.ts
	const basicSetup: Extension = (() => [
		props.showLineNumbers ? lineNumbers() : [],
		props.showLineNumbers ? EditorView.lineWrapping : [],
		props.readonly ? highlightActiveLineGutter() : [],
		highlightSpecialChars(),
		history(),
		foldGutter(),
		drawSelection(),
		dropCursor(),
		EditorState.allowMultipleSelections.of(true),
		indentOnInput(),
		syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
		bracketMatching(),
		closeBrackets(),
		autocompletion({
			activateOnTyping: true,
		}),
		rectangularSelection(),
		crosshairCursor(),
		highlightActiveLine(),
		highlightSelectionMatches(),
		keymap.of([
			...closeBracketsKeymap,
			...defaultKeymap,
			...searchKeymap,
			...historyKeymap,
			...foldKeymap,
			...completionKeymap,
		]),
	])();
	const extensions = [
		basicSetup,
		EditorState.readOnly.of(props.readonly),
		// EditorView.editable.of(!props.readonly), // removes cursor but also disables search // TODO: use https://codemirror.net/docs/ref/#search.openSearchPanel
		updateEmitter,
		blurListener,
		...extraExtensions,
		keymap.of([
			{
				key: "Tab",
				run: (view) => {
					const spaces = "    "; // 4 spaces
					view.dispatch({
						changes: {
							from: view.state.selection.main.from,
							to: view.state.selection.main.to,
							insert: spaces,
						},
						selection: {
							anchor: view.state.selection.main.from + spaces.length,
						},
					});
					return true;
				},
			},
		]),
		EditorView.domEventHandlers({
			cut: (event, view) => {
				// this is to prevent the cut event from propagating to document and trigger cutting the block
				event.stopPropagation();
			},
		}),
		search({
			createPanel(view) {
				const dom = document.createElement("div");
				dom.classList.add("@container");

				const app = createApp(CustomSearchPanel);
				app.provide("view", view);
				app.provide("enableReplace", !props.readonly);
				app.mount(dom);

				return {
					dom,
					top: true,
				};
			},
		}),
	];

	if (props.allowSave || !props.readOnly) {
		extensions.push(
			keymap.of([
				{
					key: "Ctrl-s",
					mac: "Cmd-s",
					run: () => {
						onSaveCallback();
						return true;
					},
				},
			]),
		);
	}
	// TODO: reconfigure with Compartments instead of switch...case
	switch (props.type) {
		case "JavaScript": {
			const { javascript, javascriptLanguage } = await import(
				"@codemirror/lang-javascript"
			);
			extensions.push(
				javascript(),
				javascriptLanguage.data.of({
					autocomplete: jsCompletionsFromGlobalScope,
				}),
			);
			break;
		}
		case "Python": {
			const { python, pythonLanguage } = await import(
				"@codemirror/lang-python"
			);
			extensions.push(
				python(),
				pythonLanguage.data.of({
					autocomplete: (context: any) =>
						customPythonCompletions(context, pythonCompletions),
				}),
			);
			break;
		}
		case "HTML": {
			const { html } = await import("@codemirror/lang-html");
			extensions.push(html());
			break;
		}
		case "CSS": {
			const { css } = await import("@codemirror/lang-css");
			extensions.push(css());
			break;
		}
		case "JSON": {
			const { json } = await import("@codemirror/lang-json");
			extensions.push(json());
			break;
		}
	}

	let startState = EditorState.create({
		doc: props.initialValue || initialValue || "",
		extensions,
	});
	return { startState };
};
