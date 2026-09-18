import { useCall } from 'frappe-ui'
import type { NotificationRow } from './notifications'

/** A notification row as the card shows it: the row, plus the discussion title and, for a
 * mention, a snippet of the text that mentioned you. */
export interface AwayItem extends Omit<NotificationRow, 'read'> {
  title: string | null
  snippet: string | null
}

/** The "while you were away" card payload; `null` when there is nothing to recap. */
export interface AwaySummary {
  period: string
  kind: 'Toggle' | 'Active hours'
  starts_at: string
  ends_at: string
  unread: number
  mentions: { total: number; items: AwayItem[] }
  comments: AwayItem[]
  other: AwayItem[]
}

/**
 * Loaded by the Notifications page alongside its lists and reloaded with them: a period
 * that ends while the page is open shows its card on the next list reload, and reading
 * the rows anywhere retires it, since the summary only counts unread rows.
 *
 * Deliberately not cached: `useCall` serves the cached response whenever the fresh one is
 * `null`, and `null` is exactly how the server says "no card any more".
 */
export const awaySummary = useCall<AwaySummary | null>({
  url: '/api/v2/method/gameplan.api.away_summary',
  immediate: false,
})

export const markAwayCardRead = useCall<void, { period: string }>({
  url: '/api/v2/method/gameplan.api.mark_away_card_read',
  method: 'POST',
  immediate: false,
})

export const dismissAwayCard = useCall<void, { period: string }>({
  url: '/api/v2/method/gameplan.api.dismiss_away_card',
  method: 'POST',
  immediate: false,
})
