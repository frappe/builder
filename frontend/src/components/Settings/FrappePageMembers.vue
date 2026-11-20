<template>
	<FrappePagePane v-slot="{ site, session }">
		<div class="flex h-full flex-col gap-5">
			<div class="flex items-center justify-between gap-2">
				<BuilderInput
					type="text"
					class="w-72"
					:placeholder="__('Search by name or email')"
					icon-left="lucide-search"
					:modelValue="searchQuery"
					@input="(val: string) => (searchQuery = val)" />
				<Button v-if="site.can_manage" variant="solid" icon-left="lucide-plus" @click="openInviteDialog">
					{{ __("Invite") }}
				</Button>
			</div>
			<p v-if="!site.can_manage" class="-mt-2 text-p-sm text-ink-gray-5">
				{{ __("Owners and admins can invite people and change their roles.") }}
			</p>

			<div v-if="devInvite" class="flex items-center gap-2 rounded-4 bg-surface-gray-1 px-3 py-2.5">
				<div class="min-w-0 flex-1">
					<p class="text-p-sm-medium leading-6 text-ink-gray-8">
						{{ __("Dev mode: invite link for {0}", [devInvite.email]) }}
					</p>
					<a
						class="block truncate font-mono text-p-xs text-ink-gray-6 hover:underline"
						data-dev-invite-url
						:href="devInvite.url"
						target="_blank">
						{{ devInvite.url }}
					</a>
				</div>
				<Button
					variant="ghost"
					icon="lucide-copy"
					:aria-label="__('Copy invite link')"
					:tooltip="__('Copy invite link')"
					@click="copyText(devInvite.url)" />
			</div>

			<div class="min-h-0 flex-1 overflow-y-auto">
				<div v-if="invites(site).length" class="mb-6 flex flex-col">
					<span class="sticky top-0 z-10 bg-surface-base pb-1 text-p-sm text-ink-gray-5">
						{{ __("Pending Invites ({0})", [invites(site).length]) }}
					</span>
					<div
						v-for="invite in invites(site)"
						:key="invite.email"
						class="flex items-center justify-between gap-2 border-b border-outline-gray-1 py-2 last:border-b-0">
						<div class="flex min-w-0 items-center gap-2">
							<Avatar shape="circle" :label="invite.email" size="lg" />
							<div class="flex min-w-0 flex-col">
								<span class="truncate text-p-sm text-ink-gray-8">{{ invite.email }}</span>
								<span class="truncate text-p-xs text-ink-gray-5">
									{{ __("Invited as {0}", [roleLabels[invite.role]]) }}
								</span>
							</div>
						</div>
						<Button
							variant="subtle"
							size="sm"
							icon="lucide-x"
							:title="__('Cancel invitation')"
							:aria-label="__('Cancel the invitation for {0}', [invite.email])"
							@click="cancelInvite(site, invite)" />
					</div>
				</div>

				<div class="flex flex-col">
					<span class="sticky top-0 z-10 bg-surface-base pb-1 text-p-sm text-ink-gray-5">
						{{ __("Members ({0})", [members(site).length]) }}
					</span>
					<div
						v-for="member in members(site)"
						:key="member.user"
						data-member
						class="flex items-center gap-2 border-b border-outline-gray-1 py-2 last:border-b-0">
						<Avatar shape="circle" :label="member.full_name || member.user" size="lg" />
						<div class="flex min-w-0 flex-col">
							<span class="truncate text-p-sm text-ink-gray-8">
								{{ member.full_name || member.user }}
								<Badge v-if="member.user === session.user" theme="gray" class="ml-1">
									{{ __("You") }}
								</Badge>
							</span>
							<span class="truncate text-p-xs text-ink-gray-5">{{ member.user }}</span>
						</div>
						<div v-if="canChange(site, session, member)" class="ml-auto shrink-0">
							<Dropdown :options="memberActions(site, member)" align="end">
								<!-- the role in the slot, not `label`, which Button would also make its aria-label -->
								<Button
									variant="ghost"
									icon-right="lucide-chevron-down"
									:aria-label="__('Role of {0}: {1}', [member.user, roleLabels[member.role]])">
									{{ roleLabels[member.role] }}
								</Button>
							</Dropdown>
						</div>
						<Badge v-else theme="gray" class="ml-auto shrink-0">{{ roleLabels[member.role] }}</Badge>
					</div>
					<div v-if="!members(site).length" class="py-6 text-center text-p-sm text-ink-gray-5">
						{{ __('No members match "{0}"', [searchQuery]) }}
					</div>
				</div>
			</div>
		</div>

		<Dialog
			v-model="showInviteDialog"
			:title="__('Invite Members')"
			:actions="[{ label: __('Send Invitation'), variant: 'solid', onClick: () => sendInvite(site) }]">
			<template #default>
				<div class="flex flex-col gap-4">
					<BuilderInput
						:ref="(el: unknown) => (inviteInputRef = el)"
						type="email"
						:label="__('Email')"
						placeholder="name@example.com"
						:hideClearButton="true"
						:modelValue="inviteEmail"
						@input="(val: string) => (inviteEmail = val)"
						@keydown.enter.prevent="sendInvite(site)" />
					<FormControl
						type="select"
						:label="__('Role')"
						:options="roleOptions"
						:description="__('Admins can manage members and domains. Editors can edit pages.')"
						:modelValue="inviteRole"
						@update:modelValue="(val: SiteRole) => (inviteRole = val)" />
					<ErrorMessage v-if="inviteError" :message="inviteError" />
				</div>
			</template>
		</Dialog>
	</FrappePagePane>
