<template>
	<div class="flex flex-col gap-3">
		<!-- Domain list -->
		<div v-if="loading && !domains.length" class="text-p-sm text-ink-gray-5">
			{{ __("Loading domains…") }}
		</div>
		<div v-else-if="!domains.length" class="text-p-sm text-ink-gray-5">
			{{ __("No custom domains added yet.") }}
		</div>
		<div v-else class="mb-2 flex flex-col gap-2">
			<div
				v-for="d in sortedDomains"
				:key="d.domain"
				class="flex flex-col gap-1 rounded-md border border-outline-gray-1 px-3 py-2.5">
				<div class="flex items-center gap-2">
					<div class="flex min-w-0 flex-1 items-center gap-2">
						<p class="text-p-sm-medium truncate leading-6 text-ink-gray-9">{{ d.domain }}</p>
						<Badge v-if="d.dns_type" size="sm" theme="gray" :label="d.dns_type" />
						<p v-if="d.redirect_to_primary" class="text-p-xs text-ink-gray-5">
							{{ __("Redirects to primary") }}
						</p>
						<Badge v-if="d.primary" size="sm" theme="green" :label="__('Primary')" />
						<Badge
							v-else-if="d.status !== 'Active'"
							:label="d.status"
							size="sm"
							:theme="statusTheme(d.status)" />
					</div>
					<Dropdown v-if="getDomainActions(d).length" :options="getDomainActions(d)" placement="right">
						<Button variant="ghost" icon="lucide-more-horizontal" />
					</Dropdown>
				</div>
				<p v-if="d.status === 'Broken'" class="text-p-xs text-ink-red-8">
					{{ brokenReason(d) }}
				</p>
			</div>
		</div>

		<!-- Add domain form -->
		<form @submit.prevent="handleAdd" class="flex flex-col gap-3">
			<FormControl
				:label="__('Enter your domain')"
				:placeholder="__('e.g. yourdomain.com')"
				v-model="newDomain"
				autocomplete="off" />

			<!-- DNS records -->
			<div class="overflow-hidden rounded bg-surface-gray-1">
				<template v-for="(rec, i) in dnsRecords" :key="rec.type">
					<div v-if="i > 0" class="flex items-center gap-3 px-3">
						<div class="bg-outline-gray-2 h-px flex-1"></div>
						<span class="text-p-xs text-ink-gray-4">{{ __("or") }}</span>
						<div class="bg-outline-gray-2 h-px flex-1"></div>
					</div>
					<div class="flex items-center gap-2 px-3 py-2.5">
						<div class="min-w-0 flex-1">
							<div class="flex items-baseline gap-1.5">
								<span class="text-p-sm-semibold leading-6 text-ink-gray-8">{{ __("{0} record", [rec.type]) }}</span>
								<span class="font-mono text-p-xs">
									<span :class="newDomain ? 'text-ink-gray-5' : 'text-ink-gray-3'">{{ rec.host }}</span>
									<span class="px-1 text-ink-gray-4">→</span>
									<span class="text-ink-gray-9">{{ rec.value }}</span>
								</span>
							</div>
							<p class="text-p-xs text-ink-gray-5">{{ rec.hint }}</p>
						</div>
						<button
							type="button"
							:disabled="!rec.copyValue"
							@click="copyToClipboard(rec.copyValue)"
							class="shrink-0 text-ink-gray-4 transition-colors hover:text-ink-gray-7 disabled:cursor-not-allowed disabled:opacity-40">
							<span class="lucide-copy h-3.5 w-3.5" aria-hidden="true" />
						</button>
					</div>
				</template>
			</div>
			<ErrorMessage v-if="addError" :message="addError" />
			<div class="flex gap-2">
				<Button type="submit" :disabled="submitting || !newDomain" variant="subtle" :loading="submitting">
					{{ __("Add Domain") }}
				</Button>
			</div>
		</form>
	</div>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import { useDomains } from "@/data/domains";
import { useIntervalFn } from "@vueuse/core";
import { Badge, Dropdown, ErrorMessage, FormControl, toast } from "frappe-ui";
import { computed, onActivated, onDeactivated, onMounted, ref, watch } from "vue";

const PENDING_STATUSES = ["Pending", "In Progress"];

const currentSite = window.location.hostname;
const {
	domains,
	serverIP,
	loading,
	fetchDomains,
	fetchServerIP,
	addDomain,
	removeDomain,
	retryDomain,
	setHostName,
	setRedirect,
	unsetRedirect,
} = useDomains();

const newDomain = ref("");
const submitting = ref(false);
const addError = ref("");

watch(newDomain, () => {
	addError.value = "";
});

