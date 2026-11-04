import { dayjs, getConfig } from 'frappe-ui'

export type RestrictionUser = {
  user: string
  full_name?: string
  user_image?: string
  reason?: string
  expires_at?: string | null
  modified?: string
}

export function expiryLabel(value?: string | null) {
  if (!value) return 'Until manually lifted'
  const date = dayjs(value).tz(
    getConfig('localTimezone') || Intl.DateTimeFormat().resolvedOptions().timeZone,
  )
  return `${date.format('D MMM YYYY, h:mm A z')} (${date.fromNow()})`
}

export function restrictionTransition(item: {
  action: string
  expires_at?: string
  previous_expires_at?: string
}) {
  const date = (value?: string) =>
    value
      ? dayjs(value)
          .tz(getConfig('localTimezone') || Intl.DateTimeFormat().resolvedOptions().timeZone)
          .format('D MMM YYYY, h:mm A z')
      : 'Indefinite'
  if (item.action === 'Restriction Expired') return `Expired at ${date(item.expires_at)}`
  if (['Unban', 'Lift Suspension'].includes(item.action))
    return `${date(item.previous_expires_at)} → Lifted`
  if (['Ban', 'Suspend'].includes(item.action)) return `Expiry: ${date(item.expires_at)}`
  return `${date(item.previous_expires_at)} → ${date(item.expires_at)}`
}
