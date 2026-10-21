import type { Component } from "vue";

// frappe-ui ships source types. Keep type-checking scoped to what this sample uses.
export const Button: Component;
export const toast: { success: (message: string) => void; error: (message: string) => void };
