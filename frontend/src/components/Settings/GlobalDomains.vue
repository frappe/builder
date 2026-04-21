<template>
	<div class="flex flex-col gap-3">
		<!-- Domain list -->
		<div v-if="loading && !domains.length" class="text-p-sm text-ink-gray-5">Loading domains…</div>
		<div v-else-if="!domains.length" class="text-p-sm text-ink-gray-5">No custom domains added yet.</div>
		<div v-else class="mb-2 flex flex-col gap-2">
			<div
				v-for="d in domains"
				:key="d.domain"
				class="flex items-center gap-2 rounded-md border border-outline-gray-1 px-3 py-2.5">
				<div class="flex min-w-0 flex-1 items-center gap-2">
					<p class="truncate text-p-sm font-medium leading-6 text-ink-gray-9">{{ d.domain }}</p>
					<p v-if="d.redirect_to_primary" class="text-p-xs text-ink-gray-5">Redirects to primary</p>
					<Badge v-if="d.primary" size="sm" theme="green" label="Primary" />
					<Badge v-else :label="d.status" size="sm" :theme="statusTheme(d.status)" />
				</div>
				<Dropdown v-if="getDomainActions(d).length" :options="getDomainActions(d)" placement="right">
					<Button variant="ghost" icon="more-horizontal" />
				</Dropdown>
			</div>
		</div>

		<!-- Add domain form -->
		<form @submit.prevent="handleVerifyOrAdd" class="flex flex-col gap-3">
			<FormControl
				label="Add Domain"
				placeholder="e.g. yourdomain.com"
				v-model="newDomain"
				:readonly="dnsVerified === true"
				autocomplete="off" />

			<!-- DNS records -->
			<div class="overflow-hidden rounded bg-surface-gray-1">
				<template v-for="(rec, i) in dnsRecords" :key="rec.type">
					<div v-if="i > 0" class="flex items-center gap-3 px-3">
						<div class="bg-outline-gray-2 h-px flex-1"></div>
						<span class="text-p-xs text-ink-gray-4">or</span>
						<div class="bg-outline-gray-2 h-px flex-1"></div>
					</div>
					<div class="flex items-center gap-2 px-3 py-2.5">
						<div class="min-w-0 flex-1">
							<div class="flex items-baseline gap-1.5">
								<span class="text-p-sm font-semibold leading-6 text-ink-gray-8">{{ rec.type }} record</span>
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
							<FeatherIcon name="copy" class="h-3.5 w-3.5" />
						</button>
					</div>
				</template>
			</div>
			<div class="flex items-center gap-1.5 text-p-xs" :class="statusClass">
				<FeatherIcon :name="statusIcon" class="h-3.5 w-3.5 shrink-0" />
				<span v-if="dnsVerified === true">
					DNS verified. Click
					<strong>Add Domain</strong>
					to proceed.
				</span>
				<span v-else v-html="statusMessage"></span>
			</div>

			<ErrorMessage v-if="addDomainError" :message="addDomainError" />
			<div class="flex gap-2">
				<Button
					type="submit"
					:disabled="checkingDNS || addingDomain || !newDomain"
					:variant="dnsVerified ? 'solid' : 'subtle'"
					:loading="checkingDNS || addingDomain">
					{{ dnsVerified ? "Add Domain" : "Verify DNS" }}
				</Button>
				<Button v-if="dnsVerified !== null" variant="ghost" @click="resetForm">Reset</Button>
			</div>
		</form>
	</div>
</template>

<script setup lang="ts">
import { useDomains } from "@/data/domains";
import { Badge, Dropdown, ErrorMessage, FeatherIcon, FormControl } from "frappe-ui";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { toast } from "vue-sonner";

const PENDING_STATUSES = ["Pending", "In Progress"];

const currentSite = window.location.hostname;
const {
	domains,
	serverIP,
	loading,
	fetchDomains,
	fetchServerIP,
	checkDNS,
	addDomain,
	removeDomain,
	retryDomain,
	setHostName,
	setRedirect,
	unsetRedirect,
} = useDomains();

const newDomain = ref("");
const dnsVerified = ref<boolean | null>(null);
const dnsCheckError = ref("");
const addDomainError = ref("");
const checkingDNS = ref(false);
const addingDomain = ref(false);

