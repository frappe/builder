<template>
	<div class="flex flex-col gap-3">
		<!-- Domain list -->
		<div v-if="loading && !domains.length" class="text-p-sm text-ink-gray-5">正在加载域名…</div>
		<div v-else-if="!domains.length" class="text-p-sm text-ink-gray-5">尚未添加自定义域名。</div>
		<div v-else class="mb-2 flex flex-col gap-2">
			<div
				v-for="d in sortedDomains"
				:key="d.domain"
				class="flex flex-col gap-1 rounded-md border border-outline-gray-1 px-3 py-2.5">
				<div class="flex items-center gap-2">
					<div class="flex min-w-0 flex-1 items-center gap-2">
						<p class="text-p-sm-medium truncate leading-6 text-ink-gray-9">{{ d.domain }}</p>
						<Badge v-if="d.dns_type" size="sm" theme="gray" :label="d.dns_type" />
						<p v-if="d.redirect_to_primary" class="text-p-xs text-ink-gray-5">重定向到主域名</p>
						<Badge v-if="d.primary" size="sm" theme="green" label="主域名" />
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
				label="输入您的域名"
				placeholder="例如 yourdomain.com"
				v-model="newDomain"
				autocomplete="off" />

			<!-- DNS records -->
			<div class="overflow-hidden rounded bg-surface-gray-1">
				<template v-for="(rec, i) in dnsRecords" :key="rec.type">
					<div v-if="i > 0" class="flex items-center gap-3 px-3">
						<div class="bg-outline-gray-2 h-px flex-1"></div>
						<span class="text-p-xs text-ink-gray-4">或</span>
						<div class="bg-outline-gray-2 h-px flex-1"></div>
					</div>
					<div class="flex items-center gap-2 px-3 py-2.5">
						<div class="min-w-0 flex-1">
							<div class="flex items-baseline gap-1.5">
								<span class="text-p-sm-semibold leading-6 text-ink-gray-8">{{ rec.type }} 记录</span>
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
					添加域名
				</Button>
			</div>
		</form>
	</div>
</template>

<script setup lang="ts">
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
			hint: "自动跟随服务器 IP 变化。子域名的最佳选择。",
		});
	}
	records.push({
		type: "A",
		host: isSubdomain.value ? host : "@",
		value: serverIP.value ?? "加载中…",
		copyValue: serverIP.value ?? "",
		recommended: !isSubdomain.value,
		hint: isSubdomain.value
			? "如果您的 DNS 服务商不支持子域名的 CNAME 记录，请使用此项。"
			: "将您的根域名直接指向服务器。使用 @ 作为主机名。",
	});
	return records;
});

function brokenReason(d: any): string {
	if (!d.dns_response) return "域名设置失败。请重试或联系技术支持。";
	try {
		const parsed = JSON.parse(d.dns_response);
		if (parsed.exc_message) return parsed.exc_message.replace(/<[^>]*>/g, "").trim();
		const cname = parsed.CNAME;
		const a = parsed.A;
		if (cname?.exists && !cname?.matched)
			return `CNAME 记录指向了错误的目标：${cname.answer?.trim() || "未知"}`;
		if (a?.exists && !a?.matched) return `A 记录指向了错误的 IP：${a.answer?.trim() || "未知"}`;
		if (!cname?.exists && !a?.exists) return "未找到该域名的 DNS 记录。";
		if (parsed.matched || parsed.valid)
			return "DNS 已验证，但 SSL 证书签发失败。请重试。";
	} catch {
		// ignore parse errors
	}
	return "域名设置失败。请重试或联系技术支持。";
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
		toast.success("已复制到剪贴板");
	} catch {
		toast.error("复制失败");
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
		actions.push({ label: "设为主域名", icon: "lucide-star", onClick: () => setHostName(d.domain) });
	if (!d.primary && !d.redirect_to_primary && d.status === "Active")
		actions.push({
			label: "重定向到主域名",
			icon: "lucide-corner-right-up",
			onClick: () => setRedirect(d.domain),
		});
	if (d.redirect_to_primary)
		actions.push({ label: "禁用重定向", icon: "lucide-slash", onClick: () => unsetRedirect(d.domain) });
	if (d.status === "Broken")
		actions.push({ label: "重试", icon: "lucide-refresh-cw", onClick: () => retryDomain(d.domain) });
	if (!d.primary)
		actions.push({ label: "移除域名", icon: "lucide-trash", onClick: () => removeDomain(d.domain) });
	return actions;
}
</script>
