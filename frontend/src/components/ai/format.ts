/** Costs are computed in USD (provider pricing); display converts to the site's
 * currency with a daily rate the backend caches (builder.ai.api.get_ai_cost_currency).
 * Until that loads (or when it fails) we display plain USD. */
import { ref } from "vue";

// Reactive so already-rendered cost lines re-format the instant the currency
// resource resolves — the FX rate is slow on a cold cache, and history renders
// before it lands, so a plain module var would strand every cost on USD.
const costCurrency = ref({ currency: "USD", rate: 1 });

export function setCostCurrency(c: { currency?: string; rate?: number } | null) {
	if (c?.currency && c?.rate) costCurrency.value = { currency: c.currency, rate: c.rate };
}

/** Display an approximate LLM cost in the site's currency, with enough
 * significant digits that sub-cent turns don't read as zero. */
export function formatCost(costUsd: number): string {
	const { currency, rate } = costCurrency.value;
	const value = costUsd * rate;
	try {
		return new Intl.NumberFormat(navigator.language, {
			style: "currency",
			currency,
			maximumSignificantDigits: 3,
		}).format(value);
	} catch {
		return `$${parseFloat(costUsd.toFixed(4))}`;
	}
}
