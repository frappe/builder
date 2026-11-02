<template>
	<Dialog v-model="open" title="Your project" size="4xl">
		<template #default>
			<Tabs v-model="tab" :tabs="tabItems" variant="subtle" class="workspace-tabs space-y-4 text-ink-gray-9">
				<template #tab-panel>
					<p v-if="error" role="alert" class="text-p-sm text-ink-red-5">{{ error }}</p>
					<p v-if="loading" class="text-p-sm text-ink-gray-5">Loading your project…</p>
					<div v-else-if="tab === 'Brief'" class="max-h-[60vh] space-y-6 overflow-y-auto p-1">
						<p class="text-p-sm text-ink-gray-6">
							Keep the facts, voice and constraints you want Bob to use across chats. Your corrections take
							precedence.
						</p>
						<div class="grid gap-4 sm:grid-cols-2">
							<FormControl
								v-for="field in fields"
								:key="field.key"
								v-model="brief[field.key]"
								class="min-w-0"
								type="textarea"
								:label="field.label"
								:placeholder="field.placeholder" />
						</div>
						<template v-for="kind in ['facts', 'decisions'] as const" :key="kind">
							<section v-if="brief[kind]?.length" class="space-y-3" :aria-label="kind">
								<div class="space-y-1">
									<h4 class="text-p-sm font-medium capitalize text-ink-gray-8">{{ kind }}</h4>
									<p class="text-p-xs text-ink-gray-6">
										Confirm what Bob should use, or exclude anything that isn't right.
									</p>
								</div>
								<ul
									class="m-0 list-none divide-y divide-outline-gray-2 rounded-5 border border-outline-gray-2 p-0">
									<li
										v-for="record in brief[kind]"
										:key="record.id"
										class="flex flex-col gap-3 p-3 sm:flex-row sm:items-start sm:gap-4">
										<div class="min-w-0 flex-1 space-y-1 [overflow-wrap:anywhere]">
											<p class="text-p-sm font-medium text-ink-gray-8">{{ record.label }}</p>
											<p class="whitespace-pre-wrap text-p-sm text-ink-gray-7">{{ record.value }}</p>
										</div>
										<div class="w-36 max-w-full shrink-0">
											<FormControl
												v-model="record.status"
												type="select"
												:options="recordStatuses"
												:aria-label="`Status for ${record.label || record.value}`" />
										</div>
									</li>
								</ul>
							</section>
						</template>
					</div>
					<div
						v-else-if="tab === 'Assets'"
						class="grid max-h-[65vh] gap-4 overflow-y-auto p-1 sm:grid-cols-3">
						<p v-if="!brief.assets?.length" class="col-span-full text-p-sm text-ink-gray-6">
							Ask Bob to find imagery, or upload your own in chat. Your choices will stay here.
						</p>
						<div
							v-for="asset in brief.assets || []"
							:key="asset.id || asset.url"
							class="space-y-2 rounded border border-outline-gray-2 p-2">
							<img
								v-if="safeImage(asset.thumb || asset.url)"
								:src="asset.thumb || asset.url"
								:alt="asset.description || 'Project asset'"
								class="aspect-[4/3] w-full rounded object-cover"
								loading="lazy" />
							<p class="text-p-xs text-ink-gray-6">{{ asset.credit || asset.provider }}</p>
							<FormControl
								:model-value="asset.role || 'undecided'"
								type="select"
								label="Use as"
								:options="['undecided', 'reference', 'content', 'logo', 'product', 'team']"
								@update:model-value="classify(asset, $event)" />
							<Button
								v-if="
									asset.provider === 'Upload' &&
									asset.preview_only &&
									['content', 'logo', 'product', 'team'].includes(asset.role)
								"
								:disabled="saving || !asset.selected"
								@click="prepareUpload(asset)">
								Make available on published page
							</Button>
							<p v-if="asset.preview_only || asset.requires_acquisition" class="text-p-xs text-ink-orange-5">
								Preview · acquire the original before building
							</p>
							<Button :disabled="saving" @click="selectAsset(asset)">
								{{ asset.selected ? "Remove from shortlist" : "Shortlist" }}
							</Button>
						</div>
					</div>
					<div
						v-else-if="tab === 'Versions'"
						class="grid max-h-[65vh] gap-4 overflow-y-auto p-1 sm:grid-cols-2">
						<p v-if="!variants.length" class="col-span-full text-p-sm text-ink-gray-6">
							Ask Bob for visual directions. Preview a layout, inspect its sections, or tweak it before
							choosing.
						</p>
						<AIDesignCard
							v-for="variant in variants"
							:key="variant.variant_id"
							:direction="variant"
							:selected="variant.status === 'selected'"
							:disabled="busy"
							:action-label="variant.status === 'selected' ? 'Continue this direction' : 'Use this direction'"
							@select="choose(variant)"
							@refine="refine(variant, $event)" />
					</div>
					<div v-else class="max-h-[65vh] overflow-y-auto p-1">
						<AIProjectPlan v-if="tab === 'Pages'" :project="project" />
						<AIMediaBudget
							v-if="tab === 'Spending' && pageId"
							:page-id="pageId"
							:can-reconcile="canReconcileMedia"
							:budget="mediaBudget"
							:requests="media"
							@resolved="load" />
					</div>
				</template>
			</Tabs>
		</template>
		<template v-if="tab === 'Brief' && !loading" #actions>
			<div class="flex items-center justify-between gap-4 border-t border-outline-gray-2 pt-4">
				<p class="text-p-xs text-ink-gray-6">Changes apply when you save.</p>
				<Button :loading="saving" :disabled="!pageId" variant="solid" @click="save">Save brief</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { Button, Dialog, FormControl, Tabs, call } from "frappe-ui";
