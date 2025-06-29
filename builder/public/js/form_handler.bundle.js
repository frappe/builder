import { showToast } from "./toast.js";

class FormHandler {
	constructor(formSelector) {
		this.form = document.querySelector(formSelector);
		if (!this.form) {
			return;
		}
		this.handleSubmit = this.handleSubmit.bind(this);
		this.loadWebForm();
	}

	init() {
		if (this.form) {
			this.form.addEventListener("submit", this.handleSubmit);
		}
	}

	loadWebForm() {
		const webFormName = this.form.dataset.webForm;
		if (!webFormName) {
			console.error("Web form name is not specified.");
			return;
		}
		fetch(`/api/method/frappe.client.get?doctype=Web%20Form&name=${webFormName}`, {
			method: "GET",
			headers: {
				accept: "application/json",
			},
		})
			.then((response) => response.json())
			.then((data) => {
				if (data.message) {
					this.webFormDoc = data.message;
				} else {
					console.error("Error loading web form.");
				}
			})
			.catch((error) => {
				console.error("Error:", error);
			});
	}

	handleSubmit(event) {
		event.preventDefault();
		const formData = new FormData(this.form);
		const webFormName = this.form.dataset.webForm;

		fetch("/api/method/frappe.website.doctype.web_form.web_form.accept", {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify({
				data: JSON.stringify(Object.fromEntries(formData)),
				web_form: webFormName,
			}),
		})
			.then((response) => response.json())
			.then((data) => {
				if (data.message) {
					// Handle success based on webFormDoc
					if (
						this.webFormDoc &&
						(this.webFormDoc.success_message || this.webFormDoc.success_title || this.webFormDoc.success_url)
					) {
						// Show custom success message or redirect
						if (this.webFormDoc.success_message) {
							showToast(this.webFormDoc.success_message, "success");
						} else if (this.webFormDoc.success_title) {
							showToast(this.webFormDoc.success_title, "success");
						}
						if (this.webFormDoc.success_url) {
							setTimeout(() => {
								window.location.href = this.webFormDoc.success_url;
							}, 2000); // 2 second delay
							return;
						}
					} else {
						alert("Form submitted successfully!");
					}
				} else {
					alert("Error submitting form.");
				}
			})
			.catch((error) => {
				console.error("Error:", error);
			});
	}
}

document.addEventListener("DOMContentLoaded", () => {
	const formHandler = new FormHandler("form");
	formHandler.init();
});
