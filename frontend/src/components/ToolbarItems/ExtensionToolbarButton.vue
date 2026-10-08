<template>
	<Tooltip :text="tooltip" :hoverDelay="0.6" arrow-class="mb-3">
		<Button
			class="relative"
			variant="ghost"
			:icon="icon.startsWith('lucide-') ? undefined : icon"
			:disabled="disabled"
			:label="label"
			@click="click">
			<template v-if="icon.startsWith('lucide-')" #icon>
				<RuntimeLucideIcon :name="icon" class="size-4.5" />
			</template>
			<template v-if="badge !== null && badge !== undefined" #suffix>
				<span
					class="pointer-events-none absolute -right-0.5 -top-0.5 grid h-3.5 min-w-3.5 place-items-center rounded-full bg-amber-100 px-0.5 text-[9px] font-medium text-amber-700">
					{{ badge }}
				</span>
			</template>
		</Button>
	</Tooltip>
</template>

<script setup lang="ts">
/**
 * A toolbar button from an extension. Builder makes it with its own components.
 * This component does not know about the bridge. The bridge gives `onClick`.
 */
import { Button, Tooltip } from "frappe-ui";

const props = defineProps<{
	icon: string;
	tooltip?: string;
	label?: string;
	badge?: string | number | null;
	disabled?: boolean;
	onClick?: () => void;
}>();

// Remove the focus after a click, like the built-in buttons.
const click = (event: MouseEvent) => {
	(event.currentTarget as HTMLElement)?.blur();
	props.onClick?.();
};
</script>
