<template>
	<div class="flex flex-col gap-2">
		<div class="flex h-6 items-center justify-between">
			<div class="flex items-center gap-2">
				<label class="text-[10px] font-bold uppercase tracking-[0.1em] text-ink-gray-4">
					{{ modelValue ? "Style" : "Design Style" }}
				</label>
				<div v-if="modelValue" class="flex items-center gap-1.5">
					<div
						class="flex items-center gap-1.5 rounded-md bg-surface-gray-2 px-2 py-0.5 ring-1 ring-inset ring-outline-gray-2">
						<span class="text-[10px] font-bold uppercase text-ink-gray-9">
							{{ modelValue.name }}
						</span>
						<button
							class="text-ink-gray-4 transition-colors hover:text-ink-gray-9"
							@click="$emit('update:modelValue', null)"
							title="Clear style selection">
							<FeatherIcon name="x" class="size-3" />
						</button>
					</div>
				</div>
			</div>
		</div>

		<!-- Category Filter -->
		<div class="pb-2 pt-0.5">
			<TabButtons v-model="selectedCategory" :buttons="CATEGORIES" />
		</div>

		<div class="grid grid-cols-2 gap-3 sm:grid-cols-3">
			<button
				v-for="preset in filteredPresets"
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
							<div class="rounded-lg bg-blue-200"></div>
							<div class="rounded-md bg-orange-200"></div>
							<div class="rounded-md bg-violet-200"></div>
							<div class="rounded-xl bg-pink-200"></div>
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
						<div class="h-1 w-3/5 rounded-full bg-blue-200 opacity-40"></div>
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

					<!-- Cyber Punk -->
					<template v-else-if="preset.id === 'cyber-punk'">
						<div
							class="absolute inset-0 opacity-10"
							style="
								background-image: radial-gradient(circle at 2px 2px, #00f2ff 1px, transparent 0);
								background-size: 10px 10px;
							"></div>
						<div class="relative z-10 flex flex-col gap-1.5 pt-1">
							<div class="h-1.5 w-4/5 border-l-2 border-cyan-400 bg-cyan-400/10 px-1"></div>
							<div class="h-1.5 w-1/2 border-l-2 border-blue-500 bg-blue-500/10 px-1"></div>
							<div class="mt-1 h-3.5 w-full border border-cyan-400/50 bg-cyan-400/5">
								<div class="h-full w-1/3 bg-cyan-400/40"></div>
							</div>
						</div>
					</template>

					<!-- Paper & Ink -->
					<template v-else-if="preset.id === 'paper-print'">
						<div
							class="absolute inset-0 opacity-20"
							style="
								background-image: url(&quot;data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%224%22 height=%224%22 viewBox=%220 0 4 4%22%3E%3Cpath fill=%22%23000%22 fill-opacity=%220.4%22 d=%22M1 3h1v1H1V3zm2-2h1v1H3V1z%22%3E%3C/path%3E%3C/svg%3E&quot;);
							"></div>
						<div class="relative border-b border-orange-200 py-1">
							<div class="h-2 w-3/4 bg-gray-900"></div>
						</div>
						<div class="mt-1 space-y-1">
							<div class="h-1 w-full bg-gray-600/60"></div>
							<div class="h-1 w-5/6 bg-gray-600/60"></div>
						</div>
						<div class="mt-auto flex justify-end">
							<div class="h-3 w-3 rounded-full border border-gray-900"></div>
						</div>
					</template>

					<!-- Playful Pastel -->
					<template v-else-if="preset.id === 'playful-pastel'">
						<div class="absolute -right-2 -top-2 h-12 w-12 rounded-full bg-blue-200/50"></div>
						<div class="absolute -bottom-4 -left-2 h-10 w-10 rounded-full bg-yellow-200/50"></div>
						<div class="relative flex flex-col gap-1.5">
							<div class="h-3 w-3/4 rounded-full bg-pink-400"></div>
							<div class="h-4 w-1/2 rounded-full border-2 border-pink-400 bg-white"></div>
						</div>
					</template>

					<!-- Industrial Mono -->
					<template v-else-if="preset.id === 'industrial-mono'">
						<div
							class="absolute inset-0 opacity-10"
							style="
								background-image: linear-gradient(#fff 1px, transparent 1px),
									linear-gradient(90deg, #fff 1px, transparent 1px);
								background-size: 8px 8px;
							"></div>
						<div class="relative flex flex-col gap-2 p-1">
							<div class="h-0.5 w-full bg-white opacity-20"></div>
							<div class="flex items-center gap-2">
								<div class="h-4 w-4 border border-white opacity-40"></div>
								<div class="h-2 w-12 bg-white opacity-60"></div>
							</div>
							<div class="h-0.5 w-full bg-white opacity-20"></div>
						</div>
					</template>

					<!-- Cosmic Nebula -->
					<template v-else-if="preset.id === 'cosmic-nebula'">
						<div
							class="absolute inset-0"
							style="
								background: radial-gradient(circle at 70% 30%, #4c1d95 0%, transparent 70%),
									radial-gradient(circle at 20% 80%, #1e40af 0%, transparent 70%);
							"></div>
						<div
							class="absolute inset-0 opacity-20"
							style="
								background-image: radial-gradient(circle at 1px 1px, white 0.5px, transparent 0);
								background-size: 8px 8px;
							"></div>
						<div class="relative z-10 flex flex-col gap-1.5">
							<div class="h-2 w-2/3 rounded-full bg-white/20 backdrop-blur-sm"></div>
							<div class="h-1.5 w-1/2 rounded-full bg-white/10"></div>
							<div
								class="mt-1 h-3 w-1/3 rounded-full bg-blue-500/60 shadow-[0_0_8px_rgba(99,102,241,0.5)]"></div>
						</div>
					</template>

					<!-- Synthwave Neon -->
					<template v-else-if="preset.id === 'synthwave'">
						<div
							class="absolute inset-0"
							style="
								background: linear-gradient(0deg, #2d0b5a 0%, #0d0221 100%);
								background-image: linear-gradient(rgba(255, 0, 255, 0.1) 1px, transparent 1px),
									linear-gradient(90deg, rgba(255, 0, 255, 0.1) 1px, transparent 1px);
								background-size: 15px 15px;
								background-position: center bottom;
								perspective: 100px;
							"></div>
						<div
							class="absolute -bottom-2 -left-2 h-16 w-16 rounded-full bg-gradient-to-t from-orange-500/40 to-pink-500/40 blur-md"></div>
						<div class="relative z-10 flex flex-col gap-1.5">
							<div class="h-1.5 w-3/4 bg-cyan-400 shadow-[0_0_5px_#22d3ee]"></div>
							<div class="h-1 w-1/2 bg-blue-400 shadow-[0_0_5px_#e879f9]"></div>
						</div>
					</template>

					<!-- Sketch Book -->
					<template v-else-if="preset.id === 'sketch-book'">
						<div
							class="absolute inset-0"
							style="
								background-image: radial-gradient(#d1d5db 0.5px, transparent 0.5px);
								background-size: 10px 10px;
							"></div>
						<div class="relative flex flex-col gap-2 pt-1">
							<div
								class="h-3 w-4/5 border-2 border-gray-800 bg-white"
								style="border-radius: 2px 8px 3px 6px"></div>
							<div class="h-1 w-full border-b border-gray-400"></div>
							<div class="h-1 w-2/3 border-b border-gray-400"></div>
							<div
								class="absolute -right-1 bottom-0 h-4 w-4 border-2 border-dashed border-gray-400"
								style="transform: rotate(5deg)"></div>
						</div>
					</template>

					<!-- Holographic -->
					<template v-else-if="preset.id === 'holographic'">
						<div
							class="absolute inset-0"
							style="
								background: linear-gradient(
									135deg,
									#e0f2fe 0%,
									#fdf2f8 25%,
									#f5f3ff 50%,
									#ecfdf5 75%,
									#fff7ed 100%
								);
								filter: saturate(3);
							"></div>
						<div class="relative flex flex-col gap-1.5">
							<div class="h-3 w-3/4 rounded-lg bg-white/80 ring-1 ring-blue-300/60 backdrop-blur-md"></div>
							<div class="h-1.5 w-1/2 rounded-full bg-white/30 backdrop-blur-sm"></div>
							<div
								class="mt-1 h-4 w-1/3 rounded-lg border border-white/80 bg-gradient-to-br from-white/60 to-transparent shadow-sm"></div>
						</div>
					</template>

					<!-- Claymorphism -->
					<template v-else-if="preset.id === 'claymorphism'">
						<div
							class="absolute bottom-2 right-2 h-10 w-10 rounded-full"
							style="
								background: radial-gradient(circle at 30% 30%, #d8d4f0, #bdb8e8);
								filter: blur(10px);
								opacity: 0.5;
							"></div>

						<div class="relative flex flex-col gap-3 pt-1">
							<div
								class="h-4 w-4/5 rounded-2xl"
								style="
									background: linear-gradient(135deg, #ede9fa 0%, #d4ceef 100%);
									box-shadow:
										6px 6px 14px #c8c2e844,
										-6px -6px 14px #ffffff,
										inset 2px 2px 5px rgba(255, 255, 255, 0.95),
										inset -2px -2px 5px rgba(139, 120, 200, 0.08);
								"></div>

							<div
								class="h-6 w-1/2 rounded-full"
								style="
									background: linear-gradient(135deg, #d4eee3 0%, #b8dece 100%);
									box-shadow:
										5px 5px 12px #aed4c044,
										-5px -5px 12px #ffffff,
										inset 3px 3px 7px rgba(255, 255, 255, 0.9),
										inset -3px -3px 7px rgba(80, 160, 120, 0.08);
								"></div>
						</div>
					</template>

					<!-- Blueprint -->
					<template v-else-if="preset.id === 'blueprint'">
						<div
							class="absolute inset-0"
							style="
								background-color: #0c3a6e;
								background-image: linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px),
									linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px);
								background-size: 10px 10px;
							"></div>
						<div class="relative flex flex-col gap-1.5 border-l border-white/20 pl-2">
							<div class="h-2 w-3/4 border-b border-t border-white/40 bg-white/5"></div>
							<div class="flex items-center gap-1">
								<div class="h-1.5 w-1.5 border border-white/60"></div>
								<div class="h-0.5 w-12 bg-white/40"></div>
							</div>
							<div class="h-px w-full bg-white/10"></div>
							<div class="h-1 w-1/3 bg-white/30"></div>
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
	category: string;
	description: string;
	icon: string;
	preview?: PresetPreview;
}

const PRESETS: Preset[] = [
	{
		id: "aurora-glass",
		name: "Aurora Glass",
		category: "modern",
		description:
			"Deep dark backgrounds with vibrant aurora-inspired gradients, glassmorphism cards with blur/translucency, and glowing blobs. Ultra-modern and immersive.",
		icon: "aperture",
		preview: {
			bg: "bg-gray-900",
			blobA: "bg-purple-600",
			blobB: "bg-blue-700",
		},
	},
	{
		id: "bento",
		name: "Bento Grid",
		category: "modern",
		description:
			"Modular bento-box grid layouts with varied tile sizes, and generous rounded corners. Each section is a self-contained card. Inspired by Japanese bento compartments — clean, playful, highly structured.",
		icon: "grid",
		preview: {
			bg: "bg-gray-50",
		},
	},
	{
		id: "neo-brutalist",
		name: "Neo-Brutalist",
		category: "retro",
		description:
			"Raw, unapologetic design with heavy borders, bold offset shadows, and chunky typography. Intentionally rough and high-contrast. No gradients, no subtlety.",
		icon: "bold",
		preview: {
			bg: "bg-white",
		},
	},
	{
		id: "soft-glow",
		name: "Soft Glow",
		category: "modern",
		description:
			"Dreamy gradients, soft glow halos, pill-shaped buttons, and rounded fluid shapes. Light and airy — think Figma landing pages and modern SaaS products with a fresh, inviting feel.",
		icon: "sun",
		preview: {
			bg: "bg-purple-100",
		},
	},
	{
		id: "minimal-ink",
		name: "Minimal Ink",
		category: "minimal",
		description:
			"Absolute restraint — hairline borders, sparse layout. Typography does all the work. Inspired by Swiss editorial design and Japanese stationery brands. Zero decoration.",
		icon: "feather",
		preview: {
			bg: "bg-gray-100",
		},
	},
	{
		id: "earthy",
		name: "Earthy Organic",
		category: "minimal",
		description:
			"Organic shapes, natural textures, and rounded asymmetric forms. Grounded and tactile — ideal for wellness, food, craft, and sustainability brands.",
		icon: "coffee",
		preview: {
			bg: "bg-red-100",
		},
	},
	{
		id: "tech-terminal",
		name: "Tech Terminal",
		category: "tech",
		description:
			"Dark background with monospace typography, terminal-style chrome, and code-aesthetic UI. Think developer tools, CLI apps, and hacker-culture interfaces.",
		icon: "terminal",
		preview: {
			bg: "bg-gray-900",
		},
	},
	{
		id: "luxe-editorial",
		name: "Luxe Editorial",
		category: "minimal",
		description:
			"Thin serif typefaces, and refined negative space. Understated luxury — think high-fashion magazines and premium brand campaigns.",
		icon: "star",
		preview: {
			bg: "bg-gray-800",
		},
	},
	{
		id: "bold-retro",
		name: "Bold Retro",
		category: "retro",
		description:
			"Thick borders, chunky chart bars, flat graphic shapes, and retro poster energy. Bold and high-contrast, inspired by 90s print graphics and risograph aesthetics.",
		icon: "zap",
		preview: {
			bg: "bg-yellow-100",
		},
	},
	{
		id: "cyber-punk",
		name: "Futuristic Cyber",
		category: "tech",
		description:
			"High-visibility neon accents against deep obsidian backgrounds. Glowing borders, scanning lines, and tech-heavy interfaces with futuristic energy.",
		icon: "cpu",
		preview: {
			bg: "bg-black",
		},
	},
	{
		id: "paper-print",
		name: "Paper & Ink",
		category: "minimal",
		description:
			"Warm, textured paper backgrounds with high-contrast ink-like typography. Tactile and organic, inspired by letterpress printing and boutique stationery.",
		icon: "book-open",
		preview: {
			bg: "bg-orange-50",
		},
	},
	{
		id: "playful-pastel",
		name: "Playful Pastel",
		category: "modern",
		description:
			"Soft candy-colored palettes, organic wiggly shapes, and pill-shaped rounded buttons. Bouncy, cheerful, and approachable for consumer-friendly apps.",
		icon: "smile",
		preview: {
			bg: "bg-pink-50",
		},
	},
	{
		id: "industrial-mono",
		name: "Industrial Mono",
		category: "tech",
		description:
			"Raw, high-contrast monochrome with technical grid backgrounds and utility-first layouts. Rugged, functional, and inspired by architectural blueprints.",
		icon: "box",
		preview: {
			bg: "bg-zinc-900",
		},
	},
	{
		id: "cosmic-nebula",
		name: "Cosmic Nebula",
		category: "tech",
		description:
			"Deep space aesthetics with swirling stellar clouds, star-fields, and floating translucent elements. Magical, expansive, and ethereal.",
		icon: "cloud",
		preview: {
			bg: "bg-zinc-900",
		},
	},
	{
		id: "synthwave",
		name: "Synthwave Neon",
		category: "retro",
		description:
			"80s retro-futurism with glowing grid floors, vibrant sun-gradient headers, and high-contrast pink and purple neon accents. Retro-digital aesthetic.",
		icon: "sun",
		preview: {
			bg: "bg-purple-900",
		},
	},
	{
		id: "sketch-book",
		name: "Sketch Book",
		category: "minimal",
		description:
			"Hand-drawn pencil lines, rough scribbled borders, and graphite textures. Creative and raw artistic feel, as if sketched in a physical notebook.",
		icon: "edit-3",
		preview: {
			bg: "bg-gray-100",
		},
	},
	{
		id: "holographic",
		name: "Holographic",
		category: "modern",
		description:
			"Iridescent color-shifting surfaces, holographic overlays, and translucent frosted glass. Ethereal, modern, and shimmering with light.",
		icon: "layers",
		preview: {
			bg: "bg-blue-100",
		},
	},
	{
		id: "claymorphism",
		name: "Organic Clay",
		category: "modern",
		description:
			"Soft, pillowy surfaces with deep inner shadows and outer glows. Friendly, tactile, and highly rounded shapes. Modern 3D 'clay' look.",
		icon: "box",
		preview: {
			bg: "bg-blue-100",
		},
	},
	{
		id: "blueprint",
		name: "Technical Blueprint",
		category: "tech",
		description:
			"Deep architectural blue backgrounds with fine white grid lines and technical drafting annotations. Precise, structural, and professional.",
		icon: "map",
		preview: {
			bg: "bg-blue-900",
		},
	},
];

import TabButtons from "@/components/Controls/TabButtons.vue";
import { FeatherIcon } from "frappe-ui";
import { computed, ref } from "vue";

const CATEGORIES = [
	{ label: "Modern", value: "modern" },
	{ label: "Minimal", value: "minimal" },
	{ label: "Technical", value: "tech" },
	{ label: "Retro", value: "retro" },
];

const selectedCategory = ref("modern");

const filteredPresets = computed(() => {
	return PRESETS.filter((p) => p.category === selectedCategory.value);
});

defineProps<{
	modelValue: Preset | null;
}>();

defineEmits<{
	(e: "update:modelValue", value: Preset | null): void;
}>();
</script>
