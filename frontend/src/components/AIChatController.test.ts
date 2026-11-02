import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from "vitest";
import { reactive, ref } from "vue";
import type { AIRun, AIRunEvent, AISession, ChatMessage } from "./ai/types";

const mocks = vi.hoisted(() => ({
	api: {} as Record<string, Mock<(...args: any[]) => any>>,
	builder: {} as any,
	canvas: {} as any,
	page: {} as any,
	route: {} as any,
	applyTool: vi.fn(),
	applyYaml: vi.fn(),
	confirm: vi.fn(),
	error: vi.fn(),
	success: vi.fn(),
	info: vi.fn(),
}));
vi.mock("@/stores/builderStore", () => ({ default: () => mocks.builder }));
vi.mock("@/stores/canvasStore", () => ({ default: () => mocks.canvas }));
vi.mock("@/stores/pageStore", () => ({ default: () => mocks.page }));
vi.mock("vue-router", () => ({ useRoute: () => mocks.route }));
vi.mock("@/data/builderToken", () => ({ default: { reload: vi.fn() } }));
vi.mock("@/utils/helpers", () => ({ confirm: mocks.confirm, getErrorMessage: (e: Error) => e.message }));
vi.mock("vue", async (original) => ({ ...(await original<any>()), inject: () => ({ value: null }) }));
vi.mock("@vueuse/core", () => ({ useLocalStorage: () => ref("model") }));
vi.mock("frappe-ui", () => ({
	createResource: (options: any) => ({
		submit: (params: any) => mocks.api[options.url.split(".").at(-1)](params || options.makeParams?.() || {}),
	}),
	toast: { error: mocks.error, success: mocks.success, info: mocks.info },
}));
vi.mock("./ai/toolDispatch", () => ({
	ToolDispatcher: class {
		pendingAffectedBlocks = ref<any[]>([]);
		pendingAffectedScripts = ref([]);
		reset() {}
		trackAffectedItem(_tool: string, args: any) {
			if (args.block_id)
				this.pendingAffectedBlocks.value.push({ block_id: args.block_id, changedProps: ["color"] });
		}
		applyToolOperation = mocks.applyTool;
		applyPageYaml = mocks.applyYaml;
	},
}));
vi.mock("./ai/yaml", () => ({
	buildLocalMessage: (role: string, content: string, metadata: any) => ({
		id: crypto.randomUUID(),
		role,
		content,
		metadata,
	}),
}));

import { AIChatController } from "./AIChatController";

function deferred<T>() {
	let resolve!: (value: T) => void;
	let reject!: (reason: unknown) => void;
	const promise = new Promise<T>((yes, no) => {
		resolve = yes;
		reject = no;
	});
	return { promise, resolve, reject };
}
function storage() {
	const values = new Map<string, string>();
	return {
		getItem: (key: string) => values.get(key) ?? null,
		setItem: (key: string, value: string) => values.set(key, value),
		removeItem: (key: string) => values.delete(key),
	};
}
const message = (id: string, content = id, role: "user" | "assistant" = "user"): ChatMessage => ({
	id,
	content,
	role,
});
const run = (id = "run-1", session = "A"): AIRun => ({
	run_id: id,
	session_id: session,
	status: "running",
	model: "model",
	user_message_id: "user-1",
});
const event = (seq: number, runId = "run-1", session = "A"): AIRunEvent => ({
	run_id: runId,
	seq,
	session_id: session,
});
async function settle() {
	for (let i = 0; i < 30; i++) await Promise.resolve();
}

let chat: AIChatController;
let server: AISession;

function readyChat() {
	const controller = new AIChatController();
	controller.availableModels.value = [
		{ provider: "Fixture", models: [{ name: "model", label: "Fixture", ready: true, vision: true }] },
	];
	return controller;
}

