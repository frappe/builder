<template>
	<Dialog
		:modelValue="modelValue"
		@update:modelValue="$emit('update:modelValue', $event)"
		:title="isEdit ? model.label || 'Edit Model' : 'New Model'"
		size="lg"
		:actions="[{ label: isEdit ? 'Update' : 'Add', variant: 'solid', onClick: save }]">
		<template #default>
			<div class="flex flex-col gap-4">
				<div class="grid grid-cols-2 gap-4">
					<div class="flex flex-col gap-1.5">
						<InputLabel>Provider</InputLabel>
						<Autocomplete
							:options="providerOptions"
							:modelValue="model.provider"
							@update:modelValue="(value: string | null) => (model.provider = value || '')"
							:allowArbitraryValue="false"
							placeholder="OpenRouter" />
					</div>
					<div class="flex flex-col gap-1.5">
						<InputLabel>Model ID</InputLabel>
						<BuilderInput
							type="text"
							:autofocus="true"
							:modelValue="model.model_id"
							@update:modelValue="(value: string) => (model.model_id = value)"
							placeholder="anthropic/claude-sonnet-5"
							:hideClearButton="true" />
						<p class="text-p-xs text-ink-gray-5">The id at the provider. Becomes {{ preview }}.</p>
					</div>
				</div>
				<div class="flex flex-col gap-1.5">
					<InputLabel>Label</InputLabel>
					<BuilderInput
						type="text"
						:modelValue="model.label"
						@update:modelValue="(value: string) => (model.label = value)"
						placeholder="Claude Sonnet 5"
						:hideClearButton="true" />
				</div>
				<div class="grid grid-cols-3 gap-4">
					<div class="flex flex-col gap-1.5">
						<InputLabel>Context Window</InputLabel>
						<BuilderInput
							type="number"
							:modelValue="model.max_tokens"
							@update:modelValue="(value: string) => (model.max_tokens = Number(value))"
							:hideClearButton="true" />
					</div>
					<div class="flex flex-col gap-1.5">
						<InputLabel>Input $ / 1M</InputLabel>
						<BuilderInput
							type="number"
							:modelValue="model.input_price"
							@update:modelValue="(value: string) => (model.input_price = Number(value))"
							:hideClearButton="true" />
					</div>
					<div class="flex flex-col gap-1.5">
						<InputLabel>Output $ / 1M</InputLabel>
						<BuilderInput
							type="number"
							:modelValue="model.output_price"
							@update:modelValue="(value: string) => (model.output_price = Number(value))"
							:hideClearButton="true" />
					</div>
				</div>
				<p class="text-p-xs text-ink-gray-5">
					OpenRouter models take their live pricing and context window from OpenRouter; these are the
					fallback.
				</p>
				<div class="flex flex-col gap-2">
					<label class="flex items-center gap-2 text-p-sm text-ink-gray-8">
						<Switch
							size="sm"
							:modelValue="Boolean(model.supports_vision)"
							@update:modelValue="(value: boolean) => (model.supports_vision = value ? 1 : 0)" />
						Accepts images
					</label>
					<p class="text-p-xs text-ink-gray-5">
						Leave off unless the model takes image input: sending one to a text-only model fails the turn.
					</p>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import Autocomplete from "@/components/Controls/Autocomplete.vue";
import InputLabel from "@/components/Controls/InputLabel.vue";
import { aiModels, aiProviders, defaultModel } from "@/data/aiModels";
import { BuilderAIModel } from "@/types/doctypes";
import { Dialog, Switch, toast } from "frappe-ui";
import { computed, ref, watch } from "vue";

const props = defineProps<{ modelValue: boolean; model?: BuilderAIModel | null }>();
const emit = defineEmits(["update:modelValue", "saved"]);

const model = ref<Partial<BuilderAIModel>>(defaultModel(""));
const isEdit = computed(() => Boolean(props.model?.name));

const providerOptions = computed(() =>
	(aiProviders.data || []).map((p: any) => ({ label: p.provider_name, value: p.name })),
);

const preview = computed(() => {
	const provider = (aiProviders.data || []).find((p: any) => p.name === model.value.provider);
	return provider ? `${provider.route_prefix}/${model.value.model_id || "…"}` : "…";
});

watch(
	() => props.modelValue,
	(open) => {
		if (!open) return;
		model.value = props.model ? { ...props.model } : defaultModel(providerOptions.value[0]?.value || "");
	},
);

const save = async () => {
	if (!model.value.provider || !model.value.model_id) {
		toast.error("Provider and model id are required");
		return;
	}
	const values = { ...model.value, label: model.value.label || model.value.model_id };
	try {
		if (isEdit.value) {
			await aiModels.setValue.submit({ name: props.model!.name, ...values });
			toast.success("Model updated");
		} else {
			await aiModels.insert.submit(values);
			toast.success("Model added");
		}
		emit("saved");
		emit("update:modelValue", false);
	} catch (error) {
		toast.error((error as Error).message || "Could not save the model");
	}
};
</script>
