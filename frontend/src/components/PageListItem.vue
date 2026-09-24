<template>
	<router-link
		:to="{ name: 'builder', params: { pageId: page.page_name } }"
		class="group block h-fit w-full"
		@contextmenu.prevent="menuOpen = true">
		<div
			class="group relative flex w-full justify-between overflow-hidden rounded-8 p-3 hover:cursor-pointer hover:bg-surface-gray-1">
			<div class="flex w-[85%] gap-4">
				<img
					width="140"
					height="82"
					:src="page.meta_image || page.preview"
					alt=""
					onerror="this.src='/assets/builder/images/fallback.png'"
					class="block aspect-video w-36 flex-shrink-0 overflow-hidden rounded-6 bg-surface-gray-1 object-cover shadow-md" />
				<div class="flex flex-1 items-start justify-between overflow-hidden">
					<span class="flex h-full w-full flex-col justify-between text-base">
						<div>
							<div class="flex items-center gap-1">
								<p class="truncate font-medium text-ink-gray-9" :title="page.page_title || page.page_name">
									<template v-if="folderLabel">
										<span class="font-normal text-ink-gray-5">{{ folderLabel }}</span>
										<span class="mx-1.5 font-normal text-ink-gray-4">/</span>
									</template>
									{{ page.page_title || page.page_name }}
								</p>
							</div>
							<div class="mt-1 flex items-center gap-2 text-ink-gray-6">
								<span
									:title="__('Limited access')"
									class="lucide-shield-user size-4 shrink-0 text-ink-amber-6"
									v-if="(page.published || page.staging) && page.authenticated_access" />
								<p class="min-w-0 truncate text-sm" :title="page.route">
									{{ page.route }}
								</p>
							</div>
						</div>
						<UseTimeAgo v-slot="{ timeAgo }" :time="timestamp">
							<PageStatusLine
								:page="page"
								:time="
									sortedByCreation
										? __('Created {0} by {1}', [timeAgo, owner.fullname])
										: __('Updated {0} by {1}', [timeAgo, modifiedBy.fullname])
								" />
						</UseTimeAgo>
					</span>
				</div>
			</div>
			<div class="flex h-fit items-center gap-2">
				<!-- the menu sits inside the card link, so its clicks must not follow it -->
				<div class="contents" @click.stop.prevent>
					<PageActionsDropdown v-model:open="menuOpen" :page="page" size="sm" align="end" v-slot="{ open }">
						<span
							class="lucide-more-horizontal h-4 w-4 font-bold text-ink-gray-6 opacity-0 focus-visible:opacity-100 group-hover:opacity-100"
							:class="{ '!opacity-100': open }"
							aria-hidden="true"
							@click.stop />
					</PageActionsDropdown>
				</div>
				<Avatar
					:shape="'circle'"
					:image="owner.image"
					:label="owner.fullname"
					class="[&>div]:bg-surface-gray-2 [&>div]:text-ink-gray-4 [&>div]:group-hover:bg-surface-gray-4 [&>div]:group-hover:text-ink-gray-6"
					size="sm"
					:title="__('Created by {0}', [owner.fullname])" />
			</div>
		</div>
		<div class="mx-4 border-b border-outline-gray-1 group-last:hidden"></div>
	</router-link>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import PageActionsDropdown from "@/components/PageActionsDropdown.vue";
import { useDashboardState } from "@/composables/useDashboardState";
import PageStatusLine from "@/components/PageStatusLine.vue";
import { BuilderPage } from "@/types/doctypes";
import { getUserInfo } from "@/usersInfo";
import { UseTimeAgo } from "@vueuse/components";
import { Avatar } from "frappe-ui";
import { computed, ref } from "vue";

const props = defineProps<{
	page: BuilderPage;
}>();

const modifiedBy = getUserInfo(props.page.modified_by);
const owner = getUserInfo(props.page.owner);
const { orderBy, dashboardView, searchFilter } = useDashboardState();
const menuOpen = ref(false);
const sortedByCreation = computed(() => orderBy.value === "creation");
// outside a folder the row says which folder the page lives in
const folderLabel = computed(() =>
	dashboardView.value !== "folder" || searchFilter.value ? props.page.project_folder : "",
);
const timestamp = computed(() => (sortedByCreation.value ? props.page.creation : props.page.modified));
</script>