beforeEach(() => {
	vi.useFakeTimers();
	vi.clearAllMocks();
	vi.stubGlobal("sessionStorage", storage());
	vi.stubGlobal("window", new EventTarget());
	vi.stubGlobal("document", Object.assign(new EventTarget(), { visibilityState: "visible" }));
	vi.stubGlobal("requestAnimationFrame", (fn: () => void) => setTimeout(fn, 16));
	vi.stubGlobal("cancelAnimationFrame", clearTimeout);
	mocks.route = reactive({ params: { pageId: "page" } });
	mocks.builder = reactive({
		isAIEnabled: true,
		aiEditEpoch: 0,
		aiBuildingCanvas: false,
		canvasDarkMode: false,
		realtime: { on: vi.fn(), off: vi.fn() },
	});
	mocks.canvas = reactive({ editingMode: "page", activeCanvas: null });
	mocks.page = {
		savePage: vi.fn().mockResolvedValue(undefined),
		setPage: vi.fn().mockResolvedValue(undefined),
		pageLoadToken: 0,
		selectedPage: "page",
	};
	server = { session_id: "A", messages: [], active_run: null };
	mocks.api = {
		get_ai_session: vi.fn(async () => structuredClone(server)),
		list_page_ai_sessions: vi.fn().mockResolvedValue([]),
		get_active_build: vi.fn().mockResolvedValue(null),
		run: vi.fn().mockResolvedValue({ status: "accepted", session_id: "A", run_id: "run-1" }),
		cancel: vi.fn().mockResolvedValue({ status: "cancelling" }),
		revert_to_message: vi.fn().mockResolvedValue({ messages: [] }),
		confirm_pending_settings: vi.fn().mockResolvedValue({ resumed: true }),
		delete_ai_session: vi.fn().mockResolvedValue({ status: "ok" }),
		update_session_message_metadata: vi.fn().mockResolvedValue({ status: "ok" }),
	};
	mocks.confirm.mockResolvedValue(true);
	chat = readyChat();
	chat.sessionId.value = "A";
});
afterEach(() => {
	chat.unmount();
	vi.useRealTimers();
	vi.unstubAllGlobals();
});

async function hydrate(active = run()) {
	server.active_run = active;
	server.messages = [message("user-1")];
	await chat.loadSession();
}

describe("session ownership", () => {
	it("blocks sends during an explicit session switch", async () => {
		const read = deferred<AISession>();
		mocks.api.get_ai_session.mockReturnValueOnce(read.promise);
		const switching = chat.switchSession("B");
		chat.prompt.value = "Never send to A";
		await chat.submitPrompt();
		expect(mocks.api.run).not.toHaveBeenCalled();
		read.resolve({ session_id: "B", messages: [message("B-user")], active_run: null });
		await switching;
		expect(chat.sessionId.value).toBe("B");
	});

	it("invalidates an initial history read when sending", async () => {
		const read = deferred<AISession>();
		const admission = deferred<any>();
		mocks.api.get_ai_session.mockReturnValueOnce(read.promise);
		mocks.api.run.mockReturnValueOnce(admission.promise);
		const loading = chat.loadSession();
		chat.prompt.value = "New turn";
		const sending = chat.submitPrompt();
		await settle();
		read.resolve({ session_id: "A", messages: [message("old")], active_run: null });
		await loading;
		expect(chat.messages.value[0].content).toBe("New turn");
		admission.reject(new Error("offline"));
		await sending;
	});

	it("a terminal reload cannot erase the next turn", async () => {
		await hydrate();
		const read = deferred<AISession>();
		const admission = deferred<any>();
		mocks.api.get_ai_session.mockReturnValueOnce(read.promise);
		await chat.onComplete({ ...event(5), message: "Done" });
		chat.prompt.value = "Next turn";
		mocks.api.run.mockReturnValueOnce(admission.promise);
		const sending = chat.submitPrompt();
		await settle();
		read.resolve({ session_id: "A", messages: [message("old")], active_run: null });
		await settle();
		expect(chat.messages.value.at(-2)?.content).toBe("Next turn");
		expect(chat.isSubmitting.value).toBe(true);
		admission.reject(new Error("offline"));
		await sending;
	});

	it("binds action confirmation to its originating session", async () => {
		const response = deferred<any>();
		mocks.api.confirm_pending_settings.mockReturnValueOnce(response.promise);
		const confirming = chat.confirmPendingAction(message("card"), "apply");
		server = { session_id: "B", messages: [message("B-user")], active_run: null };
		await chat.switchSession("B");
		response.resolve({ resumed: true });
		await confirming;
		expect(chat.messages.value.map((m) => m.id)).toEqual(["B-user"]);
		expect(chat.isSubmitting.value).toBe(false);
	});

	it("does not resurrect an already finished confirmation continuation", async () => {
		await chat.confirmPendingAction(message("card"), "apply");
		await settle();
		expect(chat.isSubmitting.value).toBe(false);
		expect(chat.messages.value).toEqual([]);
	});
});

