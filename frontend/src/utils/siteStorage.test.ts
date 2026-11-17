import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it, vi } from "vitest";

// index.html runs this before any app code, as a classic script: the test runs the very text it ships
const html = readFileSync(path.resolve(import.meta.dirname, "../../index.html"), "utf8");
const script = html.match(/<script id="fp-site-storage">([\s\S]*?)<\/script>/)![1];

type Listener = { handler: (event: FakeStorageEvent) => void; capture: boolean };
type Handler = (event: { type: string }) => void;

/** An IndexedDB request or connection: its listeners, and the on<type> handlers idb-keyval sets. */
class FakeEvents {
	readonly listeners = new Map<string, Handler[]>();
	onsuccess: Handler | null = null;
	onerror: Handler | null = null;
	onblocked: Handler | null = null;
	addEventListener(type: string, handler: Handler) {
		this.listeners.set(type, [...(this.listeners.get(type) ?? []), handler]);
	}
	fire(type: string) {
		for (const handler of this.listeners.get(type) ?? []) handler({ type });
		(this as unknown as Record<string, Handler | null>)[`on${type}`]?.({ type });
	}
}

/** what a browser runs after the current task: request events, a blocked delete going ahead */
const settle = () => new Promise((resolve) => setTimeout(resolve, 0));

interface FakeStorageEvent {
	readonly key: string | null;
	readonly newValue: string | null;
	readonly isTrusted: boolean;
	stopped: boolean;
	stopImmediatePropagation(): void;
}

/**
 * The browser APIs the script wraps, each window with prototypes of its own (the script patches them), over
 * stores shared like one origin's: `origin` is what every site on frappe.page writes to.
 */
function browserWindow(
	origin: ReturnType<typeof sharedOrigin>,
	boot: { mount?: string; site?: string; user?: string },
) {
	// localStorage tells the origin's other windows of each change, as the browser does with storage events
	class Storage {
		constructor(
			readonly items: Map<string, string>,
			readonly tellsOtherTabs = false,
		) {}
		getItem(key: string) {
			return this.items.get(String(key)) ?? null;
		}
		setItem(key: string, value: string) {
			const changed = this.items.get(String(key)) !== String(value);
			this.items.set(String(key), String(value));
			if (changed && this.tellsOtherTabs) origin.changed(win, String(key), String(value));
		}
		removeItem(key: string) {
			const had = this.items.delete(String(key));
			if (had && this.tellsOtherTabs) origin.changed(win, String(key), null);
		}
		key(index: number) {
			return [...this.items.keys()][index] ?? null;
		}
		clear() {
			this.items.clear();
		}
		get length() {
			return this.items.size;
		}
	}
	// a trusted event comes from another tab, an untrusted one from the app's own dispatchEvent
	class StorageEvent implements FakeStorageEvent {
		stopped = false;
		#key: string | null;
		constructor(
			key: string | null,
			readonly newValue: string | null,
			readonly isTrusted: boolean,
		) {
			this.#key = key;
		}
		get key() {
			return this.#key;
		}
		stopImmediatePropagation() {
			this.stopped = true;
		}
	}
	class IDBDatabase extends FakeEvents {
		closed = false;
		constructor(readonly storedName: string) {
			super();
		}
		get name() {
			return this.storedName;
		}
		close() {
			this.closed = true;
			origin.disconnect(this);
		}
	}
	class IDBFactory {
		open(name: string) {
			const request = Object.assign(new FakeEvents(), { result: new IDBDatabase(name) });
			origin.connect(request.result);
			queueMicrotask(() => request.fire("success"));
			return request;
		}
		deleteDatabase(name: string) {
			const request = new FakeEvents();
			queueMicrotask(() => origin.deleteWhenFree(name, request));
			return request;
		}
		async databases() {
			return [...origin.databases].map((name) => ({ name, version: 1 }));
		}
	}
	class BroadcastChannel {
		constructor(readonly storedName: string) {
			origin.channels.push(storedName);
		}
		get name() {
			return this.storedName;
		}
	}

	const listeners: Listener[] = [];
	const win = {
		fp: (boot.mount ? { mount: boot.mount, user: boot.user } : {}) as { forgetUser?: () => Promise<void> },
		site_name: boot.site,
		Storage,
		StorageEvent,
		IDBFactory,
		IDBDatabase,
		BroadcastChannel,
		localStorage: new Storage(origin.local, true),
		sessionStorage: new Storage(origin.session),
		indexedDB: new IDBFactory(),
		addEventListener(type: string, handler: Listener["handler"], capture = false) {
			if (type === "storage") listeners.push({ handler, capture });
		},
		/** the browser's order: capturing listeners on the window first, until one stops the event */
		dispatchStorageEvent(event: FakeStorageEvent) {
			for (const { handler } of [
				...listeners.filter((l) => l.capture),
				...listeners.filter((l) => !l.capture),
			]) {
				if (event.stopped) return;
				handler(event);
			}
		},
	};
	new Function("window", script)(win);
	origin.windows.push(win);
	return win;
}

