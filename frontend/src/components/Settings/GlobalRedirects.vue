<template>
	<div class="flex h-full flex-col">
		<div class="mb-3">
			<BuilderInput
				:modelValue="searchQuery"
				@input="(val: string) => (searchQuery = val)"
				@update:modelValue="(val: string) => (searchQuery = val)"
				type="text"
				placeholder="搜索重定向"
				class="w-full"
				icon-left="search" />
		</div>

		<div class="min-h-0 flex-1 overflow-y-auto">
			<div
				class="sticky top-0 z-10 border-b border-outline-gray-1 bg-surface-base pb-2 pt-1 text-sm text-ink-gray-5"
				:class="rowGridClass">
				<div class="pl-2">来源</div>
				<div class="border-l border-outline-gray-1 pl-2">目标</div>
				<div></div>
			</div>

			<button
				v-if="!searchQuery.trim()"
				class="flex w-full items-center gap-2 border-b border-outline-gray-1 px-2 py-2 text-sm text-ink-gray-5 hover:bg-surface-gray-1 hover:text-ink-gray-8"
				@click="openAdd">
				<span class="lucide-plus size-4" aria-hidden="true" />
				添加重定向
			</button>

			<div
				v-for="row in rows"
				:key="row.id"
				data-row
				:data-row-id="row.id"
				class="group/row cursor-pointer border-b border-outline-gray-1 py-1 hover:bg-surface-gray-1"
				:class="rowGridClass"
				@click="openEdit(row)">
				<div
					v-for="(field, i) in fields"
					:key="field"
					class="flex min-w-0 items-center gap-2 px-2 py-1 text-sm text-ink-gray-8"
					:class="i === 1 && cellDividerClass">
					<span class="min-w-0 flex-1 truncate" v-html="highlight(field, row[field])" />
					<span
						v-if="field === 'to' && (row.status !== '301' || row.forward)"
						class="flex shrink-0 items-center gap-1 rounded bg-surface-gray-3 px-1.5 py-0.5 text-xs text-ink-gray-5"
						:title="`HTTP ${row.status}${row.forward ? ' · forwards query parameters' : ''}`">
						<span v-if="row.status !== '301'" class="tabular-nums">{{ row.status }}</span>
						<span v-if="row.forward" class="lucide-arrow-right-left size-3" aria-hidden="true" />
					</span>
				</div>
				<div class="flex justify-end">
					<span
						class="lucide-trash size-3.5 cursor-pointer text-ink-gray-5 opacity-0 hover:text-ink-gray-8 group-hover/row:opacity-100"
						aria-hidden="true"
						@click.stop="deleteRedirect(row.id)" />
				</div>
			</div>

			<div v-if="searchQuery.trim() && !rows.length" class="px-2 py-6 text-center text-sm text-ink-gray-5">
				没有重定向匹配 "{{ searchQuery }}"
			</div>
		</div>

		<Dialog
			v-model="showDialog"
			:title="editingId ? '编辑重定向' : '添加重定向'"
			:actions="[{ label: editingId ? '保存' : '添加重定向', variant: 'solid', onClick: commit }]">
			<template #default>
				<div class="flex flex-col gap-3">
					<BuilderInput
						v-for="field in fields"
						:key="field"
						required
						:ref="(el) => field === 'from' && (fromRef = el)"
						:modelValue="draft[field]"
						:label="field === 'from' ? '来源' : '目标'"
						type="text"
						:hideClearButton="true"
						:placeholder="placeholders[field]"
						@input="(val: string) => (draft[field] = val)"
						@keydown.enter.prevent="commit" />
					<button
						type="button"
						class="flex items-center gap-1 text-sm text-ink-gray-5 hover:text-ink-gray-8"
						@click="advancedOpen = !advancedOpen">
						<span
							class="size-3.5"
							:class="advancedOpen ? 'lucide-chevron-down' : 'lucide-chevron-right'"
							aria-hidden="true" />
						高级
					</button>
					<template v-if="advancedOpen">
						<FormControl
							type="select"
							size="sm"
							label="重定向状态"
							:options="statusOptions"
							:modelValue="draft.status"
							@update:modelValue="(val: string) => (draft.status = val)" />
						<Switch
							size="sm"
							label="转发查询参数"
							description="将原始查询字符串附加到目标 URL"
							class="mt-2"
							:modelValue="draft.forward"
							@update:modelValue="(val: boolean) => (draft.forward = val)" />
					</template>

					<div v-if="!editingId" class="mt-3 text-xs">
						<p class="mb-2 text-ink-gray-5">示例</p>
						<div class="grid w-fit grid-cols-[auto_auto_auto_1fr] items-center gap-x-3 gap-y-1.5">
							<template v-for="example in examples" :key="example.label">
								<code class="font-mono text-ink-gray-7" v-html="highlight('from', example.from)" />
								<span class="lucide-arrow-right size-3 text-ink-gray-4" aria-hidden="true" />
								<code class="font-mono text-ink-gray-7" v-html="highlight('to', example.to)" />
								<span class="pl-4 text-ink-gray-5">{{ example.label }}</span>
							</template>
						</div>
					</div>
				</div>
			</template>
		</Dialog>
	</div>
</template>
<script setup lang="ts">
import routeRedirects from "@/data/routeRedirects";
import { confirm } from "@/utils/helpers";
import { highlightSource, highlightTarget } from "@/utils/redirectSyntax";
import { Dialog, FormControl, Switch, toast } from "frappe-ui";
import { computed, nextTick, onMounted, ref } from "vue";