describe("run admission and retry", () => {
	it("preserves every attachment and stable request identity after a lost acceptance", async () => {
		chat.prompt.value = "Use the mock";
		chat.imageData.value = "data:image/png;base64,abc";
		chat.imagePreviewUrl.value = chat.imageData.value;
		chat.imageFileName.value = "mock.png";
		chat.attachedBlocks.value = [{ id: "hero", label: "Hero" }];
		mocks.api.run.mockRejectedValueOnce(new Error("response lost"));
		await chat.submitPrompt();
		const first = mocks.api.run.mock.calls[0][0];
		expect(chat.prompt.value).toBe("Use the mock");
		expect(chat.imageFileName.value).toBe("mock.png");
		expect(chat.attachedBlocks.value).toEqual([{ id: "hero", label: "Hero" }]);
		server.active_run = run();
		await chat.submitPrompt();
		expect(mocks.api.run.mock.calls[1][0]).toEqual(first);
		expect(mocks.page.savePage).toHaveBeenCalledTimes(1);
	});

	it("restores attachments after a failed page save and saves again on retry", async () => {
		chat.prompt.value = "Save me";
		chat.imageData.value = "image";
		chat.attachedBlocks.value = [{ id: "hero", label: "Hero" }];
		mocks.page.savePage.mockRejectedValueOnce(new Error("save failed"));
		await chat.submitPrompt();
		expect(mocks.api.run).not.toHaveBeenCalled();
		expect(chat.imageData.value).toBe("image");
		await chat.submitPrompt();
		expect(mocks.page.savePage).toHaveBeenCalledTimes(2);
	});

	it("recovers a failed first-send envelope across remount and retries with the same UUID", async () => {
		chat.newSession();
		chat.prompt.value = "First message";
		mocks.api.run.mockRejectedValueOnce(new Error("offline"));
		await chat.submitPrompt();
		const first = mocks.api.run.mock.calls[0][0];
		chat.unmount();
		chat = readyChat();
		expect(chat.prompt.value).toBe("First message");
		await chat.submitPrompt();
		expect(mocks.api.run.mock.calls[1][0].request_id).toBe(first.request_id);
	});

	it("resolves a lost first-send response by request_id without sending again", async () => {
		chat.newSession();
		chat.prompt.value = "First message";
		mocks.api.run.mockRejectedValueOnce(new Error("response lost"));
		await chat.submitPrompt();
		const requestId = mocks.api.run.mock.calls[0][0].request_id;
		server = { session_id: "A", messages: [message("accepted-user")], active_run: run(), request_run: run() };
		await chat.reconcile();
		expect(mocks.api.get_ai_session).toHaveBeenLastCalledWith(
			expect.objectContaining({ request_id: requestId }),
		);
		expect(chat.sessionId.value).toBe("A");
		expect(chat.prompt.value).toBe("");
		expect(chat.isSubmitting.value).toBe(true);
		expect(mocks.api.run).toHaveBeenCalledTimes(1);
	});

	it("holds events until the accepted run is known, including existing sessions", async () => {
		const response = deferred<any>();
		mocks.api.run.mockReturnValueOnce(response.promise);
		chat.prompt.value = "Hello";
		const sending = chat.submitPrompt();
		await settle();
		chat.onStream({ ...event(2), chunk: "Early text" });
		chat.onStream({ ...event(2, "old-run"), chunk: "Stale text" });
		server.active_run = run();
		response.resolve({ status: "accepted", session_id: "A", run_id: "run-1" });
		await sending;
		await settle();
		expect(chat.messages.value.at(-1)?.content).toBe("Early text");
	});
});