type FakeConnection = FakeEvents & { storedName: string; closed: boolean };
type FakeWindow = {
	StorageEvent: new (key: string | null, newValue: string | null, isTrusted: boolean) => FakeStorageEvent;
	dispatchStorageEvent(event: FakeStorageEvent): void;
};

function sharedOrigin() {
	const databases = new Set<string>();
	const connections = new Set<FakeConnection>();
	const waiting: { name: string; request: FakeEvents }[] = [];
	const held = (name: string) => [...connections].some((connection) => connection.storedName === name);
	const remove = (name: string, request: FakeEvents) => {
		databases.delete(name);
		request.fire("success");
	};
	const windows: FakeWindow[] = [];
	return {
		local: new Map<string, string>(),
		session: new Map<string, string>(),
		databases,
		channels: [] as string[],
		windows,
		/** each other window hears of a localStorage change after the current task, in the order made */
		changed(from: FakeWindow, key: string, newValue: string | null) {
			for (const other of windows)
				if (other !== from)
					queueMicrotask(() => other.dispatchStorageEvent(new other.StorageEvent(key, newValue, true)));
		},
		connect(connection: FakeConnection) {
			databases.add(connection.storedName);
			connections.add(connection);
		},
		disconnect(connection: FakeConnection) {
			connections.delete(connection);
			for (const entry of [...waiting].filter(({ name }) => !held(name))) {
				waiting.splice(waiting.indexOf(entry), 1);
				remove(entry.name, entry.request);
			}
		},
		/** as a browser does: each connection hears of it first, and the delete waits for those that stay open */
		deleteWhenFree(name: string, request: FakeEvents) {
			for (const connection of [...connections])
				if (connection.storedName === name) connection.fire("versionchange");
			if (!held(name)) return remove(name, request);
			waiting.push({ name, request });
			request.fire("blocked");
		},
	};
}

const MEMBER = "member+1@example.com";
/** how the script writes MEMBER in a prefix */
const M = "member%2B1%40example.com";

const twoSites = () => {
	const origin = sharedOrigin();
	return {
		origin,
		a: browserWindow(origin, { mount: "/acme", site: "s-aaaaaaaaaa", user: MEMBER }),
		b: browserWindow(origin, { mount: "/bolt", site: "s-bbbbbbbbbb", user: MEMBER }),
	};
};

