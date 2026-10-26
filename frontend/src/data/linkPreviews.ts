import { call } from 'frappe-ui'

export interface LinkPreview {
  title: string
  description: string
  image: string
  site_name: string
}

const cache = new Map<string, Promise<LinkPreview | null>>()

export function fetchLinkPreview(url: string) {
  if (!cache.has(url)) {
    const request = call('gameplan.api.get_link_preview', { url }).then(
      (preview: LinkPreview | null) => {
        if (!preview) cache.delete(url)
        return preview
      },
      (error) => {
        cache.delete(url)
        throw error
      },
    )
    cache.set(url, request)
  }
  return cache.get(url)!
}
