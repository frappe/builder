/** Costs are computed in USD (provider pricing); display converts to the site's
 * currency with a daily rate the backend caches (builder.ai.api.get_ai_cost_currency).
 * Until that loads (or when it fails) we display plain USD. */
let costCurrency = { currency: "USD", rate: 1 };

export function setCostCurrency(c: { currency?: string; rate?: number } | null) {
	if (c?.currency && c?.rate) costCurrency = { currency: c.currency, rate: c.rate };
}

/** Display an approximate LLM cost in the site's currency, with enough
 * significant digits that sub-cent turns don't read as zero. */
export function formatCost(costUsd: number): string {
	const value = costUsd * costCurrency.rate;
	try {
		return new Intl.NumberFormat(navigator.language, {
			style: "currency",
			currency: costCurrency.currency,
			maximumSignificantDigits: 3,
		}).format(value);
	} catch {
		return `$${parseFloat(costUsd.toFixed(4))}`;
	}
}
