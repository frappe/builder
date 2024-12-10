import Block from "@/utils/block";
import { getBlockInstance, getBlockObject } from "@/utils/helpers";
import { debounceFilter, pausableFilter, watchIgnorable } from "@vueuse/core";
import { nextTick, ref, Ref } from "vue";

type CanvasState = {
	block: Block;
	selectedBlockIds: string[];
};
const CAPACITY = 50;
const DEBOUNCE_DELAY = 200;

export function useCanvasHistory(source: Ref<Block>, selectedBlockIds: Ref<string[]>) {
	const {
		eventFilter: composedFilter,
		pause,
		resume: resumeTracking,
		isActive: isTracking,
	} = pausableFilter(debounceFilter(DEBOUNCE_DELAY));

	const { ignoreUpdates, ignorePrevAsyncUpdates, stop } = watchIgnorable(source, commit, {
		deep: true,
		flush: "post",
		eventFilter: composedFilter,
	});

	function setSource(value: string) {
		const obj = JSON.parse(value) as CanvasState;
		ignorePrevAsyncUpdates();
		ignoreUpdates(() => {
			source.value = getBlockInstance(obj.block);
			selectedBlockIds.value = obj.selectedBlockIds;
		});
	}
	const last = ref(createHistoryRecord(source, selectedBlockIds));
	function commit() {
		nextTick(() => {
			undoStack.value.unshift(last.value);
			last.value = createHistoryRecord(source, selectedBlockIds);
			if (undoStack.value.length > CAPACITY) {
				undoStack.value.splice(CAPACITY, Number.POSITIVE_INFINITY);
			}
			if (redoStack.value.length) {
				redoStack.value.splice(0, redoStack.value.length);
			}
		});
	}
	const undoStack = ref([]) as Ref<string[]>;
	const redoStack = ref([]) as Ref<string[]>;

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

	function resume(commitNow?: boolean) {
		resumeTracking();
		if (commitNow) commit();
	}

	function canUndo() {
		return undoStack.value.length > 0;
	}

	function canRedo() {
		return redoStack.value.length > 0;
	}

	return {
		undo,
		redo,
		dispose,
		pause,
		resumeTracking,
		resume,
		isTracking,
		canUndo,
		canRedo,
		batch: () => {},
	};
}

function createHistoryRecord(source: Ref<Block>, selectedBlockIds: Ref<string[]>) {
	return JSON.stringify({
		block: getBlockObject(source.value),
		selectedBlockIds: selectedBlockIds.value,
	});
}
