import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it, vi } from "vitest";

// index.html runs this before any app code, as a classic script: the test runs the very text it ships
const html = readFileSync(path.resolve(import.meta.dirname, "../../index.html"), "utf8");
const script = html.match(/<script id="fp-site-storage">([\s\S]*?)<\/script>/)![1];

type Listener = { handler: (event: FakeStorageEvent) => void; capture: boolean };

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
function browserWindow(origin: ReturnType<typeof sharedOrigin>, boot: { mount?: string; site?: string }) {
	class Storage {
		constructor(readonly items: Map<string, string>) {}
		getItem(key: string) {
			return this.items.get(String(key)) ?? null;
		}
		setItem(key: string, value: string) {
			this.items.set(String(key), String(value));
		}
		removeItem(key: string) {
			this.items.delete(String(key));
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
	class IDBDatabase {
		constructor(readonly storedName: string) {}
		get name() {
			return this.storedName;
		}
	}
	class IDBFactory {
		open(name: string) {
			origin.databases.add(name);
			return { result: new IDBDatabase(name) };
		}
		deleteDatabase(name: string) {
			origin.databases.delete(name);
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
		fp: boot.mount ? { mount: boot.mount } : {},
		site_name: boot.site,
		Storage,
		StorageEvent,
		IDBFactory,
		IDBDatabase,
		BroadcastChannel,
		localStorage: new Storage(origin.local),
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
	return win;
}

function sharedOrigin() {
	return {
		local: new Map<string, string>(),
		session: new Map<string, string>(),
		databases: new Set<string>(),
		channels: [] as string[],
	};
}

const twoSites = () => {
	const origin = sharedOrigin();
	return {
		origin,
		a: browserWindow(origin, { mount: "/acme", site: "s-aaaaaaaaaa" }),
		b: browserWindow(origin, { mount: "/bolt", site: "s-bbbbbbbbbb" }),
	};
};

describe("each mounted site's browser storage", () => {
	it("keeps a key one site sets out of another's", () => {
		const { origin, a, b } = twoSites();
		a.localStorage.setItem("activeFolder", "Fronds 2");

		expect(a.localStorage.getItem("activeFolder")).toBe("Fronds 2");
		expect(b.localStorage.getItem("activeFolder")).toBeNull();
		expect([...origin.local.keys()]).toEqual(["fp:s-aaaaaaaaaa:activeFolder"]);
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

		fromTab("fp:s-aaaaaaaaaa:displayType");
		fromTab("fp:s-bbbbbbbbbb:displayType");
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

		expect([...origin.databases]).toEqual(["fp:s-aaaaaaaaaa:keyval-store", "fp:s-bbbbbbbbbb:keyval-store"]);
		expect(database.name).toBe("keyval-store");
		expect(await a.indexedDB.databases()).toEqual([{ name: "keyval-store", version: 1 }]);

		a.indexedDB.deleteDatabase("keyval-store");
		expect([...origin.databases]).toEqual(["fp:s-bbbbbbbbbb:keyval-store"]);
	});

	it("names BroadcastChannels per site", () => {
		const { origin, a } = twoSites();
		const channel = new a.BroadcastChannel("builder-detached-preview");
		expect(origin.channels).toEqual(["fp:s-aaaaaaaaaa:builder-detached-preview"]);
		expect(channel.name).toBe("builder-detached-preview");
		expect(channel).toBeInstanceOf(a.BroadcastChannel);
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
		const seen = vi.fn();
		stock.addEventListener("storage", (event: FakeStorageEvent) => seen(event.key));
		stock.dispatchStorageEvent(new stock.StorageEvent("activeFolder", "x", true));
		expect(seen).toHaveBeenCalledWith("activeFolder");
	});
});
