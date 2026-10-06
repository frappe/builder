<template>
	<div class="divide-y divide-outline-gray-1 overflow-hidden rounded-6 border border-outline-gray-1">
		<section v-for="group in groups" :key="group.name" class="divide-y divide-outline-gray-1">
			<header class="bg-surface-gray-1 px-3 py-2">
				<p class="text-xs font-medium" :class="group.sensitive ? 'text-ink-red-6' : 'text-ink-gray-8'">
					{{ group.name }}
				</p>
				<p class="pt-0.5 text-xs text-ink-gray-5">{{ group.summary }}</p>
			</header>

			<div class="divide-y divide-outline-gray-1 px-3">
				<div v-for="permission in group.permissions" :key="permission" class="py-3">
					<Switch
						size="sm"
						:disabled="readOnly"
						:description="permissionDetails[permission].warning"
						:model-value="granted.includes(permission)"
						@update:model-value="(allow: boolean) => answer(permission, allow)">
						<template #label>
							<span class="text-xs">{{ permissionDetails[permission].label }}</span>
						</template>
					</Switch>
				</div>
			</div>
		</section>
	</div>
</template>

<script setup lang="ts">
import { permissionDetails, groupPermissions, isSensitive } from "@/extensions/permissionClasses";
import { confirm } from "@/utils/helpers";
import type { Permission } from "frappe-builder-extension-sdk/types";
import { Switch } from "frappe-ui";
import { computed } from "vue";

const props = defineProps<{
	extension: string;
	label: string;
	requested: Permission[];
	granted: Permission[];
	/** A user who cannot manage extensions sees this, but cannot change it. */
	readOnly?: boolean;
}>();

const emit = defineEmits<{
	"update:granted": [permissions: Permission[]];
}>();

/** Only the permissions that this extension asked for. The user cannot add other permissions. */
const groups = computed(() => groupPermissions(props.requested));

/**
 * To turn a permission off asks nothing. Fewer permissions can break only the
 * extension. To turn a sensitive permission on gives access to site data or to
 * each published page. So only that direction shows the warning.
 *
 * The parent decides where the list goes. An installation writes it. The
 * install dialog keeps it until the user installs.
 */
const answer = async (permission: Permission, allow: boolean) => {
	if (allow && isSensitive(permission) && !(await confirmSensitive(permission))) return;

	emit(
		"update:granted",
		allow ? [...props.granted, permission] : props.granted.filter((granted) => granted !== permission),
	);
};

const confirmSensitive = (permission: Permission) =>
	confirm(
		`${permissionDetails[permission].warning} Allow ${props.label} to ${permissionDetails[
			permission
		].label.toLowerCase()}?`,
		"This reaches the whole site",
	);
</script>
