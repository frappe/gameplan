import { useDoctype } from 'frappe-ui'
import type { Discussion } from './discussions'

// A bookmark row is either the opening post (GP Discussion) or one reply (GP Comment).
// Each doctype gets its own instance: a useDoctype shares one request per method kind.
const discussionDoctype = useDoctype('GP Discussion')
const commentDoctype = useDoctype('GP Comment')

type BookmarkMethod = 'add_bookmark' | 'remove_bookmark'

export function removeBookmark(row: Discussion) {
  return runBookmarkMethod(row, 'remove_bookmark')
}

export function restoreBookmark(row: Discussion) {
  return runBookmarkMethod(row, 'add_bookmark')
}

function runBookmarkMethod(row: Discussion, method: BookmarkMethod) {
  if (row.bookmarked_comment) {
    return commentDoctype.runDocMethod.submit({ name: row.bookmarked_comment, method })
  }
  return discussionDoctype.runDocMethod.submit({ name: row.name, method })
}
