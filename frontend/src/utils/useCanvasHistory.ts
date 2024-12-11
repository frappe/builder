import Block from "@/utils/block";
import { generateId, getBlockInstance, getBlockString } from "@/utils/helpers";
import { debounceFilter, pausableFilter, watchIgnorable } from "@vueuse/core";
import { nextTick, ref, Ref } from "vue";

type CanvasState = {
	block: string;
	selectedBlockIds: string[];
};

type PauseId = string & { __brand: "PauseId" };

const CAPACITY = 200;
const DEBOUNCE_DELAY = 200;

export function useCanvasHistory(source: Ref<Block>, selectedBlockIds: Ref<string[]>) {
	const undoStack = ref([]) as Ref<CanvasState[]>;
	const redoStack = ref([]) as Ref<CanvasState[]>;
	const last = ref(createHistoryRecord(source, selectedBlockIds));
	const pauseIdSet = new Set<PauseId>();

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

	function commit() {
		// console.log("committing...");
		undoStack.value.unshift(last.value);
		last.value = createHistoryRecord(source, selectedBlockIds);
		if (undoStack.value.length > CAPACITY) {
			undoStack.value.splice(CAPACITY, Number.POSITIVE_INFINITY);
		}
		if (redoStack.value.length) {
			redoStack.value.splice(0, redoStack.value.length);
		}
	}

	// const debouncedCommit = useDebounceFn(commit, DEBOUNCE_DELAY);

	const {
		ignoreUpdates: ignoreBlockUpdates,
		ignorePrevAsyncUpdates: ignorePrevAsyncBlockUpdates,
		stop: stopBlockWatcher,
	} = watchIgnorable(source, commit, {
		deep: true,
		flush: "post",
		eventFilter: blockWatcherFilter,
	});

	const {
		ignoreUpdates: ignoreSelectedBlockUpdates,
		ignorePrevAsyncUpdates: ignorePrevSelectedBlockUpdates,
		stop: stopSelectedBlockUpdates,
	} = watchIgnorable(selectedBlockIds, updateSelections, {
		deep: true,
		flush: "post",
		eventFilter: selectionWatherFilter,
	});

	function setSource(value: CanvasState) {
		ignorePrevAsyncBlockUpdates();
		ignoreBlockUpdates(() => {
			source.value = getBlockInstance(value.block);
		});
		ignorePrevSelectedBlockUpdates();
		ignoreSelectedBlockUpdates(() => {
			selectedBlockIds.value = [...value.selectedBlockIds];
		});
		last.value = value;
	}

	function undo() {
		const state = undoStack.value.shift();
		if (state) {
			redoStack.value.unshift(last.value);
			setSource(state);
		}
	}

	function redo() {
		const state = redoStack.value.shift();
		if (state) {
			undoStack.value.unshift(last.value);
			setSource(state);
		}
	}

	const clear = () => {
		undoStack.value.splice(0, undoStack.value.length);
		redoStack.value.splice(0, redoStack.value.length);
	};

	function dispose() {
		stop();
		clear();
	}

	function canUndo() {
		return undoStack.value.length > 0;
	}

	function canRedo() {
		return redoStack.value.length > 0;
	}

	function updateSelections() {
		nextTick(() => {
			last.value.selectedBlockIds = [...selectedBlockIds.value];
		});
	}

	function pause() {
		pauseBlockWatcher();
		pauseSelectionWatcher();
		const pauseId = generateId() as PauseId;
		pauseIdSet.add(pauseId);
		// console.log("\npausing...", pauseId);
		return pauseId as PauseId;
	}

	function resume(pauseId?: PauseId, commitNow?: boolean, force?: boolean) {
		nextTick(() => {
			// console.log("resuming...", pauseId);
			if (pauseId && pauseIdSet.has(pauseId)) {
				pauseIdSet.delete(pauseId);
			} else if (!force) {
				return;
			}

			if (pauseIdSet.size && !force) {
				return;
			}
			resumeTracking();
			if (commitNow) commit();
		});
	}

	function resumeTracking() {
		resumeBlockWatcher();
		resumeSelectionWatcher();
	}

	function stop() {
		stopBlockWatcher();
		stopSelectedBlockUpdates();
	}

	return {
		undo,
		redo,
		dispose,
		pause,
		resume,
		canUndo,
		canRedo,
		isTracking,
		batch: () => {},
		undoStack,
		redoStack,
	};
}

function createHistoryRecord(source: Ref<Block>, selectedBlockIds: Ref<string[]>) {
	return {
		block: getBlockString(source.value),
		selectedBlockIds: selectedBlockIds.value,
	};
}
