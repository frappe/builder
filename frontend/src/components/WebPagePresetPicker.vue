<template>
	<div class="flex flex-col gap-2">
		<div class="flex items-center justify-between">
			<label class="text-xs font-medium uppercase tracking-wider text-ink-gray-5">Design Style</label>
			<button
				v-if="modelValue"
				class="text-xs text-ink-gray-5 hover:text-ink-gray-9"
				@click="$emit('update:modelValue', null)">
				Clear
			</button>
		</div>
		<div class="grid grid-cols-2 gap-3 sm:grid-cols-3">
			<button
				v-for="preset in PRESETS"
				:key="preset.id"
				class="group relative flex flex-col items-center gap-2 rounded-xl border p-2 outline-none transition-all duration-200"
				:class="
					modelValue?.id === preset.id
						? 'border-outline-gray-9 shadow-md ring-2 ring-outline-gray-5'
						: 'border-outline-gray-2 bg-surface-white hover:border-outline-gray-4 hover:shadow-sm'
				"
				@click="$emit('update:modelValue', preset)">
				<!-- Preview -->
				<div
					class="relative flex h-16 w-full flex-col gap-1.5 overflow-hidden rounded-lg p-2 transition-transform"
					:class="preset?.preview?.bg">
					<!-- Aurora Glass -->
					<template v-if="preset.id === 'aurora-glass'">
						<div
							class="absolute -left-3 -top-3 h-10 w-10 rounded-full opacity-60"
							:class="preset?.preview?.blobA"
							style="filter: blur(8px)"></div>
						<div
							class="absolute -bottom-2 right-1 h-8 w-8 rounded-full opacity-40"
							:class="preset?.preview?.blobB"
							style="filter: blur(6px)"></div>
						<div class="relative z-10 flex flex-col gap-1.5 pt-1">
							<div class="h-2 w-3/4 rounded-full border border-white/10 bg-white opacity-15"></div>
							<div class="h-1.5 w-1/2 rounded-full bg-white opacity-10"></div>
							<div
								class="mt-0.5 h-3.5 w-2/5 rounded-md border border-white/20"
								style="
									background: linear-gradient(90deg, rgba(139, 92, 246, 0.7), rgba(6, 182, 212, 0.7));
								"></div>
						</div>
					</template>

					<!-- Bento Grid -->
					<template v-else-if="preset.id === 'bento'">
						<div class="grid h-full w-full grid-cols-2 grid-rows-2 gap-1">
							<div class="bg-indigo-100 rounded-lg"></div>
							<div class="rounded-md bg-amber-100"></div>
							<div class="bg-emerald-100 rounded-md"></div>
							<div class="rounded-xl bg-pink-100"></div>
						</div>
					</template>

					<!-- Neo-Brutalist -->
					<template v-else-if="preset.id === 'neo-brutalist'">
						<div class="absolute inset-x-0 top-0 flex h-6 items-center bg-black px-2">
							<div class="h-1.5 w-1/3 rounded-sm bg-yellow-300"></div>
						</div>
						<div class="mt-6 flex flex-col gap-1">
							<div class="h-1.5 w-3/5 rounded-sm bg-black"></div>
							<div class="h-1.5 w-2/5 rounded-sm border-2 border-black bg-transparent"></div>
						</div>
					</template>

					<!-- Soft Glow -->
					<template v-else-if="preset.id === 'soft-glow'">
						<div
							class="absolute bottom-0 right-0 h-12 w-12 rounded-full bg-purple-500 opacity-20"
							style="filter: blur(10px)"></div>
						<div
							class="h-2 w-2/3 rounded-full"
							style="background: linear-gradient(90deg, #a855f7, #818cf8)"></div>
						<div class="h-1 w-1/2 rounded-full bg-purple-300 opacity-50"></div>
						<div class="bg-indigo-200 h-1 w-3/5 rounded-full opacity-40"></div>
						<div
							class="mt-1 h-3 w-2/5 rounded-full"
							style="background: linear-gradient(90deg, #a855f7, #818cf8); opacity: 0.85"></div>
					</template>

					<!-- Minimal Ink -->
					<template v-else-if="preset.id === 'minimal-ink'">
						<div class="h-px w-full bg-gray-200"></div>
						<div class="flex items-center gap-1.5 py-1">
							<div class="h-4 w-4 flex-shrink-0 rounded border-2 border-gray-800"></div>
							<div class="h-1.5 w-2/5 rounded-sm bg-gray-800"></div>
						</div>
						<div class="h-px w-full bg-gray-200"></div>
						<div class="h-1 w-1/3 rounded-sm bg-gray-300"></div>
					</template>

					<!-- Earthy Organic -->
					<template v-else-if="preset.id === 'earthy'">
						<div class="absolute -right-2 -top-2 h-10 w-10 rounded-full bg-amber-300 opacity-30"></div>
						<div class="h-2 w-3/5 rounded-xl rounded-l-none bg-amber-800 opacity-80"></div>
						<div class="h-1 w-4/5 rounded bg-amber-500 opacity-50"></div>
						<div class="h-1 w-1/2 rounded bg-amber-700 opacity-40"></div>
						<div class="mt-1 flex gap-1">
							<div class="h-3 w-1/3 rounded-full bg-amber-800 opacity-70"></div>
							<div class="h-3 w-1/4 rounded-full bg-amber-500 opacity-50"></div>
						</div>
					</template>

					<!-- Tech Terminal -->
					<template v-else-if="preset.id === 'tech-terminal'">
						<div class="mb-1 flex gap-1">
							<div class="h-1.5 w-1.5 rounded-full bg-red-500"></div>
							<div class="h-1.5 w-1.5 rounded-full bg-yellow-400"></div>
							<div class="h-1.5 w-1.5 rounded-full bg-green-400"></div>
						</div>
						<div class="h-1.5 w-2/5 rounded-sm bg-green-400 opacity-90"></div>
						<div class="h-1 w-3/5 rounded-sm bg-green-400 opacity-35"></div>
						<div class="h-1 w-1/2 rounded-sm bg-green-400 opacity-25"></div>
						<div class="h-1.5 w-4 animate-pulse rounded-sm bg-green-400 opacity-70"></div>
					</template>

					<!-- Luxe Editorial -->
					<template v-else-if="preset.id === 'luxe-editorial'">
						<div
							class="absolute bottom-0 left-0 top-0 w-0.5"
							style="background: linear-gradient(180deg, #b8860b, #ffd700, #b8860b)"></div>
						<div class="flex h-full flex-col justify-center gap-1.5 pl-3">
							<div class="h-1.5 w-4/5 rounded-sm bg-yellow-300 opacity-90"></div>
							<div class="h-px w-full bg-yellow-300 opacity-20"></div>
							<div class="h-1 w-3/5 rounded-sm bg-yellow-200 opacity-50"></div>
							<div class="h-1 w-2/5 rounded-sm bg-yellow-200 opacity-30"></div>
						</div>
					</template>

					<!-- Bold Retro -->
					<template v-else-if="preset.id === 'bold-retro'">
						<div class="pointer-events-none absolute inset-0 rounded-lg border-2 border-black"></div>
						<div class="flex h-4 w-full items-center rounded-sm bg-black px-1.5">
							<div class="h-1.5 w-8 rounded-sm bg-yellow-300"></div>
						</div>
						<div class="flex flex-1 items-end gap-0.5">
							<div class="h-full flex-1 rounded-t-sm bg-red-500"></div>
							<div class="flex-1 rounded-t-sm bg-black" style="height: 60%"></div>
							<div class="flex-1 rounded-t-sm bg-red-500" style="height: 75%"></div>
							<div class="flex-1 rounded-t-sm bg-black" style="height: 35%"></div>
							<div class="flex-1 rounded-t-sm bg-red-500" style="height: 88%"></div>
						</div>
					</template>
				</div>

				<!-- Label -->
				<div class="flex flex-col items-center gap-0.5 px-0.5">
					<span class="text-[11px] font-semibold leading-tight text-ink-gray-9">
						{{ preset.name }}
					</span>
				</div>
			</button>
		</div>
	</div>
