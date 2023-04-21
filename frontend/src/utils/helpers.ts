function getNumberFromPx(px: string | number ): number {
	if (!px) {
		return 0;
	}
	if (typeof px === "number") {
		return px;
	}
	return Number(px.replace("px", ""));
}

export {
	getNumberFromPx,
}