// Copyright (c) 2023, asdf and contributors
// For license information, please see license.txt

frappe.ui.form.on("Builder Page", {
  refresh(frm) {
    // only show in developer mode
    if (frappe.boot.developer_mode || !frm.doc.is_template) {
      frm.sidebar
        .add_user_action(__("Open in Builder"))
        .attr("href", `/${frm.doc.__onload.builder_path}/page/${frm.doc.name}`)
        .attr("target", "_blank");
    }
  },
  onload(frm) {
    frm.set_df_property("blocks", "wrap", true);
    frm.set_df_property("draft_blocks", "wrap", true);
  },
  set_meta_tags(frm) {
    frappe.utils.set_meta_tag(frm.doc.route);
  },
});
