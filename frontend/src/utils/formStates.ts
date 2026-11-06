import { __ } from "@/translation";

// a published form's submit script puts it in a state through data-state; without one it is in default
const formStates = [
	{ label: __("Default"), value: "default" },
	{ label: __("Sending"), value: "sending" },
	{ label: __("Success"), value: "success" },
	{ label: __("Error"), value: "error" },
];

const FORM_STATES = formStates.map((state) => state.value);

// the states a block inside a form can style, as it styles hover; default is its base style
const FORM_STYLE_STATES = FORM_STATES.filter((state) => state !== "default");

export { FORM_STATES, FORM_STYLE_STATES, formStates };