describe("reconciliation and event identity", () => {
	it("rehydrates a pending assistant and preserves live text during periodic reads", async () => {
		await hydrate();
		chat.onStream({ ...event(1), chunk: "Still writing" });
		const pendingId = chat.messages.value.at(-1)?.id;
		await chat.reconcile();
		expect(chat.messages.value.at(-1)?.id).toBe(pendingId);
		expect(chat.messages.value.at(-1)?.content).toBe("Still writing");
		expect(chat.isSubmitting.value).toBe(true);
		expect(mocks.page.setPage).toHaveBeenCalledWith("page", false);
	});

	it("recovers a missing terminal event and reloads the authoritative page", async () => {
		await hydrate();
		server = {
			session_id: "A",
			messages: [message("user-1"), message("done", "Finished", "assistant")],
			active_run: null,
		};
		await chat.reconcile();
		expect(chat.isSubmitting.value).toBe(false);
		expect(chat.messages.value.at(-1)?.content).toBe("Finished");
		expect(mocks.page.setPage).toHaveBeenCalledWith("page", false);
		chat.onStream({ ...event(99), chunk: "late" });
		expect(chat.messages.value.at(-1)?.content).toBe("Finished");
	});

	it("dedupes exact events without discarding delayed tool batches", async () => {
		await hydrate();
		chat.onStream({ ...event(10), chunk: "Hello" });
		chat.onStream({ ...event(10), chunk: "Hello" });
		const batch = { ...event(3), operations: [{ tool_name: "update_block", args: { block_id: "hero" } }] };
		chat.onToolBatch(batch);
		chat.onToolBatch(batch);
		expect(chat.messages.value.at(-1)?.content).toBe("Hello");
		expect(mocks.applyTool).toHaveBeenCalledTimes(1);
	});

	it("ignores a stale terminal and tool batch from a previous run", async () => {
		await hydrate();
		server.active_run = run("run-2");
		await chat.loadSession();
		await chat.onComplete({ ...event(99), message: "Old completion" });
		chat.onToolBatch({ ...event(100), operations: [{ tool_name: "update_block", args: {} }] });
		expect(chat.activeRun.value?.run_id).toBe("run-2");
		expect(chat.isSubmitting.value).toBe(true);
		expect(mocks.applyTool).not.toHaveBeenCalled();
	});

	it("reconciles on reconnect and bounds polling to one pending request", async () => {
		server.active_run = run();
		await chat.mount();
		const read = deferred<AISession>();
		mocks.api.get_ai_session.mockReturnValueOnce(read.promise);
		const reconnect = mocks.builder.realtime.on.mock.calls.find(([name]: string[]) => name === "connect")[1];
		reconnect();
		reconnect();
		const reads = mocks.api.get_ai_session.mock.calls.length;
		await vi.advanceTimersByTimeAsync(60000);
		expect(mocks.api.get_ai_session).toHaveBeenCalledTimes(reads);
		server.active_run = null;
		read.resolve(server);
		await settle();
		expect(chat.isSubmitting.value).toBe(false);
	});

	it("disposes pending reads, timers and reconnect listeners", async () => {
		const read = deferred<AISession>();
		mocks.api.get_ai_session.mockReturnValueOnce(read.promise);
		const mounting = chat.mount();
		chat.unmount();
		read.resolve({ session_id: "late", active_run: run(), messages: [message("late")] });
		await mounting;
		await vi.advanceTimersByTimeAsync(60000);
		expect(chat.sessionId.value).toBe("A");
		expect(mocks.page.setPage).not.toHaveBeenCalled();
		expect(mocks.builder.realtime.off).toHaveBeenCalledWith("connect", expect.any(Function));
	});
});

