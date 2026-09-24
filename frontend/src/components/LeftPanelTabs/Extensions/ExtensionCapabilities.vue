<template>
	<div class="divide-y divide-outline-gray-1 overflow-hidden rounded-6 border border-outline-gray-1">
		<section v-for="group in groups" :key="group.name" class="divide-y divide-outline-gray-1">
			<header class="bg-surface-gray-1 px-3 py-2">
				<p class="text-xs font-medium" :class="group.sensitive ? 'text-ink-red-6' : 'text-ink-gray-8'">
					{{ group.name }}
				</p>
				<p class="pt-0.5 text-xs text-ink-gray-5">{{ group.summary }}</p>
			</header>

			<div class="divide-y divide-outline-gray-1 px-3">
				<div v-for="capability in group.capabilities" :key="capability" class="py-3">
					<Switch
						size="sm"
						:description="capabilityDetails[capability].warning"
						:model-value="granted.includes(capability)"
						@update:model-value="(allow: boolean) => answer(capability, allow)">
						<template #label>
							<span class="text-xs">{{ capabilityDetails[capability].label }}</span>
						</template>
					</Switch>
				</div>

				<!--
					The doctypes answered for sit under the capability they elaborate, so
					turning that capability off shows what it leaves behind. No divider
					comes before them, because they belong to the toggle above.
				-->
				<div
					v-if="doctypeGrantsUnder(group).length"
					class="flex flex-col gap-3"
					:class="group.capabilities.length ? '!border-t-0 pb-3' : 'py-3'">
					<!-- <p class="text-xs text-ink-gray-5">Doctypes</p> -->
					<div
						v-for="grant in doctypeGrantsUnder(group)"
						:key="grant.document_type"
						class="flex flex-col gap-1.5">
						<hr />
						<div class="flex items-center justify-between gap-2">
							<p class="min-w-0 truncate text-xs font-medium text-ink-gray-8">{{ grant.document_type }}</p>
							<Dropdown :options="answerAllOptions(grant)" placement="right">
								<template #trigger="{ open }">
									<Button
										variant="ghost"
										size="sm"
										icon="lucide-more-horizontal"
										:active="open"
										:aria-label="`Answer every access to ${grant.document_type}`" />
								</template>
							</Dropdown>
						</div>
						<div v-for="access in ACCESS" :key="access" class="flex items-center justify-between gap-2">
							<span class="text-xs capitalize text-ink-gray-6">{{ access }}</span>
							<TabButtons
								:options="ANSWER_BUTTONS"
								:model-value="answersOf(grant)[access]"
								@update:model-value="
									(answer: unknown) => setAnswers(grant, [access], answer as AccessAnswer)
								" />
						</div>
					</div>
				</div>
			</div>
		</section>
	</div>
</template>

<script setup lang="ts">
import { setExtensionGrant, type ExtensionGrant } from "@/data/extensions";
import { ACCESS, type Access, type AccessAnswer } from "@/extensions/data/grants";
import {
	capabilityDetails,
	groupCapabilities,
	isSensitive,
	SITE_DATA_CLASS,
	type CapabilityGroup,
} from "@/extensions/capabilityClasses";
import { confirm } from "@/utils/helpers";
import type { Capability } from "frappe-builder-extension-sdk/types";
import { Button, Dropdown, Switch, TabButtons, toast } from "frappe-ui";
import { computed } from "vue";

const props = defineProps<{
	extension: string;
	label: string;
	requested: Capability[];
	granted: Capability[];
	doctypeGrants: ExtensionGrant[];
}>();

const emit = defineEmits<{
	"update:granted": [capabilities: Capability[]];
	doctypeGrants: [doctypeGrants: ExtensionGrant[]];
}>();

/** Only what this extension asked for. A capability it never asked for is not a choice. */
const groups = computed(() =>
	groupCapabilities(props.requested, props.doctypeGrants.length ? [SITE_DATA_CLASS] : []),
);

const doctypeGrantsUnder = (group: CapabilityGroup) =>
	group.name === SITE_DATA_CLASS ? props.doctypeGrants : [];

/** Icon only: the label names each segment for a screen reader and a tooltip. */
const ANSWER_BUTTONS = [
	{ label: "Allowed", value: "allowed", icon: "lucide-check" },
	{ label: "Denied", value: "denied", icon: "lucide-x" },
	{ label: "Not asked", value: "not asked", icon: "lucide-minus" },
];

const answersOf = (grant: ExtensionGrant): Record<Access, AccessAnswer> => ({
	read: grant.read_access,
	write: grant.write_access,
	delete: grant.delete_access,
});

const answerAllOptions = (grant: ExtensionGrant) => [
	{ label: "Allow all", icon: "lucide-check", onClick: () => setAnswers(grant, ACCESS, "allowed") },
	{ label: "Deny all", icon: "lucide-x", onClick: () => setAnswers(grant, ACCESS, "denied") },
	{
		label: "Set all to not asked",
		icon: "lucide-minus",
		onClick: () => setAnswers(grant, ACCESS, "not asked"),
	},
];

/** The server takes the three answers whole, so the ones not changed travel with the change. */
const setAnswers = async (grant: ExtensionGrant, changed: readonly Access[], answer: AccessAnswer) => {
	const answers = answersOf(grant);
	changed.forEach((access) => (answers[access] = answer));
	try {
		emit("doctypeGrants", await setExtensionGrant(props.extension, grant.document_type, answers));
	} catch (thrown) {
		toast.error((thrown as Error).message);
	}
};

/**
 * Turning one off asks nothing: a narrower grant can break the extension and
 * nothing else. Turning a sensitive one on reaches the site's data or every
 * published page, so that direction carries the warning.
 *
 * The parent decides where the list goes: an installation writes it, and the
 * install dialog holds it until the user installs.
 */
const answer = async (capability: Capability, allow: boolean) => {
	if (allow && isSensitive(capability) && !(await confirmSensitive(capability))) return;

	emit(
		"update:granted",
		allow ? [...props.granted, capability] : props.granted.filter((granted) => granted !== capability),
	);
};

const confirmSensitive = (capability: Capability) =>
	confirm(
		`${capabilityDetails[capability].warning} Allow ${props.label} to ${capabilityDetails[
			capability
		].label.toLowerCase()}?`,
		"This reaches the whole site",
	);
</script>
