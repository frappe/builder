<template>
	<FrappePagePane v-slot="{ site, session }">
		<div class="flex flex-col gap-3">
			<p v-if="site.primary_domain" class="text-p-sm text-ink-gray-6">
				{{ __("The live site is served at") }}
				<span class="font-medium text-ink-gray-8">{{ site.primary_domain }}</span>
				.
				<button
					v-if="site.can_manage"
					type="button"
					class="font-medium text-ink-gray-8 underline underline-offset-2 hover:text-ink-gray-9"
					@click="useSubdomain">
					{{ __("Use the subdomain again") }}
				</button>
			</p>

			<template v-if="site.can_manage">
				<div v-if="!site.domains?.length" class="text-p-sm text-ink-gray-5">
					{{ __("No custom domains added yet.") }}
				</div>
				<div v-else class="mb-2 flex flex-col gap-2">
					<div
						v-for="d in site.domains"
						:key="d.domain"
						data-domain
						class="flex flex-col gap-2 rounded-5 border border-outline-gray-1 px-3 py-2.5">
						<div class="flex items-center gap-2">
							<div class="flex min-w-0 flex-1 items-center gap-2">
								<p class="text-p-sm-medium truncate leading-6 text-ink-gray-9">{{ d.domain }}</p>
								<Badge v-if="d.is_primary" size="sm" theme="green" :label="__('Primary')" />
								<Badge
									v-else-if="d.status === 'Pending'"
									size="sm"
									theme="amber"
									:label="__('Waiting for DNS')" />
							</div>
							<Button
								v-if="d.status === 'Pending'"
								variant="subtle"
								:label="__('Verify')"
								:loading="verifying === d.domain"
								@click="verify(d)" />
							<Dropdown :options="domainActions(d)" align="end">
								<Button
									variant="ghost"
									icon="lucide-more-horizontal"
									:aria-label="__('More for {0}', [d.domain])" />
							</Dropdown>
						</div>
						<template v-if="d.status === 'Pending'">
							<p class="text-p-xs text-ink-gray-5">
								{{
									__(
										"Add these records at your DNS provider, then press Verify. DNS changes can take up to an hour.",
									)
								}}
								<template v-if="session.dev_mode">
									{{ __("Dev mode: domains ending in .localhost verify without DNS.") }}
								</template>
							</p>
							<div class="overflow-hidden rounded-4 bg-surface-gray-1">
								<template v-for="(rec, i) in d.records" :key="rec.type">
									<div v-if="i > 1" class="flex items-center gap-3 px-3">
										<div class="h-px flex-1 bg-outline-gray-2"></div>
										<span class="text-p-xs text-ink-gray-4">{{ __("or") }}</span>
										<div class="h-px flex-1 bg-outline-gray-2"></div>
									</div>
									<div
										class="flex items-center gap-2 px-3 py-2.5"
										:class="{ 'border-b border-outline-gray-2': i === 0 }"
										data-dns-record>
										<div class="min-w-0 flex-1">
											<div class="flex flex-wrap items-baseline gap-x-1.5">
												<span class="text-p-sm-semibold leading-6 text-ink-gray-8">
													{{ __("{0} record", [rec.type]) }}
												</span>
												<span class="min-w-0 break-all font-mono text-p-xs">
													<span class="text-ink-gray-5">{{ rec.name }}</span>
													<span class="px-1 text-ink-gray-4">→</span>
													<span class="text-ink-gray-9">{{ rec.value }}</span>
												</span>
											</div>
											<p class="text-p-xs text-ink-gray-5">{{ recordHints[rec.purpose] }}</p>
										</div>
										<button
											type="button"
											:aria-label="__('Copy {0}', [rec.value])"
											:title="__('Copy value')"
											@click="copyText(rec.value)"
											class="shrink-0 text-ink-gray-4 transition-colors hover:text-ink-gray-7">
											<span class="lucide-copy h-3.5 w-3.5" aria-hidden="true" />
										</button>
									</div>
								</template>
							</div>
						</template>
					</div>
				</div>

				<form @submit.prevent="add" class="flex flex-col gap-3">
					<FormControl
						:label="__('Enter your domain')"
						:placeholder="__('e.g. www.yourdomain.com')"
						v-model="newDomain"
						autocomplete="off"
						autocapitalize="off"
						spellcheck="false" />
					<ErrorMessage v-if="addError" :message="addError" />
					<div class="flex gap-2">
						<Button
							type="submit"
							:disabled="submitting || !newDomain.trim()"
							variant="subtle"
							:loading="submitting">
							{{ __("Add Domain") }}
						</Button>
					</div>
				</form>
			</template>
			<p v-else class="text-p-sm text-ink-gray-5">
				{{ __("Owners and admins can add custom domains to this site.") }}
			</p>
		</div>
	</FrappePagePane>
