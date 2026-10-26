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

export function measureImageLayout(src?: string): Promise<'large' | ''> {
  if (!src || !/^https?:\/\//i.test(src)) return Promise.resolve('')
  return new Promise((resolve) => {
    const image = new Image()
    const timer = setTimeout(() => resolve(''), 3000)
    image.referrerPolicy = 'no-referrer'
    image.onload = () => {
      clearTimeout(timer)
      const { naturalWidth: width, naturalHeight: height } = image
      resolve(width >= 400 && width / height >= 1.3 ? 'large' : '')
    }
    image.onerror = () => {
      clearTimeout(timer)
      resolve('')
    }
    image.src = src
  })
}
