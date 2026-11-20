<template>
	<slot v-if="session && site" :site="site" :session="session" />
	<div v-else-if="signedOut" class="flex flex-col items-start gap-3">
		<p class="text-p-sm text-ink-gray-6">
			{{ __("Your frappe.page sign-in has ended. Sign in again to manage this site.") }}
		</p>
		<Button variant="solid" :label="__('Sign In Again')" @click="signInAgain" />
	</div>
	<div v-else-if="error" class="flex flex-col items-start gap-3">
		<ErrorMessage :message="error" />
		<Button :label="__('Try Again')" @click="reload" />
	</div>
	<div v-else class="text-p-sm text-ink-gray-5">{{ __("Loading…") }}</div>
</template>
<script setup lang="ts">
// The frame of the frappe.page site panes: the site from the control site, or why it is not there.
import { __ } from "@/translation";
import {
	signInAgainURL,
	useFrappePageSite,
	type EditorSession,
	type SiteSummary,
} from "@/data/frappePageSite";
import { ErrorMessage } from "frappe-ui";
import { onActivated } from "vue";

defineSlots<{ default(props: { site: SiteSummary; session: EditorSession }): any }>();

const { session, site, error, signedOut, reload } = useFrappePageSite();

// members and domains change from other browsers too: the pane shows them afresh each time it opens
onActivated(() => reload());

const signInAgain = () => (window.location.href = signInAgainURL());
</script>
