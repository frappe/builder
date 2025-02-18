// Copyright (c) 2023, Frappe Technologies Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Builder Settings", {
  refresh(frm) {
    frm.add_custom_button(__("Replace Component"), () => {
      frappe.call({
        method:
          "builder.builder.doctype.builder_settings.builder_settings.get_components",
        callback: (r) => {
          const components = r.message;
          // modal to select target component and component to replace with
          const d = new frappe.ui.Dialog({
            title: __("Replace Component"),
            fields: [
              {
                fieldname: "target_component",
                label: __("Target Component"),
                fieldtype: "Select",
                options: components,
                reqd: 1,
              },
              {
                fieldname: "replace_with",
                label: __("Replace With"),
                fieldtype: "Select",
                options: components,
                reqd: 1,
              },
            ],
          });

          d.set_primary_action(__("Replace"), (values) => {
            frappe.confirm(
              __("Are you sure you want to replace {0} with {1}?", [
                values.target_component,
                values.replace_with,
              ]),
              () => {
                frappe.call({
                  method:
                    "builder.builder.doctype.builder_settings.builder_settings.replace_component",
                  args: {
                    target_component: values.target_component,
                    replace_with: values.replace_with,
                  },
                  callback: (r) => {
                    frappe.msgprint(__("Component replaced successfully"));
                    d.hide();
                  },
                });
              },
            );
          });
          d.show();
        },
      });
    });
  },
});
