<template>
	<Menu
		v-if="visible"
		class="fixed z-50 h-fit w-fit min-w-[120px] rounded-md bg-surface-white p-1 shadow-xl"
		:style="{ top: y + 'px', left: x + 'px' }"
		ref="menu"
		v-on-click-outside="hide">
		<MenuItems static class="text-sm">
			<MenuItem
				v-slot="{ active, disabled }"
				class="block cursor-pointer rounded-sm px-3 py-1 text-ink-gray-9"
				:disabled="option.disabled && option.disabled()"
				v-for="(option, index) in options"
				v-show="!option.condition || option.condition()">
				<div
					@click.prevent.stop="(!option.condition || option.condition()) && handleClick(option.action)"
					:class="{
						'text-gray-900': !disabled,
						'bg-surface-gray-4': active,
						'!cursor-default !text-ink-gray-4': disabled,
					}">
					{{ option.label }}
				</div>
			</MenuItem>
		</MenuItems>
	</Menu>
</template>
<script setup lang="ts">
import { Menu, MenuItem, MenuItems } from "@headlessui/vue";
import { vOnClickOutside } from "@vueuse/components";
import { computed, ref } from "vue";

const menu = ref(null) as unknown as typeof Menu;

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

const visible = ref(false);
const internalPosX = ref(0);
const internalPosY = ref(0);

const currentPosX = computed(() => internalPosX.value || props.posX);
const currentPosY = computed(() => internalPosY.value || props.posY);

const x = computed(() => {
	const menuWidth = menu.value?.$el.clientWidth;
	const windowWidth = window.innerWidth;
	const diff = windowWidth - (currentPosX.value + menuWidth);
	if (diff < 0) {
		return currentPosX.value + diff - 10;
	}
	return currentPosX.value;
});

const y = computed(() => {
	const menuHeight = menu.value?.$el.clientHeight;
	const windowHeight = window.innerHeight;
	const diff = windowHeight - (currentPosY.value + menuHeight);
	if (diff < 0) {
		return currentPosY.value + diff - 10;
	}
	return currentPosY.value;
});

const emit = defineEmits({
	select: (action: CallableFunction) => action,
	hide: () => true,
});

const handleClick = (action: CallableFunction) => {
	action();
	hide();
	emit("select", action);
};

// Public methods
const show = (event: MouseEvent) => {
	internalPosX.value = event.pageX;
	internalPosY.value = event.pageY;
	visible.value = true;
	event.preventDefault();
	event.stopPropagation();
};

const hide = () => {
	visible.value = false;
	emit("hide");
};

// Expose public methods
defineExpose({
	show,
	hide,
});
</script>
