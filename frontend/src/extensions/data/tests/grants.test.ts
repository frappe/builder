import { beforeEach, describe, expect, it, vi } from "vitest";
import { reactive } from "vue";

/**
 * The Frappe call is mocked. What is under test is when a dialog opens at all,
 * what it is asked about, and what travels to the record — not the round trip.
 */
type Call = { url: string; params: Record<string, unknown> };

const submitted: Call[] = [];
let stored: Record<string, unknown> = {};

vi.mock("frappe-ui", () => ({
	createResource: ({ url }: { url: string }) => ({
		submit: (params: Record<string, unknown>) => {
			submitted.push({ url, params });
			// reactive, because createResource keeps its data reactive and a Vue
			// proxy cannot cross postMessage
			return Promise.resolve(reactive({ doctype: params.doctype, ...stored }));
		},
	}),
}));

const teardowns = new Map<string, () => void>();

vi.mock("../../host/bridge", () => ({
	bridge: {
		registerTeardown: (extensionName: string, cleanup: () => void) => teardowns.set(extensionName, cleanup),
	},
}));

import { answerPrompt, grantMethods, pendingPrompt, SENSITIVE_DOCTYPES } from "../grants";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";

const record = (name = "acme/crm"): InstalledExtension => ({
	name,
	label: name === "acme/crm" ? "CRM" : "Other",
	entry: `/builder_extension_asset/${name.replace("/", "-")}@1.0.0/main.js`,
	capabilities: ["data.access"],
});

const NONE = { read: "not asked", write: "not asked", delete: "not asked" };

const request = (params: unknown, extension = record()) =>
	grantMethods["data.requestAccess"].run(params, extension) as Promise<Record<string, unknown>>;

const getAccess = (params: unknown, extension = record()) =>
	grantMethods["data.getAccess"].run(params, extension) as Promise<Record<string, unknown>>;

/** Lets the pending `readGrant` promise settle so the prompt is on screen. */
const settled = () => new Promise((resolve) => setTimeout(resolve, 0));

const codeOf = async (call: () => unknown) => {
	try {
		await call();
	} catch (error) {
		return (error as { code?: string }).code;
	}
	return undefined;
};

const urls = () => submitted.map((call) => call.url);

const lastCall = (url: string) => [...submitted].reverse().find((call) => call.url.endsWith(url));

beforeEach(() => {
	submitted.length = 0;
	stored = { ...NONE };
	if (pendingPrompt.value) answerPrompt(false);
	submitted.length = 0;
});

describe("the capability", () => {
	it("gates both behind data.access", () => {
		expect(grantMethods["data.requestAccess"].needs).toBe("data.access");
		expect(grantMethods["data.getAccess"].needs).toBe("data.access");
	});
});

describe("what a frame sent", () => {
	it("refuses a missing doctype", async () => {
		expect(await codeOf(() => request({ access: ["read"] }))).toBe("invalid_params");
	});

	it("refuses an empty access list", async () => {
		expect(await codeOf(() => request({ doctype: "Contact", access: [] }))).toBe("invalid_params");
	});

	it("refuses an access word it does not know", async () => {
		expect(await codeOf(() => request({ doctype: "Contact", access: ["publish"] }))).toBe("invalid_params");
	});

	it("refuses a getAccess with no doctype", async () => {
		expect(await codeOf(() => getAccess({}))).toBe("invalid_params");
	});
});

describe("what travels back to the frame", () => {
	/**
	 * `createResource` answers with its reactive `data`, and `postMessage` cannot
	 * clone a Vue proxy. A browser found this before a test did.
	 */
	it("is a plain object a port can carry", async () => {
		stored = { ...NONE, read: "allowed" };

		const grant = await getAccess({ doctype: "Contact" });

		expect(() => structuredClone(grant)).not.toThrow();
	});

	it("holds every field, whatever the server left out", async () => {
		stored = {};

		expect(await getAccess({ doctype: "Contact" })).toEqual({
			doctype: "Contact",
			read: "not asked",
			write: "not asked",
			delete: "not asked",
		});
	});
});

describe("getAccess", () => {
	it("asks the record and opens no dialog", async () => {
		await getAccess({ doctype: "Contact" });

		expect(pendingPrompt.value).toBeNull();
		expect(urls()).toEqual(["builder.extensions.data.get_extension_grant"]);
	});

	it("names the calling extension, never one the frame sent", async () => {
		await getAccess({ doctype: "Contact", extension: "acme/other" }, record());

		expect(lastCall("get_extension_grant")?.params.extension).toBe("acme/crm");
	});
});

describe("when no dialog opens", () => {
	it("returns the grant when it already covers the request", async () => {
		stored = { ...NONE, read: "allowed" };

		const grant = await request({ doctype: "Contact", access: ["read"] });

		expect(pendingPrompt.value).toBeNull();
		expect(grant.read).toBe("allowed");
		expect(urls()).toEqual(["builder.extensions.data.get_extension_grant"]);
	});

	it("returns the grant when the user denied that access before", async () => {
		stored = { ...NONE, read: "denied" };

		await request({ doctype: "Contact", access: ["read"] });

		expect(pendingPrompt.value).toBeNull();
		expect(urls()).toEqual(["builder.extensions.data.get_extension_grant"]);
	});
});