describe("each mounted site's browser storage", () => {
	it("keeps a key one site sets out of another's", () => {
		const { origin, a, b } = twoSites();
		a.localStorage.setItem("activeFolder", "Fronds 2");

		expect(a.localStorage.getItem("activeFolder")).toBe("Fronds 2");
		expect(b.localStorage.getItem("activeFolder")).toBeNull();
		expect([...origin.local.keys()]).toEqual([`fp:s-aaaaaaaaaa:${M}:activeFolder`]);
	});

	it("scopes sessionStorage the same way", () => {
		const { a, b } = twoSites();
		a.sessionStorage.setItem("copiedStyle", "{}");
		expect(b.sessionStorage.getItem("copiedStyle")).toBeNull();
		a.sessionStorage.removeItem("copiedStyle");
		expect(a.sessionStorage.getItem("copiedStyle")).toBeNull();
	});

	it("shares the color scheme, stored under its own name for frappe.page's pages", () => {
		const { origin, a, b } = twoSites();
		a.localStorage.setItem("vueuse-color-scheme", "dark");
		b.localStorage.setItem("theme", "dark");

		expect(b.localStorage.getItem("vueuse-color-scheme")).toBe("dark");
		expect(a.localStorage.getItem("theme")).toBe("dark");
		expect(origin.local.get("vueuse-color-scheme")).toBe("dark");
	});

	it("lists and clears only the site's own keys, leaving the shared ones", () => {
		const { origin, a, b } = twoSites();
		a.localStorage.setItem("displayType", "list");
		b.localStorage.setItem("displayType", "grid");
		b.localStorage.setItem("orderBy", "modified");
		a.localStorage.setItem("vueuse-color-scheme", "dark");
		origin.local.set("fp-chosen-subdomain", "{}"); // a frappe.page page's own key

		const listed = Array.from({ length: b.localStorage.length }, (_, index) => b.localStorage.key(index));
		expect(listed.sort()).toEqual(["displayType", "orderBy", "vueuse-color-scheme"]);
		expect(b.localStorage.key(listed.length)).toBeNull();

		b.localStorage.clear();
		expect(b.localStorage.length).toBe(1);
		expect(a.localStorage.getItem("displayType")).toBe("list");
		expect(a.localStorage.getItem("vueuse-color-scheme")).toBe("dark");
		expect(origin.local.get("fp-chosen-subdomain")).toBe("{}");
	});

	it("passes another tab's write on this site under the app's key, and stops other sites' writes", () => {
		const { a } = twoSites();
		const seen = vi.fn();
		a.addEventListener("storage", (event: FakeStorageEvent) => seen(event.key, event.newValue));
		const fromTab = (key: string) => a.dispatchStorageEvent(new a.StorageEvent(key, "x", true));

		fromTab(`fp:s-aaaaaaaaaa:${M}:displayType`);
		fromTab(`fp:s-bbbbbbbbbb:${M}:displayType`);
		fromTab("fp:s-aaaaaaaaaa:other%40example.com:displayType"); // another member of this site
		fromTab("displayType"); // a page that is no site's editor
		fromTab("vueuse-color-scheme");

		expect(seen.mock.calls).toEqual([
			["displayType", "x"],
			["vueuse-color-scheme", "x"],
		]);
	});

	it("leaves an event the app dispatches itself as the app wrote it", () => {
		const { a } = twoSites();
		const seen = vi.fn();
		a.addEventListener("storage", (event: FakeStorageEvent) => seen(event.key));
		a.dispatchStorageEvent(new a.StorageEvent("displayType", "list", false));
		expect(seen).toHaveBeenCalledWith("displayType");
	});

	it("opens and lists IndexedDB databases of the site's own", async () => {
		const { origin, a, b } = twoSites();
		const database = a.indexedDB.open("keyval-store").result;
		b.indexedDB.open("keyval-store");

		expect([...origin.databases]).toEqual([
			`fp:s-aaaaaaaaaa:${M}:keyval-store`,
			`fp:s-bbbbbbbbbb:${M}:keyval-store`,
		]);
		expect(database.name).toBe("keyval-store");
		expect(await a.indexedDB.databases()).toEqual([{ name: "keyval-store", version: 1 }]);

		a.indexedDB.deleteDatabase("keyval-store");
		await settle();
		expect([...origin.databases]).toEqual([`fp:s-bbbbbbbbbb:${M}:keyval-store`]);
		expect(database.closed).toBe(true); // it gave way to the delete
	});

	it("names BroadcastChannels per site", () => {
		const { origin, a } = twoSites();
		const channel = new a.BroadcastChannel("builder-detached-preview");
		expect(origin.channels).toEqual([`fp:s-aaaaaaaaaa:${M}:builder-detached-preview`]);
		expect(channel.name).toBe("builder-detached-preview");
		expect(channel).toBeInstanceOf(a.BroadcastChannel);
	});
});

