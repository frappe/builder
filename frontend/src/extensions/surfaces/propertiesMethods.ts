/**
 * Tier B. A section in the right panel, from a list of controls that the
 * extension sends as data. `controlSchema.ts` shows each control with Builder
 * components. So the section looks the same as the built-in sections.
 *
 * The section header shows `label`, not the registry name. The host makes each
 * name as `extension:name`, and the user must not see that.
 *
 * No method here needs a permission. A section with no bound control writes
 * nothing. So the permission belongs to the controls. `readControls` checks it
 * on both ways into that list.
 */

import { propertySections, type PropertySection } from "@/components/BlockPropertySections";
import { editorContext } from "../context/editorContext";
import { assertRule, matches, type ShowWhenRule } from "../context/showWhen";
import type { MethodTable } from "../bridge/permissions";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";
import { readControls, toBlockProperty, type Control } from "./controlSchema";
import { fields, flag, optionalText, text } from "../bridge/params";
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
	// setControls changes into this patch. So both ways use the same reader
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
 * A new full list is a patch of one field. So it uses the merge and the second
 * registration that all surfaces share.
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
