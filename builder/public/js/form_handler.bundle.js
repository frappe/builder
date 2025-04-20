console.log("form handler loaded 3");
document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("form");
  form.addEventListener("submit", function (event) {
    event.preventDefault();
    const formData = new FormData(this);
    fetch("/api/method/frappe.website.doctype.web_form.web_form.accept", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        data: JSON.stringify(Object.fromEntries(formData)),
        web_form: this.dataset.webForm,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.message) {
          alert("Form submitted successfully!");
        } else {
          alert("Error submitting form.");
        }
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  });
});
