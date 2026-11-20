<template>
	<div class="flex flex-col gap-3">
		<div class="flex flex-col gap-1">
			<span class="text-md-semibold text-ink-gray-9">{{ __("Providers") }}</span>
			<span class="text-p-sm text-ink-gray-5">{{ __("Bob uses the models of the providers you add.") }}</span>
		</div>

		<div v-if="!aiProviders.data" class="flex justify-center py-6">
			<LoadingIndicator class="size-4 text-ink-gray-4" />
		</div>
		<!-- one provider open at a time. The negative margin lines the names up with the heading -->
		<AccordionRoot
			v-else-if="aiProviders.data.length"
			v-model="openProvider"
			type="single"
			collapsible
			class="-mx-2 flex flex-col">
			<AccordionItem
				v-for="provider in aiProviders.data as BuilderAIProvider[]"
				:key="provider.name"
				v-slot="{ open }"
				:value="provider.name"
				class="border-b border-outline-gray-1 last:border-b-0">
				<AccordionHeader class="flex items-center gap-2 rounded-4 px-2 py-2 hover:bg-surface-gray-1">
					<!-- greyed with its content while off. The switch stays clear, as it turns the provider on -->
					<AccordionTrigger
						class="flex min-w-0 flex-1 items-center gap-2 text-left"
						:class="!provider.enabled && 'opacity-60'">
						<span
							class="lucide-chevron-right size-4 shrink-0 text-ink-gray-5 transition-transform"
							:class="open && 'rotate-90'"
							aria-hidden="true" />
						<div class="flex min-w-0 flex-col">
							<span class="truncate text-base text-ink-gray-8">{{ provider.provider_name }}</span>
							<span class="truncate text-p-sm text-ink-gray-5">{{ summary(provider) }}</span>
						</div>
					</AccordionTrigger>
					<Badge
						v-if="provider.enabled && isLow(provider.name)"
						:theme="creditsTheme(credits[provider.name]!)"
						:label="creditsLabel(credits[provider.name])" />
					<Switch
						:model-value="Boolean(provider.enabled)"
						:aria-label="__('Use {0}', [provider.provider_name])"
						@update:model-value="(on: boolean) => setEnabled(provider.name, on)" />
				</AccordionHeader>
				<AccordionContent class="mb-3 ml-8 mr-2 pt-1">
					<ProviderDetails :provider="provider" @changed="refresh" />
				</AccordionContent>
			</AccordionItem>
		</AccordionRoot>

		<AddProvider @connected="refresh" />
	</div>
</template>

<script setup lang="ts">
import { creditsFor, creditsLabel, creditsTheme, type Credits } from "@/components/ai/commands/shared";
import AddProvider from "@/components/Settings/AI/AddProvider.vue";
import ProviderDetails from "@/components/Settings/AI/ProviderDetails.vue";
import { aiProviders, listedModelsOf, reloadAIRegistry, setProviderEnabled } from "@/data/aiModels";
import useBuilderStore from "@/stores/builderStore";
import { __ } from "@/translation";
import type { BuilderAIProvider } from "@/types/doctypes";
import { Badge, LoadingIndicator, Switch } from "frappe-ui";
import { AccordionContent, AccordionHeader, AccordionItem, AccordionRoot, AccordionTrigger } from "reka-ui";
import { onMounted, ref } from "vue";

const builderStore = useBuilderStore();
const credits = ref<Record<string, Credits | null>>({});
const openProvider = ref<string>();

const refresh = async () => {
	await reloadAIRegistry();
	await builderStore.refreshAIState();
	// a gateway slow to report its balance must not hold up the list
	const gateways = (aiProviders.data || []).filter((p: BuilderAIProvider) => p.api_base);
	creditsFor(gateways.map((p: BuilderAIProvider) => p.name))
		.then((found) => (credits.value = found))
		.catch(() => null);
};
onMounted(refresh);

const setEnabled = async (name: string, on: boolean) => {
	await setProviderEnabled(name, on);
	await refresh();
};

// the balance sits with the model count, and turns into a badge once it runs low
const isLow = (name: string) => !!credits.value[name] && creditsTheme(credits.value[name]!) !== "gray";
const summary = (provider: BuilderAIProvider) => {
	const count = listedModelsOf(provider.name).filter((m) => m.enabled).length;
	const models = count === 1 ? __("1 model") : __("{0} models", [count]);
	const balance = isLow(provider.name) ? undefined : creditsLabel(credits.value[provider.name]);
	return [models, balance].filter(Boolean).join(" · ");
};
</script>