</template>
<script setup lang="ts">
// frappe.page's Domains pane: custom domains are kept on the app host's control site, which proves each one
// with a TXT record and then points it at this site.
import FrappePagePane from "@/components/Settings/FrappePagePane.vue";
import { errorText, useFrappePageSite, type DNSRecord, type SiteDomain } from "@/data/frappePageSite";
import { __ } from "@/translation";
import { confirm } from "@/utils/helpers";
import { Badge, Dropdown, ErrorMessage, FormControl, toast } from "frappe-ui";
import { ref, watch } from "vue";

const { change } = useFrappePageSite();

const recordHints: Record<DNSRecord["purpose"], string> = {
	verify: __("Proves you own the domain"),
	subdomain: __("For a subdomain, like www.example.com"),
	apex: __("For a root domain, like example.com"),
};

const newDomain = ref("");
const submitting = ref(false);
const addError = ref("");
const verifying = ref("");

watch(newDomain, () => (addError.value = ""));

const add = async () => {
	const domain = newDomain.value
		.trim()
		.replace(/(^\w+:|^)\/\//, "")
		.split("/")[0]
		.toLowerCase();
	if (!domain) return;
	submitting.value = true;
	try {
		await change<SiteDomain>(
			"add_domain",
			{ domain },
			{
				loading: __("Adding {0}…", [domain]),
				success: (d) => __("{0} was added. Add its DNS records, then press Verify.", [d.domain]),
			},
			{ throws: true },
		);
		newDomain.value = "";
	} catch (error) {
		addError.value = errorText(error);
	} finally {
		submitting.value = false;
	}
};

const verify = async (d: SiteDomain) => {
	verifying.value = d.domain;
	await change(
		"verify_domain",
		{ domain: d.domain },
		{ loading: __("Checking DNS for {0}…", [d.domain]), success: __("{0} is verified", [d.domain]) },
	);
	verifying.value = "";
};

const useSubdomain = () =>
	change(
		"set_primary_domain",
		{ domain: "" },
		{ loading: __("Updating the primary domain…"), success: __("The site is served on its subdomain again") },
	);

const remove = async (d: SiteDomain) => {
	if (!(await confirm(__("The site stops answering on {0}.", [d.domain]), __("Remove {0}?", [d.domain]))))
		return;
	change(
		"remove_domain",
		{ domain: d.domain },
		{ loading: __("Removing {0}…", [d.domain]), success: __("{0} removed", [d.domain]) },
	);
};

const domainActions = (d: SiteDomain) => [
	{
		label: __("Set as Primary"),
		icon: "lucide-star",
		condition: () => d.status === "Active" && !d.is_primary,
		onClick: () =>
			change(
				"set_primary_domain",
				{ domain: d.domain },
				{ loading: __("Updating the primary domain…"), success: __("{0} set as primary", [d.domain]) },
			),
	},
	{
		label: __("Use Subdomain Instead"),
		icon: "lucide-undo-2",
		condition: () => Boolean(d.is_primary),
		onClick: useSubdomain,
	},
	{ label: __("Remove Domain"), icon: "lucide-trash", onClick: () => remove(d) },
];

const copyText = async (text: string) => {
	try {
		await navigator.clipboard.writeText(text);
		toast.success(__("Copied to clipboard"));
	} catch {
		toast.error(__("Failed to copy"));
	}
};
</script>