let pollInterval: ReturnType<typeof setInterval> | null = null;

const hasPendingDomains = computed(() => domains.value.some((d) => PENDING_STATUSES.includes(d.status)));

watch(hasPendingDomains, (val) => {
	if (val && !pollInterval) {
		pollInterval = setInterval(() => {
			if (!loading.value) fetchDomains();
		}, 5000);
	} else if (!val && pollInterval) {
		clearInterval(pollInterval);
		pollInterval = null;
	}
});

onMounted(() => Promise.all([fetchDomains(), fetchServerIP()]));
onUnmounted(() => {
	if (pollInterval) clearInterval(pollInterval);
});

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
			hint: "Automatically follows server IP changes. Best choice for subdomains.",
		});
	}
	records.push({
		type: "A",
		host: isSubdomain.value ? host : "@",
		value: serverIP.value ?? "loading…",
		copyValue: serverIP.value ?? "",
		recommended: !isSubdomain.value,
		hint: isSubdomain.value
			? "Use this if your DNS provider doesn't support CNAME for subdomains."
			: "Points your root domain directly to the server. Use @ as the host name.",
	});
	return records;
});

const statusClass = computed(() => {
	if (dnsVerified.value === true) return "text-ink-green-3";
	if (dnsVerified.value === false && dnsCheckError.value) return "text-ink-red-4";
	if (dnsVerified.value === false) return "text-yellow-700";
	return "text-ink-gray-5";
});

const statusIcon = computed(() => {
	if (dnsVerified.value === true) return "check-circle";
	if (dnsVerified.value === false && dnsCheckError.value) return "alert-circle";
	if (dnsVerified.value === false) return "alert-triangle";
	return "info";
});

const statusMessage = computed(() => {
	if (dnsVerified.value === false && dnsCheckError.value) return dnsCheckError.value;
	if (dnsVerified.value === false)
		return "DNS record not matched. Double-check the values below and allow up to 48h for propagation.";
	return isSubdomain.value
		? "Choose one of the records below and set it at your DNS registrar, then click Verify DNS."
		: "Set the A record at your registrar, then click Verify DNS.";
});

function statusTheme(status: string) {
	return (
		({ Active: "green", Broken: "red", Pending: "orange", "In Progress": "blue" } as Record<string, string>)[
			status
		] ?? "gray"
	);
}

async function copyToClipboard(text: string) {
	if (!text) return;
	try {
		await navigator.clipboard.writeText(text);
		toast.success("Copied to clipboard");
	} catch {
		toast.error("Failed to copy");
	}
}

function resetForm() {
	newDomain.value = "";
	dnsVerified.value = null;
	dnsCheckError.value = "";
	addDomainError.value = "";
}

async function handleVerifyOrAdd() {
	addDomainError.value = "";
	if (!newDomain.value) return;

	newDomain.value = newDomain.value
		.replace(/(^\w+:|^)\/\//, "")
		.split("/")[0]
		.toLowerCase();

	if (dnsVerified.value) {
		addingDomain.value = true;
		const ok = await addDomain(newDomain.value);
		addingDomain.value = false;
		if (ok) resetForm();
	} else {
		checkingDNS.value = true;
		const { matched, error } = await checkDNS(newDomain.value);
		checkingDNS.value = false;
		dnsVerified.value = matched;
		dnsCheckError.value = error;
	}
}

function getDomainActions(d: any) {
	const actions: any[] = [];
	if (d.status === "Active" && !d.primary)
		actions.push({ label: "Set as Primary", icon: "star", onClick: () => setHostName(d.domain) });
	if (!d.primary && !d.redirect_to_primary && d.status === "Active")
		actions.push({
			label: "Redirect to Primary",
			icon: "corner-right-up",
			onClick: () => setRedirect(d.domain),
		});
	if (d.redirect_to_primary)
		actions.push({ label: "Disable Redirect", icon: "slash", onClick: () => unsetRedirect(d.domain) });
	if (d.status === "Broken")
		actions.push({ label: "Retry", icon: "refresh-cw", onClick: () => retryDomain(d.domain) });
	if (!d.primary)
		actions.push({ label: "Remove Domain", icon: "trash", onClick: () => removeDomain(d.domain) });
	return actions;
}
</script>
