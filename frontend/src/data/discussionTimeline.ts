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

// Scoped to the session user: a discussion can live in a private space, so a second account
// on the same browser must not see these cached offline before its own permission-checked
// fetch resolves (review finding from PR #516).
export function commentsCacheKey(doctype: string, name: string, user: string) {
  return ['Comments', doctype, name, user]
}

export function activitiesCacheKey(doctype: string, name: string, user: string) {
  return ['Activities', doctype, name, user]
}

export function pollsCacheKey(discussion: string, user: string) {
  return ['Polls', discussion, user]
}
