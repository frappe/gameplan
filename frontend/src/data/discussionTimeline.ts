/**
 * What a discussion's timeline lists fetch and where they cache it. Shared by CommentsArea,
 * which fetches them, and offline downloads, which fills the same cache entries so a
 * downloaded discussion opens offline exactly as if it had been visited.
 */

export const COMMENT_FIELDS = [
  'name',
  'content',
  'owner',
  'creation',
  'modified',
  'edited_at',
  'deleted_at',
  { reactions: ['name', 'user', 'emoji'] },
]

export const ACTIVITY_FIELDS = ['name', 'user', 'action', 'data', 'creation']

export const POLL_FIELDS = [
  'name',
  'title',
  'anonymous',
  'multiple_answers',
  'creation',
  'owner',
  'stopped_at',
  { options: ['name', 'title', 'idx', 'percentage'] },
  { votes: ['user', 'option'] },
  { reactions: ['name', 'user', 'emoji'] },
]

// The offline-aware useList appends the signed-in user to each (offlineRevalidation.ts).
export function commentsCacheKey(doctype: string, name: string) {
  return ['Comments', doctype, name]
}

export function activitiesCacheKey(doctype: string, name: string) {
  return ['Activities', doctype, name]
}

export function pollsCacheKey(discussion: string) {
  return ['Polls', discussion]
}
