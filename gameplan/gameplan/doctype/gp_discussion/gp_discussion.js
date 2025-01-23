// Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("GP Discussion", {
  refresh: function (frm) {
    frm.add_custom_button(__("Show in Gameplan"), function () {
      window.open(`/g/space/${frm.doc.project}/discussion/${frm.doc.name}`);
    });
  },
});