describe("cancellation and atomic revert", () => {
	it("targets the queued run and reconciles durable cancellation without a terminal event", async () => {
		await hydrate({ ...run(), status: "queued" });
		mocks.api.cancel.mockImplementationOnce(async () => {
			server.active_run = null;
			return { status: "cancelled" };
		});
		await chat.cancel();
		expect(mocks.api.cancel).toHaveBeenCalledWith({ session_id: "A", run_id: "run-1" });
		expect(chat.isSubmitting.value).toBe(false);
		expect(chat.isCancelling.value).toBe(false);
		expect(mocks.page.setPage).toHaveBeenCalled();
	});

	it("never claims a still-running provider ended after a cancellation timeout", async () => {
		server.active_run = run();
		await chat.mount();
		await chat.cancel();
		await vi.advanceTimersByTimeAsync(60000);
		expect(chat.isSubmitting.value).toBe(true);
		expect(chat.isCancelling.value).toBe(true);
		expect(mocks.info).not.toHaveBeenCalled();
	});

	it("cancels after a first-send admission response arrives", async () => {
		chat.newSession();
		const admission = deferred<any>();
		mocks.api.run.mockReturnValueOnce(admission.promise);
		chat.prompt.value = "Build";
		const sending = chat.submitPrompt();
		await settle();
		await chat.cancel();
		expect(mocks.api.cancel).not.toHaveBeenCalled();
		server.active_run = run();
		admission.resolve({ status: "accepted", session_id: "A", run_id: "run-1" });
		await sending;
		await settle();
		expect(mocks.api.cancel).toHaveBeenCalledWith({ session_id: "A", run_id: "run-1" });
	});

	it("restores only through the atomic endpoint, then refreshes the page", async () => {
		chat.messages.value = [message("before")];
		mocks.api.revert_to_message.mockResolvedValueOnce({ messages: [message("kept")] });
		await chat.revertTurn({ ...message("turn"), metadata: { revertSnapshot: "snapshot" } });
		expect(mocks.api.revert_to_message).toHaveBeenCalledWith({ session_id: "A", message_id: "turn" });
		expect(chat.messages.value.map((m) => m.id)).toEqual(["kept"]);
		expect(mocks.page.setPage).toHaveBeenCalledWith("page", false);
	});

	it("surfaces expired-snapshot errors and preserves both transcript and page", async () => {
		chat.messages.value = [message("kept")];
		mocks.api.revert_to_message.mockRejectedValueOnce(new Error("Restore point expired"));
		await expect(
			chat.revertTurn({ ...message("turn"), metadata: { revertSnapshot: "expired" } }),
		).rejects.toThrow("expired");
		expect(chat.messages.value.map((m) => m.id)).toEqual(["kept"]);
		expect(mocks.page.setPage).not.toHaveBeenCalled();
		expect(mocks.error).toHaveBeenCalledWith("Restore point expired");
	});
});

