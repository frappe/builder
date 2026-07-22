import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import { frappeRequest, toast } from "frappe-ui";
import { nextTick, onMounted, watch } from "vue";

const TOAST_ID = "site-read-only-mode";
const POLL_INTERVAL = 10 * 1000;

export function useSiteReadOnlyNotice() {
	const builderStore = useBuilderStore();
	const pageStore = usePageStore();
	let poll: number | null = null;

	function showNotice() {
		toast.warning("Site is in read-only mode", {
			id: TOAST_ID,
			duration: Infinity,
			description: "Editing is disabled while the site is being updated. Please try again in a few minutes.",
		});
	}

	function checkIfSiteIsWritable() {
		frappeRequest({ url: "builder.api.is_site_read_only" })
			.then((readOnly) => (builderStore.isSiteInReadOnlyMode = Boolean(readOnly)))
			.catch(() => {});
	}

	function startPolling() {
		poll ??= window.setInterval(checkIfSiteIsWritable, POLL_INTERVAL);
	}

	function stopPolling() {
		if (poll) clearInterval(poll);
		poll = null;
	}

	function onSiteBackOnline() {
		stopPolling();
		toast.dismiss(TOAST_ID);
		toast.success("Site is back online", { description: "You can continue editing." });
		if (pageStore.selectedPage) nextTick(() => pageStore.savePage());
	}

	// on mount so the immediate toast fires after the ToastProvider exists
	onMounted(() => {
		watch(
			() => builderStore.isSiteInReadOnlyMode,
			(readOnly, wasReadOnly) => {
				if (readOnly) {
					showNotice();
					startPolling();
				} else if (wasReadOnly) {
					onSiteBackOnline();
				}
			},
			{ immediate: true },
		);
	});
}
