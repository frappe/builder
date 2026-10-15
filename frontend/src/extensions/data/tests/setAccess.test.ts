import { beforeEach, describe, expect, it, vi } from "vitest";
import { schemaMethods } from "../schemaMethods";

const { confirmSchema, invoke } = vi.hoisted(() => ({ confirmSchema: vi.fn(), invoke: vi.fn() }));
vi.mock("../confirmations", () => ({ confirmSchema }));
vi.mock("../documentMethods", () => ({ invoke }));

const extension = { name: "acme/cms", label: "CMS", entryUrl: "/main.js", permissions: [] };
const setAccess = () =>
	schemaMethods["schema.setAccess"].run({ doctype: "CMS Post", roles: ["Editor"] }, extension as never);
const request = { extension: "acme/cms", doctype: "CMS Post", roles: ["Editor"] };

describe("schema.setAccess", () => {
	beforeEach(() => {
		vi.resetAllMocks();
		confirmSchema.mockResolvedValue(true);
	});

	it("asks with the change from the server, and sends back that approved change", async () => {
		const access = { added: ["Editor"], removed: ["Blogger"] };
		invoke.mockResolvedValue(access);
		await setAccess();
		expect(invoke).toHaveBeenCalledWith("builder.extensions.schema.get_access_change", request);
		expect(confirmSchema).toHaveBeenCalledWith(extension, "CMS Post", "change access", { access });
		expect(invoke).toHaveBeenCalledWith("builder.extensions.schema.set_doctype_access", {
			...request,
			access,
		});
	});

	it("asks nothing when nothing changes", async () => {
		invoke.mockResolvedValue({ added: [], removed: [] });
		await setAccess();
		expect(confirmSchema).not.toHaveBeenCalled();
	});

	it("writes nothing when the user denies", async () => {
		invoke.mockResolvedValue({ added: ["Editor"], removed: [] });
		confirmSchema.mockResolvedValue(false);
		await expect(setAccess()).rejects.toMatchObject({ code: "refused" });
		expect(invoke).not.toHaveBeenCalledWith(
			"builder.extensions.schema.set_doctype_access",
			expect.anything(),
		);
	});
});
