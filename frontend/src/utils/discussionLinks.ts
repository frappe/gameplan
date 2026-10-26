declare const __FRONTEND_ROUTE__: string

const DISCUSSION_PATH = /^\/(?:.+\/)?discussion\/(\d+)(?:\/|$)/

export function parseDiscussionUrl(href: string) {
  let url: URL
  try {
    url = new URL(href, window.location.origin)
  } catch {
    return null
  }
  const base = __FRONTEND_ROUTE__
  if (url.host !== window.location.host || !url.pathname.startsWith(`${base}/`)) return null
  const path = url.pathname.slice(base.length)
  const name = path.match(DISCUSSION_PATH)?.[1]
  return name ? { name, path: path + url.search + url.hash } : null
}

export function discussionHref(project: string, name: string) {
  return `${__FRONTEND_ROUTE__}/space/${project}/discussion/${name}`
}