describe("generation identity", () => {
	it("uses UTF-16 offsets and resets them for each generation in one run", async () => {
		await hydrate();
		chat.onStream({ ...event(1), kind: "page_yaml", generation_id: "one", chunk: "😀", offset: 0 });
		chat.onStream({ ...event(2), kind: "page_yaml", generation_id: "one", chunk: " hi", offset: 2 });
		await vi.advanceTimersByTimeAsync(200);
		expect(mocks.applyYaml).toHaveBeenLastCalledWith("😀 hi");
		chat.onStream({ ...event(3), kind: "page_yaml", generation_id: "two", chunk: "new", offset: 0 });
		chat.onStream({ ...event(4), kind: "page_yaml", generation_id: "one", chunk: "stale", offset: 5 });
		await vi.advanceTimersByTimeAsync(200);
		expect(mocks.applyYaml).toHaveBeenLastCalledWith("new");
	});

	it("resets offsets for successive foreign-session builds", async () => {
		mocks.api.get_active_build.mockResolvedValue({
			run_id: "foreign-1",
			generation_id: "foreign-gen-1",
			yaml: "old and long",
		});
		mocks.api.get_ai_session.mockImplementation(async ({ session_id }) =>
			session_id === "B" ? { session_id: "B", active_run: run("foreign-1", "B"), messages: [] } : server,
		);
		chat.onStream({
			...event(1, "foreign-1", "B"),
			kind: "page_yaml",
			generation_id: "foreign-gen-1",
			chunk: "old and long",
			offset: 0,
		});
		await settle();
		await chat.onComplete({ ...event(2, "foreign-1", "B") });
		await settle();
		mocks.api.get_ai_session.mockImplementation(async ({ session_id }) =>
			session_id === "B" ? { session_id: "B", active_run: run("foreign-2", "B"), messages: [] } : server,
		);
		mocks.api.get_active_build.mockResolvedValue({
			run_id: "foreign-2",
			generation_id: "foreign-gen-2",
			yaml: "new",
		});
		chat.onStream({
			...event(1, "foreign-2", "B"),
			kind: "page_yaml",
			generation_id: "foreign-gen-2",
			chunk: "new",
			offset: 0,
		});
		await settle();
		await vi.advanceTimersByTimeAsync(200);
		expect(mocks.applyYaml).toHaveBeenLastCalledWith("new");
		expect(chat.messages.value).toEqual([]);
	});

	it("rejects a buffered build response arriving after its terminal event", async () => {
		await hydrate();
		const build = deferred<any>();
		mocks.api.get_active_build.mockReturnValueOnce(build.promise);
		const reconciling = chat.reconcile();
		await settle();
		server.active_run = null;
		await chat.onComplete(event(10));
		build.resolve({ run_id: "run-1", generation_id: "late", yaml: "stale preview" });
		await reconciling;
		expect(mocks.applyYaml).not.toHaveBeenCalled();
	});
});

