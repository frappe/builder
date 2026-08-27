import type Block from "@/block";
import { generateId, getBlockInstance, getBlockString } from "@/utils/helpers";
import { debounceFilter, pausableFilter, watchIgnorable } from "@vueuse/core";
import { ref, Ref } from "vue";

type CanvasState = {
	block: string;
	selectedBlockIds: Set<string>;
};
export type PauseId = string & { __brand: "PauseId" };

const CAPACITY = 500;
const DEBOUNCE_DELAY = 100;
// each record serialises the whole tree, so a heavy page blows past this well before CAPACITY
const MAX_BYTES = 20 * 1024 * 1024;
const MIN_ENTRIES = 10;

export function useCanvasHistory(source: Ref<Block>, selectedBlockIds: Ref<Set<string>>) {
	const undoStack = ref([]) as Ref<CanvasState[]>;
	const redoStack = ref([]) as Ref<CanvasState[]>;
	const last = ref(createHistoryRecord());
	const pauseIdSet = new Set<PauseId>();
	// when disabled (e.g. the canvas is read-only) history is
	// fully inert: nothing is recorded and undo/redo are no-ops. Re-enabled by the
	// caller when the canvas returns to edit mode. Distinct from the transient,
	// reference-counted pause()/resume() used during drag/resize.
	const enabled = ref(true);

	function disable() {
		enabled.value = false;
	}
	function enable() {
		enabled.value = true;
	}

	const {
		eventFilter: blockWatcherFilter,
		pause: pauseBlockWatcher,
		resume: resumeBlockWatcher,
		isActive: isTracking,
	} = pausableFilter(debounceFilter(DEBOUNCE_DELAY));

	const {
		eventFilter: selectionWatherFilter,
		pause: pauseSelectionWatcher,
		resume: resumeSelectionWatcher,
	} = pausableFilter();

	const {
		ignoreUpdates: ignoreBlockUpdates,
		ignorePrevAsyncUpdates: ignorePrevAsyncBlockUpdates,
		stop: stopBlockWatcher,
	} = watchIgnorable(source, commit, {
		deep: true,
		eventFilter: blockWatcherFilter,
	});

	const {
		ignoreUpdates: ignoreSelectedBlockUpdates,
		ignorePrevAsyncUpdates: ignorePrevSelectedBlockUpdates,
		stop: stopSelectedBlockUpdates,
	} = watchIgnorable(selectedBlockIds, updateSelections, {
		deep: true,
		eventFilter: selectionWatherFilter,
	});

	function commit() {
		if (!enabled.value) return;
		undoStack.value.unshift(last.value);
		last.value = createHistoryRecord();
		trim(undoStack.value);
		if (redoStack.value.length) {
			redoStack.value.splice(0, redoStack.value.length);
		}
	}

	function trim(stack: CanvasState[]) {
		if (stack.length > CAPACITY) {
			stack.splice(CAPACITY, Number.POSITIVE_INFINITY);
		}
		let bytes = 0;
		for (let i = 0; i < stack.length; i++) {
			bytes += stack[i].block.length;
			if (bytes > MAX_BYTES && i >= MIN_ENTRIES) {
				stack.splice(i + 1, Number.POSITIVE_INFINITY);
				return;
			}
		}
	}

	function updateSelections() {
		last.value.selectedBlockIds = new Set(selectedBlockIds.value);
	}

	function createHistoryRecord() {
		return {
			block: getBlockString(source.value),
			// copy, or every stacked entry aliases the live set
			selectedBlockIds: new Set(selectedBlockIds.value),
		};
	}

	function setSource(value: CanvasState) {
		ignorePrevAsyncBlockUpdates();
		ignoreBlockUpdates(() => {
			source.value = getBlockInstance(value.block);
		});
		ignorePrevSelectedBlockUpdates();
		ignoreSelectedBlockUpdates(() => {
			selectedBlockIds.value = new Set(value.selectedBlockIds);
		});
		last.value = value;
	}

	// Swap the canvas root without recording it (used for version preview: show a
	// snapshot, then restore the draft). The undo stack and baseline are left intact,
	// so undo/redo keep working on the draft once preview ends.
	function silentSetSource(block: Block) {
		ignorePrevAsyncBlockUpdates();
		ignoreBlockUpdates(() => {
			source.value = block;
		});
	}

	function undo() {
		if (!enabled.value) return;
		const state = undoStack.value.shift();
		if (state) {
			redoStack.value.unshift(last.value);
			trim(redoStack.value);
			setSource(state);
		}
	}

	function canUndo() {
		return enabled.value && undoStack.value.length > 0;
	}

	function redo() {
		if (!enabled.value) return;
		const state = redoStack.value.shift();
		if (state) {
			undoStack.value.unshift(last.value);
			trim(undoStack.value);
			setSource(state);
		}
	}

	function canRedo() {
		return enabled.value && redoStack.value.length > 0;
	}

	function stop() {
		stopBlockWatcher();
		stopSelectedBlockUpdates();
	}

	const clear = () => {
		undoStack.value.splice(0, undoStack.value.length);
		redoStack.value.splice(0, redoStack.value.length);
	};

	function dispose() {
		stop();
		clear();
	}

	function pause() {
		pauseBlockWatcher();
		pauseSelectionWatcher();
		const pauseId = generateId() as PauseId;
		pauseIdSet.add(pauseId);
		return pauseId as PauseId;
	}

	function resumeTracking() {
		resumeBlockWatcher();
		resumeSelectionWatcher();
	}

	function resume(pauseId?: PauseId, commitNow?: boolean, force?: boolean) {
		if (pauseId && pauseIdSet.has(pauseId)) {
			pauseIdSet.delete(pauseId);
		} else if (!force) {
			return;
		}
		if (pauseIdSet.size && !force) {
			return;
		}
		pauseIdSet.clear();
		resumeTracking();
		if (commitNow) commit();
	}

	function batch(callback: () => void) {
		const pauseId = pause();
		callback();
		resume(pauseId, true);
	}

	return {
		undo,
		redo,
		pause,
		resume,
		batch,
		canUndo,
		canRedo,
		dispose,
		disable,
		enable,
		silentSetSource,
		undoStack,
		redoStack,
		isTracking,
	};
}
