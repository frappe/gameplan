/**
 * One photo, as `gameplan.unsplash.search_photos` returns it.
 *
 * Deliberately not Unsplash's own shape: the proxy trims their payload to these
 * fields, so this is the contract with our server, not with theirs.
 */
export interface UnsplashPhoto {
  id: string
  /** Small render for the grid. */
  thumb_url: string
  /** ~1080px render — the URL that gets stored and hotlinked. */
  url: string
  /** Unsplash's own description, used as the image's alt text. May be empty. */
  alt: string
  photographer_name: string
  /** Attribution links, already carrying the UTM parameters Unsplash requires. */
  photographer_url: string
  photo_url: string
  /** Pinged when the photo is actually chosen. Unsplash requires this. */
  download_location: string
}

export interface UnsplashSearchResult {
  /** False when the site has no `unsplash_access_key`; `message` says so. */
  configured: boolean
  message?: string
  /** Whichever of the two the photos came from. A query clears the topic. */
  query?: string
  topic?: string
  total: number
  photos: UnsplashPhoto[]
}

export interface UnsplashTopic {
  /** Must be in `TOPIC_SLUGS` in `gameplan/unsplash.py`, which rejects the rest. */
  slug: string
  label: string
}

/**
 * What the picker offers to browse, in the order the chips appear.
 *
 * Mirrors `TOPIC_SLUGS` in `gameplan/unsplash.py`. "Featured" is Unsplash's
 * editorial feed rather than a topic of theirs, and the server routes it to its
 * own endpoint. It is first because the picker opens on it.
 */
export const unsplashTopics: UnsplashTopic[] = [
  { slug: 'featured', label: 'Featured' },
  { slug: 'wallpapers', label: 'Wallpapers' },
  { slug: 'nature', label: 'Nature' },
  { slug: 'textures-patterns', label: 'Textures' },
  { slug: 'architecture-interior', label: 'Architecture' },
  { slug: 'travel', label: 'Travel' },
  { slug: '3d-renders', label: '3D renders' },
]