describe("draft and delayed response boundaries", () => {
	it("keeps an explicitly blank chat selected while polling", async () => {
		chat.newSession();
		chat.prompt.value = "Unsent new brief";
		await chat.reconcile();
		expect(chat.sessionId.value).toBe("");
		expect(chat.prompt.value).toBe("Unsent new brief");
		expect(mocks.api.get_ai_session).not.toHaveBeenCalled();
	});

	it("does not replace an unknown first request with an unrelated latest chat", async () => {
		chat.newSession();
		chat.prompt.value = "Keep this draft";
		mocks.api.run.mockRejectedValueOnce(new Error("offline"));
		await chat.submitPrompt();
		server = { session_id: "unrelated", messages: [message("other")], active_run: null, request_run: null };
		await chat.reconcile();
		expect(chat.sessionId.value).toBe("");
		expect(chat.prompt.value).toBe("Keep this draft");
		expect(chat.messages.value).toEqual([]);
	});

	it("does not send the previous session's retry identity when switching chats", async () => {
		chat.prompt.value = "Failed in A";
		mocks.api.run.mockRejectedValueOnce(new Error("offline"));
		await chat.submitPrompt();
		server = { session_id: "B", messages: [], active_run: null };
		await chat.switchSession("B");
		expect(mocks.api.get_ai_session.mock.calls.at(-1)?.[0]).not.toHaveProperty("request_id");
		expect(chat.sessionId.value).toBe("B");
	});

	it("retains an edited composer when an earlier uncertain request is found", async () => {
		chat.prompt.value = "Original message";
		mocks.api.run.mockRejectedValueOnce(new Error("lost response"));
		await chat.submitPrompt();
		chat.prompt.value = "A different draft for later";
		server = { session_id: "A", messages: [message("user-1")], active_run: run(), request_run: run() };
		await chat.reconcile();
		expect(chat.prompt.value).toBe("A different draft for later");
		expect(chat.isSubmitting.value).toBe(true);
	});

	it("does not let a late cancellation response change a different chat's run", async () => {
		await hydrate();
		const cancelled = deferred<any>();
		mocks.api.cancel.mockReturnValueOnce(cancelled.promise);
		const cancelling = chat.cancel();
		server = { session_id: "B", messages: [message("B-user")], active_run: run("B-run", "B") };
		await chat.switchSession("B");
		cancelled.resolve({ status: "cancelled" });
		await cancelling;
		expect(chat.activeRun.value?.run_id).toBe("B-run");
		expect(chat.isSubmitting.value).toBe(true);
		expect(chat.isCancelling.value).toBe(false);
	});

	it("preserves text arriving while the reconciliation read is in flight", async () => {
		await hydrate();
		const read = deferred<AISession>();
		mocks.api.get_ai_session.mockReturnValueOnce(read.promise);
		const reconciling = chat.reconcile();
		chat.onStream({ ...event(1), chunk: "Arrived during read" });
		read.resolve(server);
		await reconciling;
		expect(chat.messages.value.at(-1)?.content).toBe("Arrived during read");
	});

	it("recovers a UTF-16 stream gap from the identified server buffer", async () => {
		await hydrate();
		mocks.api.get_active_build.mockResolvedValueOnce({
			run_id: "run-1",
			generation_id: "gen",
			yaml: "😀 missed tail",
		});
		chat.onStream({ ...event(1), kind: "page_yaml", generation_id: "gen", chunk: "😀", offset: 0 });
		chat.onStream({ ...event(3), kind: "page_yaml", generation_id: "gen", chunk: "tail", offset: 10 });
		await settle();
		await vi.advanceTimersByTimeAsync(200);
		expect(mocks.applyYaml).toHaveBeenLastCalledWith("😀 missed tail");
	});
});

it("keeps an edited first-send draft when request recovery binds its newly created session", async () => {
	chat.newSession();
	chat.prompt.value = "First request";
	mocks.api.run.mockRejectedValueOnce(new Error("response lost"));
	await chat.submitPrompt();
	chat.prompt.value = "Later draft";
	chat.attachedBlocks.value = [{ id: "footer", label: "Footer" }];
	server = { session_id: "A", messages: [message("user-1")], active_run: run(), request_run: run() };
	await chat.reconcile();
	expect(chat.sessionId.value).toBe("A");
	expect(chat.prompt.value).toBe("Later draft");
	expect(chat.attachedBlocks.value).toEqual([{ id: "footer", label: "Footer" }]);
});

it("persists affected-item metadata against the completed run rather than the last assistant", async () => {
	await hydrate();
	chat.onToolBatch({
		...event(2),
		operations: [{ tool_name: "update_block", args: { block_id: "hero", base_styles: { color: "red" } } }],
	});
	server = {
		session_id: "A",
		active_run: null,
		messages: [message("user-1"), { ...message("done", "Done", "assistant"), metadata: { runId: "run-1" } }],
	};
	await chat.onComplete(event(3));
	await settle();
	expect(mocks.api.update_session_message_metadata).toHaveBeenCalledWith({
		session_id: "A",
		run_id: "run-1",
		metadata: { affectedBlocks: [{ block_id: "hero", changedProps: ["color"] }], affectedScripts: [] },
	});
	expect(chat.messages.value.at(-1)?.metadata?.affectedBlocks).toEqual([
		{ block_id: "hero", changedProps: ["color"] },
	]);
});
