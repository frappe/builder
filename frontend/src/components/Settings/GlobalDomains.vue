<template>
	<div class="flex flex-col gap-3">
		<!-- Domain list -->
		<div v-if="loading" class="text-p-sm text-ink-gray-5">Loading domains…</div>
		<div v-else-if="!domains.length" class="text-p-sm text-ink-gray-5">No custom domains added yet.</div>
		<div v-else class="mb-2 flex flex-col gap-2">
			<div
				v-for="d in domains"
				:key="d.domain"
				class="flex items-center justify-between rounded-md border border-outline-gray-1 px-3 py-2">
				<div class="flex items-center gap-2">
					<span class="text-p-sm font-medium leading-7 text-ink-gray-9">{{ d.domain }}</span>
					<Badge v-if="d.primary" size="sm" theme="green" label="Primary" />
					<Badge v-else-if="d.redirect_to_primary" size="sm" theme="blue" label="Redirecting" />
				</div>
				<Dropdown v-if="!d.primary" :options="getDomainActions(d)" placement="right">
					<Button variant="ghost" icon="more-horizontal" />
				</Dropdown>
			</div>
		</div>

		<!-- Add domain form -->
		<form @submit.prevent="handleVerifyOrAdd" class="flex flex-col gap-3">
			<span class="text-sm text-ink-gray-5">
				To add a custom domain, you must already own it. If you don't have one, buy it and come back here.
			</span>
			<FormControl
				placeholder="www.example.com"
				v-model="newDomain"
				:readonly="dnsVerified === true"
				autocomplete="off" />

			<!-- DNS info card -->
			<div class="overflow-hidden rounded-md border border-outline-gray-1">
				<div
					class="flex items-center gap-2 border-b border-outline-gray-1 px-3 py-2 text-p-xs"
					:class="statusClass">
					<FeatherIcon :name="statusIcon" class="h-3.5 w-3.5 shrink-0" />
					<span v-if="dnsVerified === true">
						DNS verified. Click
						<strong>Add Domain</strong>
						to proceed.
					</span>
					<span v-else>{{ statusMessage }}</span>
				</div>

				<div class="space-y-1 p-3">
					<div
						v-for="rec in dnsRecords"
						:key="rec.type"
						class="flex items-center gap-2 rounded bg-surface-gray-1 px-2.5 py-1.5 font-mono text-p-xs">
						<span class="w-10 shrink-0 font-semibold text-ink-gray-7">{{ rec.type }}</span>
						<span :class="newDomain ? 'text-ink-gray-5' : 'text-ink-gray-3'">
							{{ newDomain ? dnsHostLabel : "your-domain.com" }}
						</span>
						<span class="text-ink-gray-4">→</span>
						<span class="flex-1 truncate text-ink-gray-9">{{ rec.value }}</span>
						<button
							type="button"
							:disabled="!rec.copyValue"
							@click="copyToClipboard(rec.copyValue)"
							class="text-ink-gray-4 transition-colors hover:text-ink-gray-7 disabled:cursor-not-allowed disabled:opacity-40">
							<FeatherIcon name="copy" class="h-3.5 w-3.5" />
						</button>
					</div>
				</div>
			</div>

			<ErrorMessage v-if="addDomainError" :message="addDomainError" />
			<div class="flex gap-2">
				<Button
					type="submit"
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
import { computed, onMounted, ref } from "vue";
import { toast } from "vue-sonner";

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

const dnsHostLabel = computed(() => {
	const parts = newDomain.value.split(".");
	return parts.length <= 2 ? newDomain.value : parts[0];
});

const statusClass = computed(() => {
	if (dnsVerified.value === true) return "text-ink-green-4 bg-green-50";
	if (dnsVerified.value === false && dnsCheckError.value) return "bg-red-50 text-ink-red-4";
	if (dnsVerified.value === false) return "bg-yellow-50 text-yellow-700";
	return "bg-surface-gray-1 text-ink-gray-5";
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
	return "Set one of these DNS records at your domain registrar, then click Verify DNS.";
});

const dnsRecords = computed(() => [
	{ type: "CNAME", value: currentSite, copyValue: currentSite },
	{ type: "A", value: serverIP.value ?? "loading…", copyValue: serverIP.value ?? "" },
]);

onMounted(() => Promise.all([fetchDomains(), fetchServerIP()]));

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
	if (!d.redirect_to_primary && d.status === "Active")
		actions.push({
			label: "Redirect to Primary",
			icon: "corner-right-up",
			onClick: () => setRedirect(d.domain),
		});
	if (d.redirect_to_primary)
		actions.push({ label: "Disable Redirect", icon: "slash", onClick: () => unsetRedirect(d.domain) });
	if (d.status === "Broken")
		actions.push({ label: "Retry", icon: "refresh-cw", onClick: () => retryDomain(d.domain) });
	actions.push({ label: "Remove Domain", icon: "trash", onClick: () => removeDomain(d.domain) });
	return actions;
}
</script>
