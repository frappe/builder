import { describe, expect, it } from "vitest";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";
import { createRegistry, type RegistryEntry } from "@/utils/createRegistry";
import { fields, optionalText, text } from "../../bridge/params";
import { createSurfaceItems } from "../surfaceItems";

type Registration = { name: string; before?: string; after?: string };

const extension = (name: string) => ({ name }) as InstalledExtension;

const createSurface = () => {
	const registry = createRegistry<RegistryEntry>();
	registry.registerBuiltIn({ name: "publish" });
	const surface = createSurfaceItems<Registration, RegistryEntry>({
		kind: "test item",
		registry,
		readRegistration: (params) => {
			const sent = fields(params);
			return {
				name: text(sent.name, "name"),
				before: optionalText(sent.before, "before"),
				after: optionalText(sent.after, "after"),
			};
		},
		mergeRegistration: (current) => current,
		toRegistryItem: (key, { registration }) => ({ ...registration, name: key }),
	});
	const names = () => registry.all.value.map((item) => item.name);
	return { surface, names };
};

describe("createSurfaceItems anchors", () => {
	it("resolves a short name to a sibling of the same extension", () => {
		const { surface, names } = createSurface();
		const tools = extension("tools");
		surface.register({ name: "save" }, tools);
		surface.register({ name: "undo", before: "save" }, tools);

		expect(names()).toEqual(["publish", "tools:undo", "tools:save"]);
	});

	it("keeps a built-in name as the anchor", () => {
		const { surface, names } = createSurface();
		surface.register({ name: "save", before: "publish" }, extension("tools"));

		expect(names()).toEqual(["tools:save", "publish"]);
	});

	it("accepts the full key of another extension", () => {
		const { surface, names } = createSurface();
		surface.register({ name: "save" }, extension("tools"));
		surface.register({ name: "share", after: "tools:save" }, extension("other"));
		surface.register({ name: "last" }, extension("tools"));

		expect(names()).toEqual(["publish", "tools:save", "other:share", "tools:last"]);
	});

	it("does not resolve a short name to a button of another extension", () => {
		const { surface, names } = createSurface();
		surface.register({ name: "save" }, extension("tools"));
		surface.register({ name: "share", before: "save" }, extension("other"));

		expect(names()).toEqual(["other:share", "publish", "tools:save"]);
	});
});
