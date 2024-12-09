import useList from 'frappe-ui/src/data-fetching/useList'
import { GPProject } from '@/types/GPProject'

let spaces = useList<GPProject>('GP Project', {
  fields: [
    'name',
    'title',
    'icon',
    'team',
    'archived_at',
    'is_private',
    'modified',
    'tasks_count',
    'discussions_count',
    { members: ['user', 'role'] },
  ],
  orderBy: 'title asc',
  limit: 999,
})

export function useSpaces() {
  return spaces
}
