import { computed, ref } from 'vue'
import { useLocalStorage } from '@vueuse/core'
import { marked } from 'marked'

/**
 * What's new in Gameplan, read from the Markdown files in `src/changelog/`.
 *
 * A pull request adds its entry with `version: unreleased`. The release workflow
 * (.github/scripts/stamp_changelog.py) replaces that with the version and date it
 * releases, so entries group under the release that shipped them.
 *
 * `media: clip.mp4` names a light-theme screenshot or video. Put a `clip.dark.mp4`
 * beside it and dark-theme users see that one instead.
 */

export interface ChangelogEntry {
  id: string
  title: string
  /** Undefined until the release workflow stamps it. */
  version?: string
  /** `YYYY-MM-DD`, stamped with the version. */
  date?: string
  /** `darkUrl` is the `<name>.dark.<ext>` file beside the named one, when there is one. */
  media?: { url: string; darkUrl?: string; kind: 'image' | 'video' }
  html: string
}

export interface ChangelogRelease {
  /** Undefined for entries merged into this build but not yet released. */
  version?: string
  date?: string
  entries: ChangelogEntry[]
}

const sources = import.meta.glob<string>('../changelog/*.md', {
  eager: true,
  query: '?raw',
  import: 'default',
})
const mediaUrls = import.meta.glob<string>('../changelog/*.{png,jpg,jpeg,gif,webp,mp4,webm}', {
  eager: true,
  query: '?url',
  import: 'default',
})

const VIDEO_EXTENSIONS = ['mp4', 'webm']
// A browser that has never opened the dialog treats only this recent a release as new,
// so existing users hear about the latest changes without the whole history lighting up.
const NEW_FOR_DAYS = 30

export const changelogEntries: ChangelogEntry[] = Object.entries(sources)
  .map(([path, source]) => parseEntry(path, source))
  .sort(compareEntries)

export const changelogReleases: ChangelogRelease[] = groupByRelease(changelogEntries)

const seenEntryIds = useLocalStorage<string[] | null>('gameplan:changelogSeen', null)

export const unseenEntries = computed(() => {
  const seen = seenEntryIds.value
  if (seen) return changelogEntries.filter((entry) => !seen.includes(entry.id))
  return changelogEntries.filter(isRecent)
})

export const hasUnseenEntries = computed(() => unseenEntries.value.length > 0)

export const showChangelogDialog = ref(false)

export function openChangelog() {
  showChangelogDialog.value = true
  markChangelogSeen()
}

export function markChangelogSeen() {
  seenEntryIds.value = changelogEntries.map((entry) => entry.id)
}

function parseEntry(path: string, source: string): ChangelogEntry {
  const id = path.split('/').pop()!.replace(/\.md$/, '')
  const { fields, body } = splitFrontmatter(source)
  const version = fields.version && fields.version !== 'unreleased' ? fields.version : undefined

  return {
    id,
    title: fields.title || id,
    version,
    date: version ? fields.date || undefined : undefined,
    media: fields.media ? resolveMedia(id, fields.media) : undefined,
    html: marked.parse(body, { async: false }),
  }
}

/** The frontmatter is flat `key: value` lines; the release script edits it the same way. */
function splitFrontmatter(source: string) {
  const match = source.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/)
  if (!match) return { fields: {} as Record<string, string>, body: source }

  const fields: Record<string, string> = {}
  for (const line of match[1].split('\n')) {
    const separator = line.indexOf(':')
    if (separator === -1) continue
    fields[line.slice(0, separator).trim()] = line.slice(separator + 1).trim()
  }
  return { fields, body: match[2] }
}

function resolveMedia(id: string, fileName: string): ChangelogEntry['media'] {
  const url = mediaUrls[`../changelog/${fileName}`]
  if (!url) {
    console.warn(
      `Changelog entry "${id}" names media "${fileName}", which is not in src/changelog/`,
    )
    return undefined
  }
  const extension = fileName.split('.').pop()!.toLowerCase()
  const darkFileName = fileName.replace(/\.[^.]+$/, `.dark.${extension}`)
  return {
    url,
    darkUrl: mediaUrls[`../changelog/${darkFileName}`],
    kind: VIDEO_EXTENSIONS.includes(extension) ? 'video' : 'image',
  }
}

/** Unreleased first, then newest version first. */
function compareEntries(a: ChangelogEntry, b: ChangelogEntry) {
  if (!a.version || !b.version) return Number(Boolean(a.version)) - Number(Boolean(b.version))
  return compareVersions(b.version, a.version) || a.title.localeCompare(b.title)
}

function compareVersions(a: string, b: string) {
  const left = a.split('.').map(Number)
  const right = b.split('.').map(Number)
  for (let index = 0; index < Math.max(left.length, right.length); index++) {
    const difference = (left[index] ?? 0) - (right[index] ?? 0)
    if (difference) return difference
  }
  return 0
}

function groupByRelease(entries: ChangelogEntry[]): ChangelogRelease[] {
  const releases: ChangelogRelease[] = []
  for (const entry of entries) {
    const last = releases[releases.length - 1]
    if (last && last.version === entry.version) {
      last.entries.push(entry)
    } else {
      releases.push({ version: entry.version, date: entry.date, entries: [entry] })
    }
  }
  return releases
}

function isRecent(entry: ChangelogEntry) {
  if (!entry.date) return true
  const ageInDays = (Date.now() - new Date(entry.date).getTime()) / 86_400_000
  return ageInDays <= NEW_FOR_DAYS
}
