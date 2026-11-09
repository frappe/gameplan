// The feeds a discussions page can show, for one community or across all of them.
// The order is the order of the tabs.
const discussionFeeds = ['recent', 'participating', 'unread'] as const

export type FeedType = (typeof discussionFeeds)[number]

export const feedTitles: Record<FeedType, string> = {
  recent: 'All Discussions',
  participating: 'Participating',
  unread: 'Unread',
}

export const feedTabs = discussionFeeds.map((feed) => ({ label: feedTitles[feed], value: feed }))

export function isFeedType(value: string): value is FeedType {
  return (discussionFeeds as readonly string[]).includes(value)
}
