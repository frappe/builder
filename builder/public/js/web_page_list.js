frappe.listview_settings["Web Page"] = {
  ...frappe.listview_settings["Web Page"],
  onload(listview) {
    // frappe.ui.alert ships from Frappe v16
    if (!frappe.ui.alert || !frappe.model.can_create("Builder Page")) return;
    frappe.ui
      .alert({
        theme: "blue",
        title: __("Build new pages in Builder"),
        description: __(
          "Web Pages you already have keep working and stay editable here.",
        ),
        css_class: "mx-4 mt-4",
        footer: frappe.ui.button({
          label: __("Open in Builder"),
          variant: "outline",
          onclick: () => window.open("/api/method/builder.api.open_editor"),
        }),
      })
      .prependTo(listview.page.main);
  },
  primary_action() {
    if (frappe.model.can_create("Builder Page")) {
      window.location.assign("/api/method/builder.api.open_editor?page=new");
    } else {
      frappe.new_doc("Web Page");
    }
  },
};