type Field = "from" | "to";
type RedirectRow = { id: string; from: string; to: string; status: string; forward: boolean };
type Draft = { from: string; to: string; status: string; forward: boolean };

const rowGridClass = "grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_28px] items-center gap-x-2 px-1";
const cellDividerClass = "border-l border-outline-gray-1 pl-2";
const fields = ["from", "to"] as const;
const placeholders: Record<Field, string> = { from: "/old-path", to: "/new-path" };
const statusOptions = [
	{ label: "301 - 永久移动", value: "301" },
	{ label: "302 - 已找到（临时）", value: "302" },
	{ label: "307 - 临时重定向", value: "307" },
	{ label: "308 - 永久重定向", value: "308" },
];

const highlight = (field: Field, value: string) =>
	field === "to" ? highlightTarget(value) : highlightSource(value);

	const examples = [
	{ from: "/old-page", to: "/new-page", label: "精确路径" },
	{ from: "/docs", to: "https://example.com/docs", label: "外部 URL" },
	{ from: "/blog/(.*)", to: "/news/\\1", label: "正则表达式捕获" },
];

const searchQuery = ref("");
const showDialog = ref(false);
const editingId = ref<string | null>(null);
const advancedOpen = ref(false);
const draft = ref<Draft>({ from: "", to: "", status: "301", forward: false });
const fromRef = ref<any>(null);

const focusInput = (el: any) => el?.$el?.querySelector?.("input")?.focus();

onMounted(() => routeRedirects.fetch());

const findIndex = (id: string) => (routeRedirects.data ?? []).findIndex((r: any) => r.name === id);

const rows = computed<RedirectRow[]>(() => {
	const query = searchQuery.value.toLowerCase().trim();
	return (routeRedirects.data || [])
		.map(
			(r: any): RedirectRow => ({
				id: r.name,
				from: r.source,
				to: r.target,
				status: String(r.redirect_http_status || "301"),
				forward: Boolean(r.forward_query_parameters),
			}),
		)
		.filter(
			(row: RedirectRow) =>
				!query || row.from.toLowerCase().includes(query) || row.to.toLowerCase().includes(query),
		);
});

const performOptimisticUpdate = (
	operation: () => Promise<any>,
	optimistic: () => void,
	revert: () => void,
	messages: { loading: string; success: string; error: string },
) => {
	optimistic();
	toast.promise(operation(), {
		loading: messages.loading,
		success: () => (routeRedirects.fetch(), messages.success),
		error: (err: any) => (revert(), `${messages.error}: ${err}`),
	});
};

const openAdd = async () => {
	editingId.value = null;
	advancedOpen.value = false;
	draft.value = { from: "", to: "", status: "301", forward: false };
	showDialog.value = true;
	await nextTick();
	focusInput(fromRef.value);
};

const openEdit = (row: RedirectRow) => {
	editingId.value = row.id;
	advancedOpen.value = row.status !== "301" || row.forward;
	draft.value = { from: row.from, to: row.to, status: row.status, forward: row.forward };
	showDialog.value = true;
};

// fields the doctype expects, derived from the in-memory draft
const docFields = (d: Draft) => ({
	source: d.from,
	target: d.to,
	redirect_http_status: d.status,
	forward_query_parameters: d.forward ? 1 : 0,
});

const commit = () => {
	const d = draft.value;
	if (!d.from || !d.to) return;
	showDialog.value = false;
	editingId.value ? saveExisting(editingId.value, d) : insertNew(d);
};

const insertNew = (d: Draft) => {
	const tempId = `temp_${Date.now()}`;
	performOptimisticUpdate(
		() =>
			routeRedirects.insert.submit({
				...docFields(d),
				parenttype: "Website Settings",
				parentfield: "route_redirects",
				parent: "Website Settings",
			}),
		() => {
			if (!routeRedirects.data) routeRedirects.data = [];
			routeRedirects.data.unshift({ ...docFields(d), name: tempId });
		},
		() => {
			const i = findIndex(tempId);
			if (i !== -1) routeRedirects.data?.splice(i, 1);
		},
		{ loading: "正在添加重定向...", success: "重定向已添加", error: "添加重定向出错" },
	);
};

const saveExisting = (id: string, d: Draft) => {
	const index = findIndex(id);
	const backup = index !== -1 ? { ...routeRedirects.data![index] } : null;
	performOptimisticUpdate(
		() => routeRedirects.setValue.submit({ name: id, ...docFields(d) }),
		() => index !== -1 && Object.assign(routeRedirects.data![index], docFields(d)),
		() => backup && Object.assign(routeRedirects.data![index], backup),
		{ loading: "正在更新重定向...", success: "重定向已更新", error: "更新重定向出错" },
	);
};

const deleteRedirect = async (id: string) => {
	const row = rows.value.find((r) => r.id === id);
	const message = row
		? `确定要删除从 "${row.from}" 到 "${row.to}" 的重定向吗？`
		: "确定要删除此重定向吗？";
	if (!(await confirm(message))) return;

	const index = findIndex(id);
	const backup = index !== -1 ? { ...routeRedirects.data![index] } : null;
	performOptimisticUpdate(
		() => routeRedirects.delete.submit(id),
		() => index !== -1 && routeRedirects.data!.splice(index, 1),
		() => backup && routeRedirects.data!.splice(index, 0, backup),
		{ loading: "正在删除重定向...", success: "重定向已删除", error: "删除重定向出错" },
	);
};
</script>
