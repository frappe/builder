import { beforeEach, describe, expect, it, vi } from "vitest";
import { schemaMethods } from "../schemaMethods";

const { confirmSchema, invoke } = vi.hoisted(() => ({ confirmSchema: vi.fn(), invoke: vi.fn() }));
vi.mock("../confirmations", () => ({ confirmSchema }));
vi.mock("../documentMethods", () => ({ invoke }));

const extension = { name: "acme/cms", label: "CMS", entryUrl: "/main.js", permissions: [] };
const setAccess = (roles: string[]) =>
	schemaMethods["schema.setAccess"].run({ doctype: "CMS Post", roles }, extension as never);

describe("schema.setAccess", () => {
	beforeEach(() => {
		vi.resetAllMocks();
		invoke.mockResolvedValue({ roles: ["System Manager", "Website Manager", "Blogger"] });
		confirmSchema.mockResolvedValue(true);
	});

	it("asks with only the roles that gain or lose access", async () => {
		await setAccess(["Editor"]);
		expect(confirmSchema).toHaveBeenCalledWith(extension, "CMS Post", "change access", {
			access: { added: ["Editor"], removed: ["Blogger"] },
		});
	});

	it("asks nothing when the roles stay the same", async () => {
		await setAccess(["Blogger"]);
		expect(confirmSchema).not.toHaveBeenCalled();
		expect(invoke).not.toHaveBeenCalledWith("builder.extensions.schema.set_doctype_access", expect.anything());
	});
});
