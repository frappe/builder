<template>
	<div class="flex h-full flex-col gap-3">
		<div class="flex items-center justify-between gap-2">
			<BuilderInput
				type="text"
				class="w-72"
				placeholder="Search by name or email"
				icon-left="search"
				:modelValue="searchQuery"
				@input="(val: string) => (searchQuery = val)" />
			<Button variant="solid" icon-left="lucide-plus" @click="openInviteDialog">Invite</Button>
		</div>

		<div class="min-h-0 flex-1 overflow-y-auto">
			<div v-if="filteredInvites.length" class="mb-5 flex flex-col">
				<span class="sticky top-0 z-10 bg-surface-base pb-1 text-sm text-ink-gray-5">
					Pending Invites ({{ filteredInvites.length }})
				</span>
				<div
					v-for="invite in filteredInvites"
					:key="invite.name"
					class="flex items-center justify-between gap-2 border-b border-outline-gray-1 py-2">
					<div class="flex min-w-0 items-center gap-2">
						<Avatar shape="circle" :label="invite.email" size="lg" />
						<div class="flex min-w-0 flex-col">
							<span class="truncate text-sm text-ink-gray-8">{{ invite.email }}</span>
							<UseTimeAgo v-slot="{ timeAgo }" :time="invite.creation">
								<span class="truncate text-xs text-ink-gray-5">
									Invited {{ timeAgo }}{{ invite.invited_by_name ? ` by ${invite.invited_by_name}` : "" }}
								</span>
							</UseTimeAgo>
						</div>
					</div>
					<div class="flex shrink-0 items-center gap-1">
						<Button variant="subtle" size="sm" @click="resendInvite(invite)">Resend</Button>
						<Button
							variant="subtle"
							size="sm"
							icon="lucide-x"
							title="Cancel invitation"
							@click="cancelInvite(invite)" />
					</div>
				</div>
			</div>

			<div class="flex flex-col">
				<div
					class="sticky top-0 z-10 border-b border-outline-gray-1 bg-surface-base pb-2 text-sm text-ink-gray-5"
					:class="rowGridClass">
					<span>User</span>
					<span>Role</span>
					<span>User since</span>
					<span></span>
				</div>
				<div
					v-for="user in filteredMembers"
					:key="user.name"
					class="group border-b border-outline-gray-1 py-2"
					:class="rowGridClass">
					<div class="flex min-w-0 items-center gap-2">
						<Avatar shape="circle" :image="user.user_image" :label="user.full_name" size="lg" />
						<div class="flex min-w-0 flex-col">
							<span class="truncate text-sm text-ink-gray-8">
								{{ user.full_name }}
								<Badge v-if="user.name === sessionUser" theme="gray" class="ml-1">You</Badge>
							</span>
							<span class="truncate text-xs text-ink-gray-5">{{ user.name }}</span>
						</div>
					</div>
					<span class="text-sm text-ink-gray-7">{{ user.is_admin ? "Admin" : "User" }}</span>
					<span class="text-sm text-ink-gray-7">{{ memberSince(user.creation) }}</span>
					<Button
						v-if="!user.is_admin && user.name !== sessionUser"
						variant="ghost"
						size="sm"
						icon="lucide-trash-2"
						title="Remove from Builder"
						@click="removeUser(user)" />
				</div>
				<div v-if="!filteredMembers.length" class="py-6 text-center text-sm text-ink-gray-5">
					<template v-if="searchQuery.trim()">No members match "{{ searchQuery }}"</template>
					<template v-else>No members yet. Invite someone to give them access to Builder.</template>
				</div>
			</div>
		</div>

		<Dialog
			v-model="showInviteDialog"
			title="Invite Users"
			:actions="[{ label: 'Send Invitation', variant: 'solid', onClick: sendInvites }]">
			<template #default>
				<BuilderInput
					:ref="(el) => (inviteInputRef = el)"
					type="text"
					label="Email addresses"
					placeholder="jane@example.com, john@example.com"
					:hideClearButton="true"
					:modelValue="inviteEmails"
					@input="(val: string) => (inviteEmails = val)"
					@keydown.enter.prevent="sendInvites" />
			</template>
		</Dialog>
	</div>
</template>
<script setup lang="ts">
import router, { sessionUser } from "@/router";
import { confirm } from "@/utils/helpers";
import { UseTimeAgo } from "@vueuse/components";
import { Avatar, Badge, Dialog, createResource, toast } from "frappe-ui";
import { computed, nextTick, ref } from "vue";