const sortedDomains = computed(() =>
	[...domains.value].sort((a, b) => (b.primary ? 1 : 0) - (a.primary ? 1 : 0)),
);

const hasPendingDomains = computed(() => domains.value.some((d) => PENDING_STATUSES.includes(d.status)));

// Poll while domains are still provisioning; auto-stops on unmount.
const { pause: stopPolling, resume: startPolling } = useIntervalFn(
	() => {
		if (!loading.value) fetchDomains();
	},
	5000,
	{ immediate: false },
);

watch(hasPendingDomains, (val) => (val ? startPolling() : stopPolling()));

onDeactivated(stopPolling);
onActivated(() => {
	if (hasPendingDomains.value) startPolling();
});

onMounted(() => Promise.all([fetchDomains(), fetchServerIP()]));

const isSubdomain = computed(() => newDomain.value.split(".").length > 2);

const dnsHostLabel = computed(() => {
	const parts = newDomain.value.split(".");
	return parts.length <= 2 ? newDomain.value : parts[0];
});

const dnsRecords = computed(() => {
	const host = newDomain.value ? dnsHostLabel.value : "your-domain.com";
	const records = [];
	if (isSubdomain.value) {
		records.push({
			type: "CNAME",
			host,
			value: currentSite,
			copyValue: currentSite,
			recommended: true,
			hint: __("Automatically follows server IP changes. Best choice for subdomains."),
		});
	}
	records.push({
		type: "A",
		host: isSubdomain.value ? host : "@",
		value: serverIP.value ?? "loading…",
		copyValue: serverIP.value ?? "",
		recommended: !isSubdomain.value,
		hint: isSubdomain.value
			? __("Use this if your DNS provider doesn't support CNAME for subdomains.")
			: __("Points your root domain directly to the server. Use @ as the host name."),
	});
	return records;
});

function brokenReason(d: any): string {
	if (!d.dns_response) return __("Domain setup failed. Please retry or contact support.");
	try {
		const parsed = JSON.parse(d.dns_response);
		if (parsed.exc_message) return parsed.exc_message.replace(/<[^>]*>/g, "").trim();
		const cname = parsed.CNAME;
		const a = parsed.A;
		if (cname?.exists && !cname?.matched)
			return __("CNAME record points to wrong destination: {0}", [cname.answer?.trim() || __("unknown")]);
		if (a?.exists && !a?.matched) return __("A record points to wrong IP: {0}", [a.answer?.trim() || __("unknown")]);
		if (!cname?.exists && !a?.exists) return __("No DNS record found for this domain.");
		if (parsed.matched || parsed.valid)
			return __("DNS is verified but SSL certificate provisioning failed. Please retry.");
	} catch {
		// ignore parse errors
	}
	return __("Domain setup failed. Please retry or contact support.");
}

function statusTheme(status: string) {
	const themes: Record<string, "green" | "red" | "orange" | "blue"> = {
		Active: "green",
		Broken: "red",
		Pending: "orange",
		"In Progress": "blue",
	};
	return themes[status] ?? "gray";
}

async function copyToClipboard(text: string) {
	if (!text) return;
	try {
		await navigator.clipboard.writeText(text);
		toast.success(__("Copied to clipboard"));
	} catch {
		toast.error(__("Failed to copy"));
	}
}

async function handleAdd() {
	if (!newDomain.value) return;

	newDomain.value = newDomain.value
		.replace(/(^\w+:|^)\/\//, "")
		.split("/")[0]
		.toLowerCase();

	addError.value = "";
	submitting.value = true;
	const { ok, error } = await addDomain(newDomain.value);
	submitting.value = false;
	if (ok) {
		newDomain.value = "";
	} else if (error) {
		addError.value = error;
	}
}

function getDomainActions(d: any) {
	const actions: any[] = [];
	if (d.status === "Active" && !d.primary)
		actions.push({ label: __("Set as Primary"), icon: "lucide-star", onClick: () => setHostName(d.domain) });
	if (!d.primary && !d.redirect_to_primary && d.status === "Active")
		actions.push({
			label: __("Redirect to Primary"),
			icon: "lucide-corner-right-up",
			onClick: () => setRedirect(d.domain),
		});
	if (d.redirect_to_primary)
		actions.push({
			label: __("Disable Redirect"),
			icon: "lucide-slash",
			onClick: () => unsetRedirect(d.domain),
		});
	if (d.status === "Broken")
		actions.push({ label: __("Retry"), icon: "lucide-refresh-cw", onClick: () => retryDomain(d.domain) });
	if (!d.primary)
		actions.push({ label: __("Remove Domain"), icon: "lucide-trash", onClick: () => removeDomain(d.domain) });
	return actions;
}
</script>