</template>

<script setup lang="ts">
interface PresetPreview {
	bg: string;
	accent?: string;
	blobA?: string;
	blobB?: string;
}

interface Preset {
	id: string;
	name: string;
	description: string;
	icon: string;
	preview?: PresetPreview;
}

const PRESETS: Preset[] = [
	{
		id: "aurora-glass",
		name: "Aurora Glass",
		description:
			"Deep dark backgrounds with vibrant aurora-inspired gradients, glassmorphism cards with blur/translucency, glowing color blobs, and rich purple/cyan/violet palettes. Ultra-modern and immersive.",
		icon: "aperture",
		preview: {
			bg: "bg-ink-gray-9",
			blobA: "bg-ink-purple-6",
			blobB: "bg-ink-blue-7",
		},
	},
	{
		id: "bento",
		name: "Bento Grid",
		description:
			"Modular bento-box grid layouts with varied tile sizes, soft pastel fills, and generous rounded corners. Each section is a self-contained card. Inspired by Japanese bento compartments — clean, playful, highly structured.",
		icon: "grid",
		preview: {
			bg: "bg-surface-gray-1",
		},
	},
	{
		id: "neo-brutalist",
		name: "Neo-Brutalist",
		description:
			"Raw, unapologetic design with heavy black borders, stark white/yellow backgrounds, bold offset shadows, and chunky typography. Intentionally rough and high-contrast. No gradients, no subtlety.",
		icon: "bold",
		preview: {
			bg: "bg-surface-white",
		},
	},
	{
		id: "soft-glow",
		name: "Soft Glow",
		description:
			"Dreamy pastel gradients (lavender, rose, sky), soft glow halos, pill-shaped buttons, and rounded fluid shapes. Light and airy — think Figma landing pages and modern SaaS products with a fresh, inviting feel.",
		icon: "sun",
		preview: {
			bg: "bg-surface-purple-1",
		},
	},
	{
		id: "minimal-ink",
		name: "Minimal Ink",
		description:
			"Absolute restraint — off-white backgrounds, hairline borders, sparse layout. Typography does all the work. Inspired by Swiss editorial design and Japanese stationery brands. Zero decoration.",
		icon: "feather",
		preview: {
			bg: "bg-surface-gray-1",
		},
	},
	{
		id: "earthy",
		name: "Earthy Organic",
		description:
			"Warm terracotta, sand, sage, and clay tones with organic shapes, natural textures, and rounded asymmetric forms. Grounded and tactile — ideal for wellness, food, craft, and sustainability brands.",
		icon: "coffee",
		preview: {
			bg: "bg-surface-red-1",
		},
	},
	{
		id: "tech-terminal",
		name: "Tech Terminal",
		description:
			"Dark background with monospace typography, neon green accent colors, terminal-style chrome, and code-aesthetic UI. Think developer tools, CLI apps, and hacker-culture interfaces.",
		icon: "terminal",
		preview: {
			bg: "bg-ink-gray-9",
		},
	},
	{
		id: "luxe-editorial",
		name: "Luxe Editorial",
		description:
			"Deep charcoal or navy backgrounds with gold/champagne accents, thin serif typefaces, and refined negative space. Understated luxury — think high-fashion magazines and premium brand campaigns.",
		icon: "star",
		preview: {
			bg: "bg-ink-gray-8",
		},
	},
	{
		id: "bold-retro",
		name: "Bold Retro",
		description:
			"Vibrant primary colors (red, yellow, black), thick borders, chunky chart bars, flat graphic shapes, and retro poster energy. Bold and high-contrast, inspired by 90s print graphics and risograph aesthetics.",
		icon: "zap",
		preview: {
			bg: "bg-surface-yellow-1",
		},
	},
];

defineProps<{
	modelValue: Preset | null;
}>();

defineEmits<{
	(e: "update:modelValue", value: Preset | null): void;
}>();
</script>
