<template>
	<div></div>
</template>
<script setup></script>
<style>
@font-face {
	font-family: "InterVar";
	font-weight: 100 900;
	font-display: swap;
	font-style: normal;
	src:
		url("/assets/builder/fonts/Inter/Inter.var.woff2?v=3.19") format("woff2-variations"),
		url("/assets/builder/fonts/Inter/Inter.var.woff2?v=3.19") format("woff2");
	src: url("/assets/builder/fonts/Inter/Inter.var.woff2?v=3.19") format("woff2") tech("variations");
}

@font-face {
	font-family: "InterVar";
	font-weight: 100 900;
	font-display: swap;
	font-style: italic;
	src:
		url("/assets/builder/fonts/Inter/Inter-Italic.var.woff2?v=3.19") format("woff2-variations"),
		url("/assets/builder/fonts/Inter/Inter-Italic.var.woff2?v=3.19") format("woff2");
	src: url("/assets/builder/fonts/Inter/Inter-Italic.var.woff2?v=3.19") format("woff2") tech("variations");
}
@tailwind base;

@layer base {
	ul,
	ol {
		list-style: revert;
		padding: revert;
	}
}

p:empty:before {
	content: "";
	display: inline-block;
}

.__text_block__ {
	overflow-wrap: break-word;
}
.__text_block__ a {
	color: var(--link-color);
	text-decoration: underline;
	background-color: transparent;
}
</style>
