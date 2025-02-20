// Copyright (c) 2023, Frappe Technologies Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Builder Client Script", {
  refresh(frm) {
    frm.trigger("set_editor_options");
  },
  script_type(frm) {
    frm.trigger("set_editor_options");
  },
  set_editor_options(frm) {
    if (!frm.get_field("script").editor) {
      return;
    }
    if (frm.doc.script_type == "CSS") {
      frm.get_field("script").editor.session.setMode("ace/mode/css");
    } else if (frm.doc.script_type == "JavaScript") {
      frm.get_field("script").editor.session.setMode("ace/mode/javascript");
    }
  },
});
