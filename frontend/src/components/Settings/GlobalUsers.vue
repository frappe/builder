<template>
	<div class="flex h-full flex-col gap-5">
		<div class="flex items-center justify-between gap-2">
			<BuilderInput
				type="text"
				class="w-72"
				placeholder="按姓名或邮箱搜索"
				icon-left="search"
				:modelValue="searchQuery"
				@input="(val: string) => (searchQuery = val)" />
			<Button variant="solid" icon-left="lucide-plus" @click="openInviteDialog">邀请</Button>
		</div>

		<div class="min-h-0 flex-1 overflow-y-auto">
			<div v-if="filteredInvites.length" class="mb-6 flex flex-col">
				<span class="sticky top-0 z-10 bg-surface-base pb-1 text-p-sm text-ink-gray-5">
					待处理邀请 ({{ filteredInvites.length }})
				</span>
				<div
					v-for="invite in filteredInvites"
					:key="invite.name"
					class="flex items-center justify-between gap-2 border-b border-outline-gray-1 py-2 last:border-b-0">
					<div class="flex min-w-0 items-center gap-2">
						<Avatar shape="circle" :label="invite.email" size="lg" />
						<div class="flex min-w-0 flex-col">
							<span class="truncate text-p-sm text-ink-gray-8">{{ invite.email }}</span>
							<UseTimeAgo v-slot="{ timeAgo }" :time="invite.creation">
								<span class="truncate text-p-xs text-ink-gray-5">
									已邀请 {{ timeAgo }}{{ invite.invited_by_name ? ` 由 ${invite.invited_by_name}` : "" }}
								</span>
							</UseTimeAgo>
						</div>
					</div>
					<div class="flex shrink-0 items-center gap-1">
						<Button variant="subtle" size="sm" @click="resendInvite(invite)">重新发送</Button>
						<Button
							variant="subtle"
							size="sm"
							icon="lucide-x"
							title="取消邀请"
							@click="cancelInvite(invite)" />
					</div>
				</div>
			</div>

			<div class="flex flex-col">
				<span class="sticky top-0 z-10 bg-surface-base pb-1 text-p-sm text-ink-gray-5">
					成员 ({{ filteredMembers.length }})
				</span>
				<div
					v-for="user in filteredMembers"
					:key="user.name"
					class="flex items-center gap-2 border-b border-outline-gray-1 py-2 last:border-b-0">
					<Avatar shape="circle" :image="user.user_image" :label="user.full_name" size="lg" />
					<div class="flex min-w-0 flex-col">
						<span class="truncate text-p-sm text-ink-gray-8">
							{{ user.full_name }}
							<Badge v-if="user.name === sessionUser" theme="gray" class="ml-1">你</Badge>
						</span>
						<span class="truncate text-p-xs text-ink-gray-5">{{ user.name }}</span>
					</div>
					<Badge v-if="user.is_admin" theme="gray" class="ml-auto shrink-0">管理员</Badge>
				</div>
				<div v-if="!filteredMembers.length" class="py-6 text-center text-p-sm text-ink-gray-5">
					<template v-if="searchQuery.trim()">没有成员匹配“{{ searchQuery }}”</template>
					<template v-else>暂无成员。邀请他人以授予其访问 Builder 的权限。</template>
				</div>
			</div>
		</div>

		<Dialog
			v-model="showInviteDialog"
			title="邀请用户"
			:actions="[{ label: '发送邀请', variant: 'solid', onClick: sendInvites }]">
			<template #default>
				<BuilderInput
					:ref="(el) => (inviteInputRef = el)"
					type="textarea"
					label="邮箱地址"
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
	is_admin: boolean;
};

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
	inviteInputRef.value?.$el?.querySelector?.("textarea, input")?.focus();
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
			toast.success(`已向 ${res.invited_emails.join(", ")} 发送邀请`);
		}
		if (res.pending_invite_emails.length) {
			toast.info(`已邀请过：${res.pending_invite_emails.join(", ")}`);
		}
		if (res.accepted_invite_emails.length) {
			toast.info(`已是成员：${res.accepted_invite_emails.join(", ")}`);
		}
		if (res.disabled_user_emails.length) {
			toast.error(`用户已禁用：${res.disabled_user_emails.join(", ")}`);
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
		toast.success(`已重新向 ${invite.email} 发送邀请`);
	} catch (error) {
		toast.error(errorMessage(error));
	}
};

const cancelInvite = async (invite: PendingInvite) => {
	if (!(await confirm(`确定要取消向 ${invite.email} 发出的邀请吗？`))) return;
		try {
			await cancelResource.submit({ name: invite.name, app_name: "builder" });
			toast.success("邀请已取消");
		pendingInvites.fetch();
	} catch (error) {
		toast.error(errorMessage(error));
	}
};
</script>
