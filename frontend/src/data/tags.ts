import { GPTag } from '@/types/doctypes'
import { useList } from '@/data/staleWhileRevalidate'

export const tags = useList<GPTag>({
  doctype: 'GP Tag',
  fields: ['name', 'label'],
  limit: 9999,
})
