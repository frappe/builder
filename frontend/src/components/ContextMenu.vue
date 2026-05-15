<template>
	<DropdownMenuRoot v-model:open="visible">
		<DropdownMenuTrigger as-child>
			<span class="fixed size-0" :style="{ top: currentPosY + 'px', left: currentPosX + 'px' }" />
		</DropdownMenuTrigger>
		<DropdownMenuPortal>
			<DropdownMenuContent
				class="z-50 min-w-[120px] rounded-lg bg-surface-white p-1 text-sm shadow-xl"
				:side-offset="0"
				align="start"
				avoid-collisions>
				<DropdownMenuItem
					v-for="(option, index) in options"
					:key="index"
					v-show="!option.condition || option.condition()"
					class="block cursor-pointer rounded px-3 py-1.5 text-ink-gray-9 outline-none data-[highlighted]:bg-surface-gray-4"
					:class="{ '!cursor-default !text-ink-gray-4': option.disabled?.() }"
					:disabled="option.disabled?.()"
					@select="handleClick(option.action)">
					{{ option.label }}
				</DropdownMenuItem>
			</DropdownMenuContent>
		</DropdownMenuPortal>
	</DropdownMenuRoot>
</template>
<script setup lang="ts">
import {
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuPortal,
	DropdownMenuRoot,
	DropdownMenuTrigger,
} from "reka-ui";
import { computed, ref, watch } from "vue";

interface ContextMenuOption {
	label: string;
	action: CallableFunction;
	condition?: () => boolean;
	disabled?: () => boolean;
}

const props = withDefaults(
	defineProps<{
		posX?: number;
		posY?: number;
		options?: ContextMenuOption[];
	}>(),
	{
		posX: 0,
		posY: 0,
		options: () => [],
	},
);

const emit = defineEmits({
	select: (action: CallableFunction) => action,
	hide: () => true,
});

const visible = ref(false);
const internalPosX = ref(0);
const internalPosY = ref(0);

const currentPosX = computed(() => internalPosX.value || props.posX);
const currentPosY = computed(() => internalPosY.value || props.posY);

watch(visible, (open) => {
	if (!open) emit("hide");
});

const handleClick = (action: CallableFunction) => {
	action();
	emit("select", action);
};

const show = (event: MouseEvent) => {
	internalPosX.value = event.pageX;
	internalPosY.value = event.pageY;
	visible.value = true;
	event.preventDefault();
	event.stopPropagation();
};

const hide = () => {
	visible.value = false;
};

defineExpose({
	show,
	hide,
});
</script>
