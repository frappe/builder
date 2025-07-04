import { StyleToken } from "../types/Builder/StyleToken";

export function getCSSVariableValue(variable: CSSVariableValue): string {
	if (!variable?.startsWith?.("var(--")) return variable;
	const varName = variable.slice(4, -1);
	const computedStyle = getComputedStyle(document.documentElement);
	const value = computedStyle.getPropertyValue(varName).trim();
	return value || "";
}

export function setCSSVariable(name: string, value: string): void {
	document.documentElement.style.setProperty(`--${name}`, value);
}

export function getCSSVariableWithFallback(variable: CSSVariableValue, fallback: string): string {
	const value = getCSSVariableValue(variable);
	return value || fallback;
}

export function isCSSVariable(value: string): boolean {
	return value?.startsWith?.("var(--") || false;
}

export function createCSSVariable(name: string): `var(--${string})` {
	return `var(--${name})`;
}

export function createStyleTokenVariable(token: StyleToken): `var(--${string})` {
	if (!token.token_name) throw new Error("Token name is required");
	return createCSSVariable(token.token_name);
}

export function getStyleTokenValue(token: StyleToken, fallback?: string): string {
	if (!token.value) return fallback || "";
	return getCSSVariableWithFallback(token.value, fallback || "");
}

export function isValidStyleToken(token: StyleToken): boolean {
	return Boolean(token.token_name && token.type && token.value);
}
