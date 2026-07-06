<template>
	<!-- A living aurora rendered by a tiny WebGL shader: domain-warped fbm noise
	     driving a shifting violet→magenta→cyan palette with true alpha translucency.
	     Falls back to a CSS gradient if WebGL is unavailable. Pure decoration. -->
	<canvas ref="canvas" class="bob-orb-gl" aria-hidden="true" />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";

const canvas = ref<HTMLCanvasElement | null>(null);
let gl: WebGLRenderingContext | null = null;
let program: WebGLProgram | null = null;
let raf = 0;
let startedAt = 0;
let uTime: WebGLUniformLocation | null = null;
let ro: ResizeObserver | null = null;
let reduceMotion = false;

const VERT = `
attribute vec2 a_pos;
varying vec2 v_uv;
void main() {
	v_uv = a_pos * 0.5 + 0.5;
	gl_Position = vec4(a_pos, 0.0, 1.0);
}`;

// Domain-warped value-noise fbm → soft flowing bands. Colors shift with both the
// noise field and time, so the palette never sits still. Alpha falls off to a
// circle and scales with the field, so it's translucent, not a solid disc.
const FRAG = `
precision highp float;
uniform float u_time;
varying vec2 v_uv;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
	           mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}
float fbm(vec2 p) {
	float v = 0.0, a = 0.5;
	for (int i = 0; i < 5; i++) { v += a * noise(p); p *= 2.0; a *= 0.5; }
	return v;
}
void main() {
	vec2 uv = v_uv * 2.0 - 1.0;
	float r = length(uv);
	float t = u_time * 0.22;

	vec2 q = vec2(fbm(uv * 1.7 + t), fbm(uv * 1.7 - t + 4.3));
	float n = fbm(uv * 2.1 + q * 1.8 + vec2(0.0, t));
	n = clamp(n + 0.10 * sin(t * 1.4), 0.0, 1.0);
	n = clamp((n - 0.5) * 1.55 + 0.5, 0.0, 1.0); // stretch contrast around mid

	vec3 blueDeep  = vec3(0.12, 0.23, 0.54); // navy
	vec3 blueRoyal = vec3(0.31, 0.27, 0.90); // royal blue
	vec3 violet    = vec3(0.49, 0.23, 0.93); // violet
	vec3 lilac     = vec3(0.75, 0.52, 0.99); // lilac core
	vec3 col = mix(blueDeep, blueRoyal, smoothstep(0.22, 0.46, n));
	col = mix(col, violet, smoothstep(0.46, 0.68, n));
	col = mix(col, lilac, smoothstep(0.70, 0.93, n));
	col *= 0.82 + 0.55 * n; // brighter highs → punchier bands

	float mask = smoothstep(1.0, 0.16, r);
	float alpha = mask * (0.10 + 0.9 * pow(n, 1.5)); // darker lows → more contrast
	gl_FragColor = vec4(col, alpha * 0.95);
}`;

function compile(g: WebGLRenderingContext, type: number, src: string): WebGLShader | null {
	const sh = g.createShader(type);
	if (!sh) return null;
	g.shaderSource(sh, src);
	g.compileShader(sh);
	if (!g.getShaderParameter(sh, g.COMPILE_STATUS)) {
		g.deleteShader(sh);
		return null;
	}
	return sh;
}

function init(): boolean {
	const el = canvas.value;
	if (!el) return false;
	gl = (el.getContext("webgl", { premultipliedAlpha: false, alpha: true, antialias: true }) ||
		el.getContext("experimental-webgl", {
			premultipliedAlpha: false,
			alpha: true,
		})) as WebGLRenderingContext | null;
	if (!gl) return false;

	const vs = compile(gl, gl.VERTEX_SHADER, VERT);
	const fs = compile(gl, gl.FRAGMENT_SHADER, FRAG);
	if (!vs || !fs) return false;
	program = gl.createProgram();
	if (!program) return false;
	gl.attachShader(program, vs);
	gl.attachShader(program, fs);
	gl.linkProgram(program);
	if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return false;
	gl.useProgram(program);

	const buf = gl.createBuffer();
	gl.bindBuffer(gl.ARRAY_BUFFER, buf);
	gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
	const loc = gl.getAttribLocation(program, "a_pos");
	gl.enableVertexAttribArray(loc);
	gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

	gl.enable(gl.BLEND);
	gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
	uTime = gl.getUniformLocation(program, "u_time");
	return true;
}

function resize() {
	const el = canvas.value;
	if (!el || !gl) return;
	const dpr = Math.min(window.devicePixelRatio || 1, 2);
	const w = Math.max(1, Math.round(el.clientWidth * dpr));
	const h = Math.max(1, Math.round(el.clientHeight * dpr));
	if (el.width !== w || el.height !== h) {
		el.width = w;
		el.height = h;
		gl.viewport(0, 0, w, h);
	}
}

function frame(now: number) {
	if (!gl || !program) return;
	if (!startedAt) startedAt = now;
	resize();
	gl.uniform1f(uTime, (now - startedAt) / 1000);
	gl.drawArrays(gl.TRIANGLES, 0, 3);
	if (!reduceMotion) raf = requestAnimationFrame(frame);
}

onMounted(() => {
	reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
	if (!init()) {
		// WebGL unavailable — let the CSS fallback gradient show through.
		canvas.value?.classList.add("bob-orb-gl--fallback");
		return;
	}
	ro = new ResizeObserver(() => resize());
	if (canvas.value) ro.observe(canvas.value);
	raf = requestAnimationFrame(frame);
});

onBeforeUnmount(() => {
	cancelAnimationFrame(raf);
	ro?.disconnect();
	const ext = gl?.getExtension("WEBGL_lose_context");
	ext?.loseContext();
	gl = null;
	program = null;
});
</script>

<style scoped>
.bob-orb-gl {
	display: block;
	width: 100%;
	height: 100%;
}
/* Shown only if WebGL fails to initialise. */
.bob-orb-gl--fallback {
	background: radial-gradient(circle at 40% 35%, #8b5cf6, #ec4899 45%, #22d3ee 80%, transparent);
	opacity: 0.5;
	filter: blur(6px);
}
</style>
