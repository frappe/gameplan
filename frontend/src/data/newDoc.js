import { reactive, unref } from 'vue'
import { createResource } from 'frappe-ui'

export function useNewDoc(doctype, doc = {}, resourceOptions = {}) {
  doc = reactive(doc)
  const resource = createResource({
    url: 'frappe.client.insert',
    makeParams(_values) {
      let payload = { doctype }
      for (let key in doc) {
        payload[key] = unref(doc[key])
      }
      return {
        doc: payload,
      }
    },
    ...resourceOptions,
  })

  resource.doc = doc
  return resource
}
