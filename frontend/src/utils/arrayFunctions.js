Array.prototype.add = function (...itemsToAdd) {
	itemsToAdd.forEach(item => {
		if (!this.includes(item)) {
			this.push(item)
		}
	})
}

Array.prototype.remove = function (...itemsToRemove) {
	itemsToRemove.forEach(item => {
		const index = this.indexOf(item)
		if (index !== -1) {
			this.splice(index, 1)
		}
	})
}
