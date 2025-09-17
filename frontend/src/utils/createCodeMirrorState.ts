import {
	autocompletion,
	closeBrackets,
	closeBracketsKeymap,
	completionKeymap,
} from "@codemirror/autocomplete";
import { defaultKeymap, history, historyKeymap, indentWithTab } from "@codemirror/commands";
import { css } from "@codemirror/lang-css";
import { html } from "@codemirror/lang-html";
import { javascript, javascriptLanguage } from "@codemirror/lang-javascript";
import { json } from "@codemirror/lang-json";
import { python, pythonLanguage } from "@codemirror/lang-python";
import {
	bracketMatching,
	defaultHighlightStyle,
	foldGutter,
	foldKeymap,
	indentOnInput,
	syntaxHighlighting,
} from "@codemirror/language";
import { highlightSelectionMatches, searchKeymap } from "@codemirror/search";
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
		// indentWithTab,
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
		keymap.of([indentWithTab]), // enable indent with tab // TODO: better tab handling
	];

	// register Ctrl+S / Cmd+S for save
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
		case "JavaScript":
			extensions.push(
				javascript(),
				javascriptLanguage.data.of({
					autocomplete: jsCompletionsFromGlobalScope,
				}),
			);
			break;
		case "Python":
			extensions.push(
				python(),
				pythonLanguage.data.of({
					autocomplete: (context: any) => customPythonCompletions(context, pythonCompletions),
				}),
			);
			break;
		case "HTML":
			extensions.push(html());
			break;
		case "CSS":
			extensions.push(css());
			break;
		case "JSON":
			extensions.push(json());
			break;
	}

	let startState = EditorState.create({
		doc: props.initialValue || initialValue || "",
		extensions,
	});
	return { startState };
};
