<template>
	<div class="divide-y divide-outline-gray-1 overflow-hidden rounded-lg border border-outline-gray-1">
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
					turning that capability off shows what it leaves behind.
				-->
				<div v-for="grant in doctypeGrantsUnder(group)" :key="grant.document_type" class="py-3">
					<div class="flex items-center justify-between gap-2">
						<p class="min-w-0 truncate text-xs text-ink-gray-8">{{ grant.document_type }}</p>
						<Select
							size="sm"
							class="w-28 shrink-0"
							:model-value="grant.denied ? 'denied' : 'allowed'"
							:options="grantOptions(grant)"
							@update:model-value="(answer: unknown) => answerGrant(grant, answer)" />
					</div>

					<p v-if="grant.denied" class="pt-1 text-xs text-ink-gray-5">It stopped asking about this.</p>
					<div v-else class="flex flex-col gap-2 pt-2">
						<Switch
							v-for="action in GRANT_ACTIONS"
							:key="action"
							size="sm"
							:model-value="Boolean(grant[`can_${action}`])"
							@update:model-value="(allow: boolean) => setAction(grant, action, allow)">
							<template #label>
								<span class="text-xs capitalize text-ink-gray-7">{{ action }}</span>
							</template>
						</Switch>
					</div>
				</div>
			</div>
		</section>
	</div>
</template>

<script setup lang="ts">
import { setExtensionGrant, type ExtensionGrant } from "@/data/extensions";
import {
	capabilityDetails,
	groupCapabilities,
	isSensitive,
	SITE_DATA_CLASS,
	type CapabilityGroup,
} from "@/extensions/capabilityClasses";
import { confirm } from "@/utils/helpers";
import type { Capability } from "frappe-builder-extension-sdk/types";
import { Select, Switch, toast } from "frappe-ui";
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

const GRANT_ACTIONS = ["read", "write", "delete"] as const;
type GrantAction = (typeof GRANT_ACTIONS)[number];

const accessOf = (grant: ExtensionGrant) => GRANT_ACTIONS.filter((action) => grant[`can_${action}`]);

/**
 * A denial records no access, so nothing stands to allow again. Asking again is
 * the way back: the extension asks, and the answer is a fresh one.
 */
const grantOptions = (grant: ExtensionGrant) => [
	...(grant.denied ? [] : [{ label: "Allowed", value: "allowed" }]),
	{ label: "Denied", value: "denied" },
	{ label: "Ask again", value: "forgotten" },
];

/** Turning the last action off allows nothing, so the answer goes and it asks again. */
const setAction = (grant: ExtensionGrant, action: GrantAction, allow: boolean) => {
	const access = allow
		? [...accessOf(grant), action]
		: accessOf(grant).filter((granted) => granted !== action);
	return writeGrant(grant, access);
};

/** "allowed" is the standing answer, so choosing it again writes nothing. */
const answerGrant = (grant: ExtensionGrant, answer: unknown) => {
	if (answer === "denied") return writeGrant(grant, [], true);
	if (answer === "forgotten") return writeGrant(grant, []);
};

const writeGrant = async (grant: ExtensionGrant, access: GrantAction[], denied = false) => {
	try {
		emit("doctypeGrants", await setExtensionGrant(props.extension, grant.document_type, access, denied));
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
