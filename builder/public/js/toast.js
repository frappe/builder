const style = document.createElement("style");
style.textContent = `
.toast {
	position: fixed;
	bottom: 20px;
	left: 50%;
	transform: translateX(-50%);
	padding: 12px 24px;
	border-radius: 4px;
	color: white;
	z-index: 1000;
	animation: slideUp 0.3s, fadeOut 0.3s 2.7s;
}

.toast-info {
	background-color: #2196F3;
}

.toast-success {
	background-color: #4CAF50;
}

.toast-error {
	background-color: #F44336;
}

@keyframes slideUp {
	from { transform: translate(-50%, 100%); }
	to { transform: translate(-50%, 0); }
}

@keyframes fadeOut {
	from { opacity: 1; }
	to { opacity: 0; }
}
`;
document.head.appendChild(style);

function showToast(message, type = "info") {
	const toast = document.createElement("div");
	toast.className = `toast toast-${type}`;
	toast.textContent = message;
	document.body.appendChild(toast);
	setTimeout(() => {
		toast.remove();
	}, 3000);
}

export { showToast };
