import { createResource } from 'frappe-ui'
import { unref, reactive } from 'vue'

export function useNewDoc(doctype, doc = {}) {
  doc = reactive(doc)
  const resource = createResource({
    url: 'frappe.client.insert',
    makeParams() {
      let values = unref(doc)
      return {
        doc: {
          doctype,
          ...values,
        },
      }
    },
  })

  resource.doc = doc
  return resource
}
