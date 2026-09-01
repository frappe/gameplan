interface TimelineItemWithDoctype {
  doctype?: string
}

// Comments and polls are both posts: on mobile they carry their own gap here,
// because their sticky headers only pad themselves out from `sm` up.
const POST_DOCTYPES = ['GP Comment', 'GP Poll']

export function needsMobileCommentGap(
  timelineItems: TimelineItemWithDoctype[],
  index: number,
  options: { includeFirstComment?: boolean } = {},
) {
  const item = timelineItems[index]
  if (!POST_DOCTYPES.includes(item?.doctype ?? '')) return false

  return Boolean(
    (options.includeFirstComment && index === 0) ||
    POST_DOCTYPES.includes(timelineItems[index - 1]?.doctype ?? ''),
  )
}
