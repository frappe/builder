// Copyright (c) 2023, asdf and contributors
// For license information, please see license.txt

frappe.ui.form.on("Builder Page", {
  refresh(frm) {
    frm.sidebar
      .add_user_action(__("Open in Builder"))
      .attr("href", `/builder/page/${frm.doc.name}`)
      .attr("target", "_blank");
  },
});
