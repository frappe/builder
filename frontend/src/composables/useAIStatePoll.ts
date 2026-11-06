import { useIntervalFn } from "@vueuse/core";
import { computed, watch } from "vue";

export const AI_STATE_POLL_INTERVAL = 5000;

interface AIState {
	aiConfigured: boolean | null;
	refreshAIState: () => unknown;
}

/** While Bob is open and AI is off, ask the server again: Frappe Cloud can add the site's AI key at any time. */
export function useAIStatePoll(isOpen: () => boolean, state: AIState) {
	const { pause, resume } = useIntervalFn(() => state.refreshAIState(), AI_STATE_POLL_INTERVAL, {
		immediate: false,
		immediateCallback: true,
	});
	const shouldPoll = computed(() => isOpen() && state.aiConfigured === false);
	watch(shouldPoll, (poll) => (poll ? resume() : pause()), { immediate: true });
}
