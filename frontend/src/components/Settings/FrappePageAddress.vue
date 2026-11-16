<template>
	<FrappePagePane v-slot="{ site, session }">
		<div class="flex flex-col gap-6">
			<div class="flex flex-col gap-3 text-base">
				<div class="flex">
					<span class="w-28 shrink-0 text-ink-gray-6">{{ __("Address") }}</span>
					<span class="font-medium text-ink-gray-8" data-site-address>
						{{ site.subdomain }}.{{ session.content_domain }}
					</span>
				</div>
				<div class="flex items-center">
					<span class="w-28 shrink-0 text-ink-gray-6">{{ __("Live site") }}</span>
					<a
						class="truncate font-medium text-ink-gray-8 hover:underline"
						target="_blank"
						:href="site.live_url">
						{{ site.live_url }}
					</a>
					<Button
						variant="ghost"
						size="sm"
						class="ml-1 shrink-0"
						icon="lucide-copy"
						:aria-label="__('Copy address')"
						:tooltip="__('Copy address')"
						@click="copyText(site.live_url)" />
				</div>
				<div class="flex">
					<span class="w-28 shrink-0 text-ink-gray-6">{{ __("Your role") }}</span>
					<span class="text-ink-gray-8">{{ site.role }}</span>
				</div>
			</div>

			<hr class="w-full border-outline-gray-2" />

			<div class="flex flex-col gap-4">
				<div class="flex flex-col gap-1.5">
					<span class="text-md-semibold text-ink-gray-9">{{ __("Rename") }}</span>
					<p class="text-p-sm text-ink-gray-6">
						{{
							__("The old address keeps redirecting for 90 days, and nobody else can take it in that time.")
						}}
					</p>
				</div>
				<p v-if="!site.can_manage" class="text-p-sm text-ink-gray-5">
					{{ __("Owners and admins can rename the site.") }}
				</p>
				<p v-else-if="site.next_rename_on" class="text-p-sm text-ink-gray-5">
					{{
						__("A site can be renamed once every 30 days. You can rename {0} again on {1}.", [
							site.subdomain,
							formatDate(site.next_rename_on),
						])
					}}
				</p>
				<form v-else class="flex flex-col gap-3" @submit.prevent="rename(site)">
					<div class="flex flex-col gap-1.5">
						<div class="flex items-end gap-2">
							<div class="w-64">
								<BuilderInput
									type="text"
									:label="__('New address')"
									:placeholder="site.subdomain"
									:hideClearButton="true"
									maxlength="30"
									autocapitalize="off"
									spellcheck="false"
									:modelValue="newName"
									@input="onInput" />
							</div>
							<span class="pb-1.5 text-base text-ink-gray-5">.{{ session.content_domain }}</span>
						</div>
						<p
							v-if="check.text"
							class="flex items-center gap-1 text-p-sm"
							:class="checkClasses[check.tone]"
							role="status"
							aria-live="polite">
							<span v-if="check.tone === 'ok'" class="lucide-check size-4" aria-hidden="true" />
							{{ check.text }}
						</p>
					</div>
					<div>
						<Button
							type="submit"
							variant="solid"
							:label="__('Rename')"
							:disabled="!available"
							:loading="renaming" />
					</div>
				</form>
			</div>
		</div>
	</FrappePagePane>
</template>
<script setup lang="ts">
// frappe.page's Address pane: the site's address on the content domain, renamed through the app host's
// control site. The editor's address, and the name of its session cookie, follow the address, so after a
// rename the app host signs the user in again at the new one.
import FrappePagePane from "@/components/Settings/FrappePagePane.vue";
import { useFrappePageSite, type SiteSummary } from "@/data/frappePageSite";
import { __ } from "@/translation";
import { controlCall, fp, openSiteURL } from "@/utils/frappePage";
import { confirm } from "@/utils/helpers";
import { useDebounceFn } from "@vueuse/core";
import { toast } from "frappe-ui";
import { reactive, ref } from "vue";

type Check = { subdomain: string; available: boolean; reason: string | null; url: string | null };

const { change } = useFrappePageSite();

const newName = ref("");
const available = ref("");
const renaming = ref(false);
const check = reactive({ text: "", tone: "" as "" | "ok" | "bad" });
const checkClasses = { "": "text-ink-gray-5", ok: "text-ink-green-6", bad: "text-ink-red-6" };
let ticket = 0;

const show = (text: string, tone: typeof check.tone = "") => Object.assign(check, { text, tone });

// the same cleaning as the address field of onboarding
const onInput = (value: string) => {
	const cleaned = value
		.toLowerCase()
		.replace(/\s+/g, "-")
		.replace(/[^a-z0-9-]/g, "");
	newName.value = cleaned;
	available.value = "";
	show(cleaned ? __("Checking…") : "");
	checkLater(cleaned);
};

const checkLater = useDebounceFn(async (value: string) => {
	const mine = ++ticket;
	if (!value) return;
	try {
		const result = await controlCall<Check>("frappe_page.api.check_subdomain", { subdomain: value });
		if (mine !== ticket || value !== newName.value) return;
		available.value = result.available ? result.subdomain : "";
		if (result.available) show(__("{0} is available", [hostOf(result.url)]), "ok");
		else show(result.reason || __("This address is not available."), "bad");
	} catch (error) {
		if (mine === ticket) show(error instanceof Error ? error.message : String(error), "bad");
	}
}, 300);

const rename = async (site: SiteSummary) => {
	const name = available.value;
	if (!name) return;
	const sure = await confirm(
		__("The old address redirects to the new one for 90 days. You can't rename the site again for 30 days."),
		__("Rename {0} to {1}?", [site.subdomain, name]),
	);
	if (!sure) return;
	renaming.value = true;
	const done = await change(
		"rename_subdomain",
		{ new_subdomain: name },
		{ loading: __("Renaming to {0}…", [name]), success: __("Renamed to {0}", [name]) },
		{ reload: false },
	);
	if (!done) {
		renaming.value = false;
		return;
	}
	const mount = renamedMount(name);
	await untilServed(mount);
	window.location.href = openSiteURL(
		name,
		mount + window.location.pathname.slice(fp.mount?.length) + window.location.search,
	);
};

/** The editor's address after a rename: the mount ends in the subdomain. */
const renamedMount = (name: string) => (fp.mount ?? "").replace(/[^/]+$/, name);

/**
 * Each web worker of the site keeps its config, which names the address, for up to a minute, and until it
 * reads it again it sends the new address back to the old one. Wait until the new address answers for
 * itself a few times in a row, so the sign-in there sticks.
 */
async function untilServed(mount: string) {
	const answers = () =>
		fp.appFetch!(`${mount}/api/method/frappe.ping`, { redirect: "manual", credentials: "omit" })
			.then((response) => response.status === 200)
			.catch(() => false);
	const id = toast.loading(__("Moving the editor to its new address…"));
	for (let tries = 0, streak = 0; tries < 60 && streak < 6; tries++) {
		streak = (await answers()) ? streak + 1 : 0;
		await new Promise((resolve) => setTimeout(resolve, streak ? 300 : 2000));
	}
	toast.dismiss(id);
}

const hostOf = (url: string | null) => {
	try {
		return new URL(url ?? "").host;
	} catch {
		return url ?? "";
	}
};

const formatDate = (value: string) => {
	const date = new Date(String(value).replace(" ", "T"));
	return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString(undefined, { dateStyle: "medium" });
};

const copyText = async (text: string) => {
	try {
		await navigator.clipboard.writeText(text);
		toast.success(__("Copied to clipboard"));
	} catch {
		toast.error(__("Failed to copy"));
	}
};
</script>
