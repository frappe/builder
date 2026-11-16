frappe.ui.form.on("Web Page", {
  onload(frm) {
    if (frm.is_new() && frappe.model.can_create("Builder Page")) {
      // replace, so Back returns to where "New" was clicked instead of redirecting again
      window.location.replace("/api/method/builder.api.open_editor?page=new");
    }
  },
  refresh(frm) {
    if (frm.is_new() || !frappe.model.can_create("Builder Page")) return;
    frm.set_intro(
      `${__("Build new pages in Builder. This Web Page keeps working and stays editable here.")}
      <a href="/api/method/builder.api.open_editor" target="_blank">${__("Open in Builder")}</a>`,
      "blue",
    );
  },
});
