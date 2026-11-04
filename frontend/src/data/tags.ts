import { GPTag } from '@/types/doctypes'
import { useList } from 'frappe-ui'
import { isAnonymousVisitor } from '@/utils/publicAccess'

export const tags = useList<GPTag>({
  doctype: 'GP Tag',
  fields: ['name', 'label'],
  limit: 9999,
  // Tags are not public; someone who is not signed in has none to load.
  immediate: !isAnonymousVisitor(),
})
