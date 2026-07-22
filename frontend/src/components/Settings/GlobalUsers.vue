<template>
	<div class="flex h-full flex-col gap-6">
		<div class="flex items-center gap-2">
			<BuilderInput
				type="text"
				class="flex-1"
				placeholder="jane@example.com, john@example.com"
				:modelValue="inviteEmails"
				:hideClearButton="true"
				@input="(val: string) => (inviteEmails = val)"
				@keydown.enter.prevent="sendInvites" />
			<Button variant="solid" :loading="inviteResource.loading" @click="sendInvites">Invite</Button>
		</div>

		<div class="min-h-0 flex-1 overflow-y-auto">
			<div v-if="pendingInvites.data?.length" class="mb-6 flex flex-col">
				<span class="mb-1 text-sm text-ink-gray-5">Pending Invites</span>
				<div
					v-for="invite in pendingInvites.data"
					:key="invite.name"
					class="group flex items-center justify-between border-b border-outline-gray-1 py-2">
					<span class="text-sm text-ink-gray-8">{{ invite.email }}</span>
					<div class="flex items-center gap-1 opacity-0 group-hover:opacity-100">
						<Button variant="ghost" size="sm" @click="resendInvite(invite)">Resend</Button>
						<Button
							variant="ghost"
							size="sm"
							icon="lucide-x"
							title="Cancel invitation"
							@click="cancelInvite(invite)" />
					</div>
				</div>
			</div>

			<div class="flex flex-col">
				<span class="mb-1 text-sm text-ink-gray-5">Members</span>
				<div
					v-for="user in builderUsers.data"
					:key="user.name"
					class="flex items-center gap-2 border-b border-outline-gray-1 py-2">
					<Avatar shape="circle" :image="user.user_image" :label="user.full_name" size="lg" />
					<div class="flex flex-col">
						<span class="text-sm text-ink-gray-8">{{ user.full_name }}</span>
						<span class="text-xs text-ink-gray-5">{{ user.name }}</span>
					</div>
				</div>
				<div
					v-if="builderUsers.data && !builderUsers.data.length"
					class="py-6 text-center text-sm text-ink-gray-5">
					No members yet. Invite someone to give them access to Builder.
				</div>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import router from "@/router";
import { confirm } from "@/utils/helpers";
import { Avatar, createResource, toast } from "frappe-ui";
import { ref } from "vue";

type PendingInvite = { name: string; email: string; roles: string[] };

const inviteEmails = ref("");
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
