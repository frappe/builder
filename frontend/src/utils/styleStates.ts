import { __ } from "@/translation";

// A "<state>:<property>" style renders as ".<class>:<state>" on published pages,
// so each key here is a CSS pseudo-class.
const styleStates: Record<string, { label: string; description?: string }> = {
	hover: { label: __("On Hover") },
	active: { label: __("On Active") },
	focus: { label: __("On Focus") },
	"focus-visible": {
		label: __("On Keyboard Focus"),
		description: __("Applies when the block gets focus from the keyboard, as with Tab"),
	},
	"focus-within": {
		label: __("On Focus Inside"),
		description: __("Applies while this block or anything inside it has focus"),
	},
	target: {
		label: __("When Linked To"),
		description: __("Applies when a link to this block's #id is followed"),
	},
};

export default styleStates;
