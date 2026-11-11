import type { EmptyState } from '@/components/EmptyStateBox.vue'

// The feeds a discussions page can show, for one community or across all of them.
// The order is the order of the tabs.
const discussionFeeds = ['recent', 'participating', 'unread'] as const

export type FeedType = (typeof discussionFeeds)[number]

export const feedTitles: Record<FeedType, string> = {
  recent: 'All Discussions',
  participating: 'Participating',
  unread: 'Unread',
}

export const feedEmptyStates: Record<FeedType, EmptyState> = {
  recent: {
    icon: 'lucide-messages-square',
    title: 'No discussions yet',
    description: 'New discussions will show up here.',
  },
  participating: {
    icon: 'lucide-message-circle',
    title: "You're not in any discussions yet",
    description: 'Discussions you start or reply to will show up here.',
  },
  unread: {
    icon: 'lucide-check-check',
    title: "You're caught up",
    description: 'Discussions with new activity will show up here.',
  },
}

export const feedTabs = discussionFeeds.map((feed) => ({ label: feedTitles[feed], value: feed }))

export function isFeedType(value: string): value is FeedType {
  return (discussionFeeds as readonly string[]).includes(value)
}