import { ref, watch } from "vue";
import AIProjectPlan from "./AIProjectPlan.vue";
import AIMediaBudget from "./AIMediaBudget.vue";
import AIDesignCard from "./AIDesignCard.vue";
import { refinementReply } from "./cardDraft";
const props = defineProps<{ pageId: string | null; busy?: boolean }>();
const open = defineModel<boolean>({ default: false });
const emit = defineEmits<{ select: [prompt: string] }>();
const tabs = ["Brief", "Assets", "Versions", "Pages", "Spending"] as const;
const tabItems = tabs.map((name) => ({ value: name, label: name }));
const tab = ref<(typeof tabs)[number]>("Brief");
const brief = ref<Record<string, any>>({});
const variants = ref<Array<Record<string, any>>>([]);
const project = ref<any>(null),
	canReconcileMedia = ref(false),
	media = ref<any[]>([]),
	mediaBudget = ref<number | string>(0);
const loading = ref(false),
	saving = ref(false),
	error = ref("");
let epoch = 0;
const fields = [
	{ key: "project", label: "Project", placeholder: "What are you making, and for whom?" },
	{ key: "goal", label: "Visitor action", placeholder: "What should people do here?" },
	{ key: "audience", label: "Audience", placeholder: "Who needs this site?" },
	{ key: "voice", label: "Voice", placeholder: "How should it sound and feel?" },
	{ key: "content", label: "Real content", placeholder: "Your copy, products, story and useful details" },
	{
		key: "constraints",
		label: "Keep / avoid",
		placeholder: "Brand rules, accessibility needs, things you dislike",
	},
	{ key: "visual_direction", label: "Visual direction", placeholder: "The decisions you want to keep" },
	{ key: "open_questions", label: "Still deciding", placeholder: "What would you like help choosing?" },
];
const recordStatuses = [
	{ label: "Needs review", value: "proposed" },
	{ label: "Confirmed", value: "accepted" },
	{ label: "Don't use", value: "rejected" },
];
const safeImage = (value: unknown) =>
	typeof value === "string" && (/^\/(?!\/)/.test(value) || value.startsWith("https://"));
async function load() {
	if (!props.pageId) return;
	const current = ++epoch;
	loading.value = true;
	error.value = "";
	try {
		const data = await call("builder.ai.workspace.get_design_workspace", { page_id: props.pageId });
		if (current !== epoch) return;
		brief.value = data.brief;
		variants.value = data.variants;
		project.value = data.project;
		media.value = data.media || [];
		mediaBudget.value = data.media_budget_usd || 0;
		canReconcileMedia.value = data.can_reconcile_media || false;
	} catch {
		if (current === epoch) error.value = "Could not load your project. Close and reopen to retry.";
	} finally {
		if (current === epoch) loading.value = false;
	}
}
async function save() {
	const current = epoch;
	saving.value = true;
	error.value = "";
	const patch = Object.fromEntries(fields.map((field) => [field.key, brief.value[field.key] || ""]));
	try {
		const data = await call("builder.ai.workspace.save_design_brief", {
			page_id: props.pageId,
			expected_revision: brief.value.revision || 0,
			patch: { ...patch, facts: brief.value.facts || [], decisions: brief.value.decisions || [] },
		});
		if (current === epoch) {
			brief.value = data;
			saving.value = false;
			await load();
		}
	} catch (exception: any) {
		if (current === epoch)
			error.value =
				exception?.messages?.[0] ||
				"Could not save. The brief may have changed in another tab; reopen it to refresh.";
	} finally {
		if (current === epoch) saving.value = false;
	}
}
async function selectAsset(asset: Record<string, any>) {
	const current = epoch;
	saving.value = true;
	try {
		const state = await call("builder.ai.workspace.select_asset", {
			page_id: props.pageId,
			asset_id: asset.id || asset.url,
			selected: !asset.selected,
		});
		if (current === epoch) brief.value = state;
	} catch {
		if (current === epoch) error.value = "Could not update this asset.";
	} finally {
		if (current === epoch) saving.value = false;
	}
}

async function classify(asset: Record<string, any>, role: string) {
	await updateAsset("classify_asset", { asset_id: asset.id, role });
}
async function prepareUpload(asset: Record<string, any>) {
	await updateAsset("prepare_upload", { asset_id: asset.id });
}
async function updateAsset(method: string, args: Record<string, unknown>) {
	const current = epoch;
	saving.value = true;
	error.value = "";
	try {
		const data = await call(`builder.ai.workspace.${method}`, { page_id: props.pageId, ...args });
		if (current === epoch) brief.value = data;
	} catch (exception: any) {
		if (current === epoch) error.value = exception.messages?.[0] || "Could not update this asset.";
	} finally {
		if (current === epoch) saving.value = false;
	}
}
function choose(variant: Record<string, any>) {
	open.value = false;
	emit(
		"select",
		`Use the ${variant.label} direction. Apply its editable layout and continue from it. [design: ${variant.variant_id}]`,
	);
}
function refine(variant: Record<string, any>, changes: string) {
	open.value = false;
	emit("select", refinementReply(variant, changes));
}
watch([open, () => props.pageId], () => {
	epoch++;
	saving.value = false;
	if (open.value) load();
});
</script>

<style scoped>
.workspace-tabs :deep([role="tablist"]) {
	max-width: 100%;
	overflow-x: auto;
}
</style>
