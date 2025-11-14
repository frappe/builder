// Copyright (c) 2024, Frappe Technologies Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Builder Project Folder", {
  refresh(frm) {
    frm.get_field("is_standard").df.read_only = !frappe.boot.developer_mode;
    frm.refresh_field("is_standard");

    if (frm.doc.is_standard && !frappe.boot.developer_mode) {
      frm.disable_form();
      frm.dashboard.clear_comment();
      frm.dashboard.add_comment(
        __(
          "Standard folders cannot be modified. Please enable developer mode to edit standard folders.",
        ),
        "orange",
        true,
      );
    }
  },
});
