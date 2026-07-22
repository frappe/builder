<template>
	<div class="flex h-full flex-col gap-3">
		<div class="flex items-center gap-2">
			<BuilderInput
				type="text"
				class="flex-1"
				placeholder="Invite by email, comma-separated"
				:modelValue="inviteEmails"
				:hideClearButton="true"
				@input="(val: string) => (inviteEmails = val)"
				@keydown.enter.prevent="sendInvites" />
			<Button
				variant="solid"
				:disabled="!inviteEmails.trim()"
				:loading="inviteResource.loading"
				@click="sendInvites">
				Invite
			</Button>
		</div>

		<BuilderInput
			type="text"
			placeholder="Search members"
			icon-left="search"
			:modelValue="searchQuery"
			@input="(val: string) => (searchQuery = val)" />

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
				<span class="sticky top-0 z-10 bg-surface-base pb-1 text-sm text-ink-gray-5">
					Members ({{ filteredMembers.length }})
				</span>
				<div
					v-for="user in filteredMembers"
					:key="user.name"
					class="flex items-center gap-2 border-b border-outline-gray-1 py-2">
					<Avatar shape="circle" :image="user.user_image" :label="user.full_name" size="lg" />
					<div class="flex min-w-0 flex-col">
						<span class="truncate text-sm text-ink-gray-8">{{ user.full_name }}</span>
						<span class="truncate text-xs text-ink-gray-5">{{ user.name }}</span>
					</div>
					<Badge v-if="user.name === sessionUser" theme="gray" class="ml-auto">You</Badge>
				</div>
				<div v-if="!filteredMembers.length" class="py-6 text-center text-sm text-ink-gray-5">
					<template v-if="searchQuery.trim()">No members match "{{ searchQuery }}"</template>
					<template v-else>No members yet. Invite someone to give them access to Builder.</template>
				</div>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import router, { sessionUser } from "@/router";
import { confirm } from "@/utils/helpers";
import { UseTimeAgo } from "@vueuse/components";
import { Avatar, Badge, createResource, toast } from "frappe-ui";
import { computed, ref } from "vue";

type PendingInvite = {
	name: string;
	email: string;
	creation: string;
	invited_by_name?: string;
};
type BuilderUser = { name: string; full_name: string; user_image?: string };

const inviteEmails = ref("");
const searchQuery = ref("");
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