type PendingInvite = {
	name: string;
	email: string;
	creation: string;
	invited_by_name?: string;
};
type BuilderUser = {
	name: string;
	full_name: string;
	user_image?: string;
	creation: string;
	is_admin: boolean;
};

const rowGridClass = "grid grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)_32px] items-center gap-x-2";

const inviteEmails = ref("");
const searchQuery = ref("");
const showInviteDialog = ref(false);
const inviteInputRef = ref<any>(null);
const builderPath = router.options.history.base || "/builder";

const builderUsers = createResource({
	url: "builder.api.get_builder_users",
	auto: true,
});

const pendingInvites = createResource({
	url: "builder.api.get_pending_invitations",
	auto: true,
});

const inviteResource = createResource({
	url: "frappe.core.api.user_invitation.invite_by_email",
});

const cancelResource = createResource({
	url: "frappe.core.api.user_invitation.cancel_invitation",
});

const resendResource = createResource({
	url: "frappe.core.api.user_invitation.resend_invitation",
});

const removeResource = createResource({
	url: "builder.api.remove_builder_user",
});

const memberSince = (creation: string) =>
	new Date(creation).toLocaleDateString(undefined, { month: "short", year: "numeric" });

const matchesSearch = (...values: (string | undefined)[]) => {
	const query = searchQuery.value.toLowerCase().trim();
	return !query || values.some((value) => value?.toLowerCase().includes(query));
};

const filteredInvites = computed<PendingInvite[]>(() =>
	(pendingInvites.data || []).filter((invite: PendingInvite) => matchesSearch(invite.email)),
);

const filteredMembers = computed<BuilderUser[]>(() => {
	const members = (builderUsers.data || []).filter((user: BuilderUser) =>
		matchesSearch(user.full_name, user.name),
	);
	return members.sort((a: BuilderUser, b: BuilderUser) =>
		a.name === sessionUser.value ? -1 : b.name === sessionUser.value ? 1 : 0,
	);
});

const openInviteDialog = async () => {
	inviteEmails.value = "";
	showInviteDialog.value = true;
	await nextTick();
	inviteInputRef.value?.$el?.querySelector?.("input")?.focus();
};

const errorMessage = (error: any) => error?.messages?.[0] || error?.message || String(error);

const sendInvites = async () => {
	const emails = inviteEmails.value.trim();
	if (!emails) return;
	try {
		const res = await inviteResource.submit({
			emails,
			roles: ["Website Manager"],
			redirect_to_path: builderPath,
			app_name: "builder",
		});
		if (res.invited_emails.length) {
			toast.success(`Invitation sent to ${res.invited_emails.join(", ")}`);
		}
		if (res.pending_invite_emails.length) {
			toast.info(`Already invited: ${res.pending_invite_emails.join(", ")}`);
		}
		if (res.accepted_invite_emails.length) {
			toast.info(`Already a member: ${res.accepted_invite_emails.join(", ")}`);
		}
		if (res.disabled_user_emails.length) {
			toast.error(`User is disabled: ${res.disabled_user_emails.join(", ")}`);
		}
		showInviteDialog.value = false;
		inviteEmails.value = "";
		pendingInvites.fetch();
	} catch (error) {
		toast.error(errorMessage(error));
	}
};

const resendInvite = async (invite: PendingInvite) => {
	try {
		await resendResource.submit({ name: invite.name, app_name: "builder" });
		toast.success(`Invitation resent to ${invite.email}`);
	} catch (error) {
		toast.error(errorMessage(error));
	}
};

const removeUser = async (user: BuilderUser) => {
	if (!(await confirm(`Remove ${user.full_name} from Builder?`))) return;
	try {
		await removeResource.submit({ user: user.name });
		toast.success(`${user.full_name} removed from Builder`);
		builderUsers.fetch();
	} catch (error) {
		toast.error(errorMessage(error));
	}
};

const cancelInvite = async (invite: PendingInvite) => {
	if (!(await confirm(`Are you sure you want to cancel the invitation to ${invite.email}?`))) return;
	try {
		await cancelResource.submit({ name: invite.name, app_name: "builder" });
		toast.success("Invitation cancelled");
		pendingInvites.fetch();
	} catch (error) {
		toast.error(errorMessage(error));
	}
};
</script>