describe("the prompt", () => {
	it("opens when the grant does not cover the request", async () => {
		const pending = request({ doctype: "Contact", access: ["read"] });
		await settled();

		expect(pendingPrompt.value?.subject).toBe("Contact");
		expect(pendingPrompt.value?.extension.label).toBe("CRM");

		answerPrompt(false);
		await pending;
	});

	it("asks only for what is missing", async () => {
		stored = { ...NONE, read: "allowed" };

		const pending = request({ doctype: "Contact", access: ["read", "write"] });
		await settled();

		expect(pendingPrompt.value?.access).toEqual(["write"]);

		answerPrompt(false);
		await pending;
	});

	it("asks about neither an allowed nor a denied access", async () => {
		stored = { ...NONE, read: "allowed", write: "denied" };

		const pending = request({ doctype: "Contact", access: ["read", "write", "delete"] });
		await settled();

		expect(pendingPrompt.value?.access).toEqual(["delete"]);

		answerPrompt(false);
		await pending;
	});

	it("marks a sensitive doctype", async () => {
		const pending = request({ doctype: "Builder User Extension", access: ["write"] });
		await settled();

		expect(pendingPrompt.value?.sensitive).toBe(true);

		answerPrompt(false);
		await pending;
	});

	it("leaves an ordinary doctype unmarked", async () => {
		const pending = request({ doctype: "Contact", access: ["read"] });
		await settled();

		expect(pendingPrompt.value?.sensitive).toBe(false);

		answerPrompt(false);
		await pending;
	});

	it("holds the installation record sensitive, because write to it rewrites capabilities", () => {
		expect(SENSITIVE_DOCTYPES.has("Builder User Extension")).toBe(true);
	});

	/** One user's drawer. Write access to it lets one extension read another's. */
	it("holds extension state sensitive", () => {
		expect(SENSITIVE_DOCTYPES.has("Builder Extension State")).toBe(true);
	});

	/** Frappe puts no gate on Web Form.client_script, so writing one is JS on a public page. */
	it("holds every doctype that carries code the site later runs", () => {
		for (const doctype of ["Server Script", "Client Script", "Web Form", "Print Format"]) {
			expect(SENSITIVE_DOCTYPES.has(doctype)).toBe(true);
		}
	});
});

describe("the answer", () => {
	it("records what the user allowed", async () => {
		const pending = request({ doctype: "Contact", access: ["read", "write"] });
		await settled();
		answerPrompt(true);
		await pending;

		expect(lastCall("record_extension_grant")?.params).toMatchObject({
			extension: "acme/crm",
			doctype: "Contact",
			access: ["read", "write"],
			denied: false,
		});
	});

	it("records a denial for the access it asked about", async () => {
		const pending = request({ doctype: "Contact", access: ["read"] });
		await settled();
		answerPrompt(false);
		await pending;

		expect(lastCall("record_extension_grant")?.params).toMatchObject({
			access: ["read"],
			denied: true,
		});
	});

	it("clears the prompt once it is answered", async () => {
		const pending = request({ doctype: "Contact", access: ["read"] });
		await settled();
		answerPrompt(true);
		await pending;

		expect(pendingPrompt.value).toBeNull();
	});
});

describe("one dialog at a time", () => {
	it("holds a second request until the first is answered", async () => {
		const first = request({ doctype: "Contact", access: ["read"] });
		await settled();
		const second = request({ doctype: "Lead", access: ["read"] }, record("acme/leads"));
		await settled();

		expect(pendingPrompt.value?.subject).toBe("Contact");

		answerPrompt(true);
		await first;
		await settled();

		expect(pendingPrompt.value?.subject).toBe("Lead");

		answerPrompt(true);
		await second;
	});
});

/**
 * Each test uses an extension of its own. `grants.ts` hooks teardown once per
 * extension, so a name another test already prompted for is hooked already and
 * this mock would never hear about it.
 */
describe("teardown", () => {
	it("denies a standing prompt when the extension goes away", async () => {
		const pending = request({ doctype: "Contact", access: ["read"] }, record("acme/gone"));
		await settled();

		expect(teardowns.has("acme/gone")).toBe(true);
		teardowns.get("acme/gone")?.();
		await pending;

		expect(pendingPrompt.value).toBeNull();
		expect(lastCall("record_extension_grant")?.params.denied).toBe(true);
	});

	it("leaves another extension's prompt standing", async () => {
		const pending = request({ doctype: "Contact", access: ["read"] }, record("acme/stays"));
		await settled();

		teardowns.get("acme/gone")?.();

		expect(pendingPrompt.value?.subject).toBe("Contact");

		answerPrompt(false);
		await pending;
	});
});
