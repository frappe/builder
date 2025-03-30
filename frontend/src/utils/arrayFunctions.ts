// @ts-ignore
Array.prototype.add = function (...itemsToAdd: any[]) {
	itemsToAdd.forEach((item) => {
		if (!this.includes(item)) {
			this.push(item);
		}
	});
};

// @ts-ignore
Array.prototype.remove = function (...itemsToRemove: any[]) {
	itemsToRemove.forEach((item) => {
		const index = this.indexOf(item);
		if (index !== -1) {
			this.splice(index, 1);
		}
	});
};
