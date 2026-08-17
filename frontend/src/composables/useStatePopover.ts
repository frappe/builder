import blockController from "@/utils/blockController";
import { useEventListener } from "@vueuse/core";
import { ref } from "vue";

type TogglePopover = (open: boolean) => void;

// A swatch popover edits one state at a time: it opens when its field gets focus
// and toggles when the swatch is clicked.
export function useStatePopover() {
	const activeState = ref<string | null>(null);
	let closeOnClick = false;
	let ignoreFocus = false;

	// a press or a keystroke is user intent, so let focus open the popover again
	const allowFocusToOpen = () => (ignoreFocus = false);
	useEventListener(document, "pointerdown", allowFocusToOpen, { capture: true });
	useEventListener(document, "keydown", allowFocusToOpen, { capture: true });

	// the click closes the popover only when it is already open for this state
	const rememberPopoverState = (state: string | null, isOpen: boolean) => {
		closeOnClick = isOpen && activeState.value === state;
	};

	const togglePopoverForState = (state: string | null, togglePopover: TogglePopover) => {
		activeState.value = state;
		// a state row takes focus back when the panel closes, to keep its preview,
		// and that focus would otherwise reopen what this click just closed
		ignoreFocus = closeOnClick;
		togglePopover(!closeOnClick);
	};

	const canOpenOnFocus = () => !ignoreFocus;

	let lastMouseDown: MouseEvent | null = null;
	useEventListener(document, "mousedown", (event: MouseEvent) => (lastMouseDown = event), {
		capture: true,
	});

	// the canvas previews a state while its editor is open. Canvas handles prevent
	// their own mousedown and keep editing the state, so wait one frame for the
	// press that closed the popover to say which it is. The same press can also
	// hand the state to another control, which then owns it.
	const endStatePreview = () => {
		const previewedState = blockController.getSelectedBlocks()[0]?.activeState;
		lastMouseDown = null;
		requestAnimationFrame(() => {
			if (lastMouseDown?.defaultPrevented) return;
			blockController.getSelectedBlocks().forEach((block) => {
				if (block.activeState === previewedState) block.activeState = null;
			});
		});
	};

	return {
		activeState,
		rememberPopoverState,
		togglePopoverForState,
		canOpenOnFocus,
		endStatePreview,
	};
}