describe("each member of one site, signed in on one browser in turn", () => {
	const twoMembers = () => {
		const origin = sharedOrigin();
		const site = { mount: "/acme", site: "s-aaaaaaaaaa" };
		return {
			origin,
			x: browserWindow(origin, { ...site, user: "x@example.com" }),
			y: browserWindow(origin, { ...site, user: "y@example.com" }),
		};
	};

	it("never sees the other's keys, cache or channels", async () => {
		const { origin, x, y } = twoMembers();
		x.localStorage.setItem("activeFolder", "X only");
		x.localStorage.setItem("pageCreatedByFilter", "x@example.com");
		x.sessionStorage.setItem("builder:pending-asset-import", "{}");
		x.indexedDB.open("keyval-store");
		new x.BroadcastChannel("builder-detached-preview");

		expect(y.localStorage.getItem("activeFolder")).toBeNull();
		expect(y.localStorage.getItem("pageCreatedByFilter")).toBeNull();
		expect(y.localStorage.length).toBe(0);
		expect(y.sessionStorage.getItem("builder:pending-asset-import")).toBeNull();
		expect(await y.indexedDB.databases()).toEqual([]);
		y.indexedDB.open("keyval-store");
		new y.BroadcastChannel("builder-detached-preview");

		expect([...origin.local.keys()].sort()).toEqual([
			"fp:s-aaaaaaaaaa:x%40example.com:activeFolder",
			"fp:s-aaaaaaaaaa:x%40example.com:pageCreatedByFilter",
		]);
		expect([...origin.databases]).toEqual([
			"fp:s-aaaaaaaaaa:x%40example.com:keyval-store",
			"fp:s-aaaaaaaaaa:y%40example.com:keyval-store",
		]);
		expect(origin.channels).toEqual([
			"fp:s-aaaaaaaaaa:x%40example.com:builder-detached-preview",
			"fp:s-aaaaaaaaaa:y%40example.com:builder-detached-preview",
		]);
	});

	it("clears only its own keys, and finds the first member's again when that member is back", () => {
		const { origin, x, y } = twoMembers();
		x.localStorage.setItem("displayType", "list");
		y.localStorage.setItem("displayType", "grid");
		y.localStorage.clear();

		const xAgain = browserWindow(origin, { mount: "/acme", site: "s-aaaaaaaaaa", user: "x@example.com" });
		expect(xAgain.localStorage.getItem("displayType")).toBe("list");
		expect(y.localStorage.getItem("displayType")).toBeNull();
	});

	it("still shares the color scheme", () => {
		const { x, y } = twoMembers();
		x.localStorage.setItem("vueuse-color-scheme", "dark");
		expect(y.localStorage.getItem("vueuse-color-scheme")).toBe("dark");
	});
});

