/**
 * Tier B. A section in the right panel, built from a list of controls the
 * extension sends as data. `controlSchema.ts` renders each one with Builder's
 * own components, so the section cannot look foreign.
 *
 * The section header reads `label`, not the registry name, because the host
 * composes every name as `extension:name` and nobody wants that on screen.
 *
 * No method here needs a capability. A section with no bound control writes
 * nothing, so the grant belongs to the controls, and `readControls` checks it
 * on both doors into that list.
 */

import { propertySections, type PropertySection } from "@/components/BlockPropertySections";
import { editorContext } from "../editor/editorContext";
import { assertRule, matches, type ShowWhenRule } from "../editor/showWhen";
import type { MethodTable } from "../host/capabilities";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";
import { readControls, toBlockProperty, type Control } from "./controlSchema";
import { fields, flag, optionalText, text } from "../params";
import { createSurfaceItems, type SurfaceItem } from "./surfaceItems";

type Registration = {
	name: string;
	label: string;
	controls: Control[];
	before?: string;
	after?: string;
	showWhen?: ShowWhenRule;
	visible: boolean;
};

const readRegistration = (params: unknown, extension: InstalledExtension): Registration => {
	const sent = fields(params);
	assertRule(sent.showWhen as ShowWhenRule | undefined);

	const name = text(sent.name, "name");
	return {
		name,
		label: optionalText(sent.label, "label") ?? name,
		controls: readControls(sent.controls, extension),
		before: optionalText(sent.before, "before"),
		after: optionalText(sent.after, "after"),
		showWhen: sent.showWhen as ShowWhenRule | undefined,
		visible: true,
	};
};

const mergeRegistration = (
	current: Registration,
	patch: Record<string, unknown>,
	extension: InstalledExtension,
): Registration => ({
	...current,
	label: optionalText(patch.label, "label") ?? current.label,
	visible: flag(patch.visible, current.visible),
	// setControls reshapes itself into this patch, so both doors read the same way
	controls: "controls" in patch ? readControls(patch.controls, extension) : current.controls,
});

const toRegistryItem = (key: string, { extension, registration }: SurfaceItem<Registration>): PropertySection => ({
	name: key,
	label: registration.label,
	before: registration.before,
	after: registration.after,
	properties: registration.controls.map((control) =>
		toBlockProperty(control, extension, registration.label),
	),
	condition: () => matches(registration.showWhen, editorContext.value) && registration.visible,
});

const sections = createSurfaceItems<Registration, PropertySection>({
	kind: "property section",
	registry: propertySections,
	readRegistration,
	mergeRegistration,
	toRegistryItem,
});

/**
 * Replacing the whole list is a patch of one field, so it reuses the merge and
 * re-register path every surface shares.
 */
const setControls = (params: unknown, extension: InstalledExtension) => {
	const sent = fields(params);
	return sections.update({ name: sent.name, patch: { controls: sent.controls } }, extension);
};

export const propertyMethods: MethodTable = {
	"properties.registerSection": { needs: null, run: sections.register },
	"properties.unregisterSection": { needs: null, run: sections.unregister },
	"properties.update": { needs: null, run: sections.update },
	"properties.setControls": { needs: null, run: setControls },
};