</template>
<script setup lang="ts">
// frappe.page's Members pane, in place of Builder's Users: who may edit this site is kept on the app host's
// control site, which invites people and mirrors each member's role to this site.
import FrappePagePane from "@/components/Settings/FrappePagePane.vue";
import {
	useFrappePageSite,
	type EditorSession,
	type SiteInvite,
	type SiteMember,
	type SiteRole,
	type SiteSummary,
} from "@/data/frappePageSite";
import { __ } from "@/translation";
import { confirm } from "@/utils/helpers";
import { Avatar, Badge, Dialog, Dropdown, ErrorMessage, FormControl, toast } from "frappe-ui";
import { nextTick, ref } from "vue";

const { change } = useFrappePageSite();

const roleLabels: Record<SiteRole, string> = { Owner: __("Owner"), Admin: __("Admin"), Editor: __("Editor") };
const roleOptions = [
	{ label: __("Editor"), value: "Editor" },
	{ label: __("Admin"), value: "Admin" },
];

const searchQuery = ref("");
const showInviteDialog = ref(false);
const inviteEmail = ref("");
const inviteRole = ref<SiteRole>("Editor");
const inviteError = ref("");
const inviteInputRef = ref<any>(null);
const devInvite = ref<{ email: string; url: string } | null>(null);

const matches = (...values: string[]) => {
	const query = searchQuery.value.toLowerCase().trim();
	return !query || values.some((value) => value?.toLowerCase().includes(query));
};

const members = (site: SiteSummary) =>
	site.members.members.filter((member) => matches(member.full_name, member.user));
const invites = (site: SiteSummary) => (site.members.invites ?? []).filter((invite) => matches(invite.email));

// the owner's role is fixed, and nobody changes their own
const canChange = (site: SiteSummary, session: EditorSession, member: SiteMember) =>
	site.can_manage && member.role !== "Owner" && member.user !== session.user;

const memberActions = (site: SiteSummary, member: SiteMember) => [
	{
		group: __("Role"),
		hideLabel: true,
		options: (["Admin", "Editor"] as const).map((role) => ({
			label: roleLabels[role],
			description: role === "Admin" ? __("Manages members and domains") : __("Edits pages"),
			icon: role === member.role ? "lucide-check" : "",
			onClick: () => setRole(member, role),
		})),
	},
	{
		group: __("Remove"),
		hideLabel: true,
		options: [
			{
				label: __("Remove from Site"),
				icon: "lucide-user-minus",
				theme: "red" as const,
				onClick: () => removeMember(site, member),
			},
		],
	},
];

const openInviteDialog = async () => {
	inviteEmail.value = "";
	inviteRole.value = "Editor";
	inviteError.value = "";
	showInviteDialog.value = true;
	await nextTick();
	inviteInputRef.value?.$el?.querySelector?.("input")?.focus();
};

const sendInvite = async (site: SiteSummary) => {
	const email = inviteEmail.value.trim();
	if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
		inviteError.value = __("Enter an email address, like name@example.com.");
		return;
	}
	inviteError.value = "";
	const result = await change<{ email: string; dev_invite_url?: string }>(
		"invite",
		{ email, role: inviteRole.value },
		{ loading: __("Inviting {0}…", [email]), success: (r) => __("Invite sent to {0}", [r.email]) },
	);
	if (!result) return;
	showInviteDialog.value = false;
	devInvite.value = result.dev_invite_url ? { email: result.email, url: result.dev_invite_url } : null;
};

const setRole = (member: SiteMember, role: SiteRole) => {
	if (role === member.role) return;
	change(
		"set_member_role",
		{ user: member.user, role },
		{
			loading: __("Updating {0}…", [member.user]),
			success: __("{0} is now {1}", [member.user, roleLabels[role]]),
		},
	);
};

const removeMember = async (site: SiteSummary, member: SiteMember) => {
	const name = member.full_name || member.user;
	const sure = await confirm(
		__("They lose access to {0} and are signed out of its editor.", [site.subdomain]),
		__("Remove {0}?", [name]),
	);
	if (!sure) return;
	change(
		"remove_member",
		{ user: member.user },
		{ loading: __("Removing {0}…", [member.user]), success: __("{0} was removed", [member.user]) },
	);
};

const cancelInvite = async (site: SiteSummary, invite: SiteInvite) => {
	if (!(await confirm(__("Are you sure you want to cancel the invitation to {0}?", [invite.email])))) return;
	const done = await change(
		"remove_member",
		{ user: invite.email },
		{ loading: __("Cancelling the invitation…"), success: __("Invitation cancelled") },
	);
	if (done && devInvite.value?.email === invite.email) devInvite.value = null;
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
