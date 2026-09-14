import { CAPABILITIES, type Capability } from "frappe-builder-extension-sdk/types";
import { describe, expect, it } from "vitest";
import {
	capabilityDetails,
	groupCapabilities,
	isSensitive,
	SHARED_STATE_CLASS,
	SITE_DATA_CLASS,
} from "../capabilityClasses";

describe("capabilityDetails", () => {
	it("names every capability the bridge gates by", () => {
		// A capability added without wording would reach the panel as a bare key.
		expect(Object.keys(capabilityDetails).sort()).toEqual([...CAPABILITIES].sort());
	});

	it("gives every sensitive capability a reason to read", () => {
		const sensitive = CAPABILITIES.filter(isSensitive);

		expect(sensitive).toEqual(["token.write", "data.access", "schema.write"]);
		sensitive.forEach((capability) => expect(capabilityDetails[capability].warning).toBeTruthy());
	});
});

describe("groupCapabilities", () => {
	it("leaves out a class the extension never asked for", () => {
		const groups = groupCapabilities(["context.read", "block.read"]);

		expect(groups.map((group) => group.name)).toEqual(["Editor read"]);
		expect(groups[0].capabilities).toEqual(["context.read", "block.read"]);
	});

	it("puts the widest reach last, whatever order the manifest used", () => {
		const asked: Capability[] = ["schema.write", "block.update", "context.read"];

		expect(groupCapabilities(asked).map((group) => group.name)).toEqual([
			"Editor read",
			"Editor write",
			SHARED_STATE_CLASS,
		]);
	});

	it("marks the classes that reach past this session sensitive", () => {
		const groups = groupCapabilities([...CAPABILITIES]);

		expect(groups.filter((group) => group.sensitive).map((group) => group.name)).toEqual([
			SITE_DATA_CLASS,
			SHARED_STATE_CLASS,
		]);
	});

	it("answers with nothing when an extension asked for nothing", () => {
		expect(groupCapabilities([])).toEqual([]);
	});
});