describe("Sign Out (fp.forgetUser)", () => {
	const browser = () => {
		const origin = sharedOrigin();
		const editor = (site: string, user: string) => browserWindow(origin, { mount: "/" + site, site, user });
		return {
			origin,
			xOnA: editor("s-aaaaaaaaaa", "x@example.com"),
			xOnB: editor("s-bbbbbbbbbb", "x@example.com"),
			yOnA: editor("s-aaaaaaaaaa", "y@example.com"),
		};
	};

	it("forgets what every site's editor kept for the user, and nothing else", async () => {
		const { origin, xOnA, xOnB, yOnA } = browser();
		xOnA.localStorage.setItem("activeFolder", "X only");
		xOnB.localStorage.setItem("pageCreatedByFilter", "x@example.com");
		xOnA.sessionStorage.setItem("copiedStyle", "{}");
		yOnA.localStorage.setItem("activeFolder", "Y only");
		xOnA.localStorage.setItem("vueuse-color-scheme", "dark");
		origin.local.set("fp-chosen-subdomain", "{}"); // a frappe.page page's own key
		const xDatabase = xOnA.indexedDB.open("keyval-store").result; // open in this very tab, as idb-keyval keeps it
		xOnB.indexedDB.open("keyval-store");
		const yDatabase = yOnA.indexedDB.open("keyval-store").result;
		await settle();

		await xOnA.fp.forgetUser!();

		expect([...origin.local.keys()].sort()).toEqual([
			"fp-chosen-subdomain",
			"fp:s-aaaaaaaaaa:y%40example.com:activeFolder",
			"vueuse-color-scheme",
		]);
		expect([...origin.session.keys()]).toEqual([]);
		expect([...origin.databases]).toEqual(["fp:s-aaaaaaaaaa:y%40example.com:keyval-store"]);
		expect([xDatabase.closed, yDatabase.closed]).toEqual([true, false]);
	});

	/** vueuse's useStorage in an editor tab: a key another tab removed is written back with the app's default */
	const writesDefaultsBack = (tab: ReturnType<typeof browserWindow>) =>
		tab.addEventListener("storage", (event: FakeStorageEvent) => {
			if (event.key && event.newValue === null) tab.localStorage.setItem(event.key, "default");
		});
	const xKeys = (origin: ReturnType<typeof sharedOrigin>) =>
		[...origin.local.keys()].filter((key) => key.includes(":x%40example.com:"));
	const signOuts = {
		"the editor's Sign Out": (tabs: ReturnType<typeof browser>) => tabs.xOnA.fp.forgetUser!(),
		// control.js: the user named under fp-signed-out first, then the user's keys removed
		"frappe.page's sign-out": async ({ origin }: ReturnType<typeof browser>) => {
			const controlPage = browserWindow(origin, {});
			controlPage.localStorage.setItem("fp-signed-out", JSON.stringify({ user: "x%40example.com", at: 1 }));
			controlPage.localStorage.removeItem("fp-signed-out");
			for (const key of xKeys(origin)) controlPage.localStorage.removeItem(key);
		},
	};

	for (const [signOut, run] of Object.entries(signOuts)) {
		it(`leaves nothing for the user's other tabs to write back after ${signOut}`, async () => {
			const tabs = browser();
			const { origin, xOnA, yOnA } = tabs;
			const xElsewhere = browserWindow(origin, { mount: "/a", site: "s-aaaaaaaaaa", user: "x@example.com" });
			writesDefaultsBack(xElsewhere);
			writesDefaultsBack(yOnA);
			xOnA.localStorage.setItem("activeFolder", "X only");
			xElsewhere.localStorage.setItem("displayType", "list");
			await settle();

			await run(tabs);
			await settle();
			expect(xKeys(origin)).toEqual([]);

			xElsewhere.localStorage.setItem("displayType", "grid"); // what that tab still holds, written later
			xElsewhere.localStorage.setItem("vueuse-color-scheme", "dark");
			yOnA.localStorage.setItem("displayType", "grid");
			await settle();
			expect(xKeys(origin)).toEqual([]);
			expect(origin.local.get("vueuse-color-scheme")).toBe("dark");
			expect(yOnA.localStorage.getItem("displayType")).toBe("grid"); // another account's tab carries on
		});
	}

	it("does not wait on a tab that holds a database open, which goes once that tab lets go", async () => {
		const { origin, xOnA } = browser();
		const name = "fp:s-aaaaaaaaaa:x%40example.com:keyval-store";
		// an editor tab from before this script made connections give way: it opens the name as stored
		const olderTab = browserWindow(origin, {}).indexedDB.open(name).result;
		await settle();

		await xOnA.fp.forgetUser!();
		expect([...origin.databases]).toEqual([name]);

		olderTab.close();
		expect([...origin.databases]).toEqual([]);
	});
});

describe("stock Builder, not mounted", () => {
	it("keeps the browser's storage exactly as it is", async () => {
		const origin = sharedOrigin();
		const stock = browserWindow(origin, { site: "builder.example.com" });
		const Storage = stock.Storage as unknown as { prototype: object };
		const before = Object.getOwnPropertyDescriptors(Storage.prototype);

		stock.localStorage.setItem("activeFolder", "Fronds 2");
		stock.indexedDB.open("keyval-store");
		new stock.BroadcastChannel("builder-detached-preview");

		expect(Object.getOwnPropertyDescriptors(Storage.prototype)).toEqual(before);
		expect([...origin.local.keys()]).toEqual(["activeFolder"]);
		expect([...origin.databases]).toEqual(["keyval-store"]);
		expect(origin.channels).toEqual(["builder-detached-preview"]);
		expect(stock.fp.forgetUser).toBeUndefined();
		const seen = vi.fn();
		stock.addEventListener("storage", (event: FakeStorageEvent) => seen(event.key));
		stock.dispatchStorageEvent(new stock.StorageEvent("activeFolder", "x", true));
		expect(seen).toHaveBeenCalledWith("activeFolder");
	});
});
