import type { GPUserProfile } from '@/types/doctypes'
import type { ProfileBentoCard, ProfileBoundField } from './types'
import type { ProfileBoundValues } from './useProfileBentoCustomization'

/**
 * The customize editor's preview of what each bound card would show.
 *
 * The server is the authority — `resolve_profile_bound_value` in
 * `gp_user_profile.py` resolves every bound card on every read. This mirror
 * exists only so that ticking a field in the checklist shows the card's real
 * value immediately, instead of a placeholder until the layout is saved.
 */
export function resolveProfileBoundValues(profile?: GPUserProfile | null): ProfileBoundValues {
  if (!profile) return {}
  return {
    cover_image: profile.cover_image || undefined,
    image: profile.image || undefined,
    full_name: profile.full_name?.trim() || profile.user || undefined,
    bio: profile.bio?.trim() || undefined,
    readme: htmlHasContent(profile.readme) ? profile.readme : undefined,
  }
}

/**
 * The layout draft carries no bound values — they belong to the profile, and a
 * `source: 'field'` row's `text`/`image` is discarded on save. So the editor
 * resolves them for display here, on the way to the canvas, which also means a
 * profile edit made from the panel shows up as soon as the profile reloads.
 */
export function applyProfileBoundValues(
  cards: ProfileBentoCard[],
  profile?: GPUserProfile | null,
): ProfileBentoCard[] {
  let values = resolveProfileBoundValues(profile)
  return cards.map((card) => {
    if (card.source !== 'field' || !card.field) return card

    let value = values[card.field as ProfileBoundField]
    let resolved: ProfileBentoCard = { ...card, text: undefined, image: undefined }
    if (value) resolved[card.format === 'image' ? 'image' : 'text'] = value
    // Where the cover sits is a property of the image, not of the layout:
    // `set_cover_image_position` writes the profile field and mirrors it onto the
    // row, so the profile is the value both read paths agree on.
    if (card.field === 'cover_image') {
      resolved.imagePosition = clampImagePosition(profile?.cover_image_position)
    }
    return resolved
  })
}

function clampImagePosition(position?: number | null) {
  if (position == null) return 50
  return Math.min(100, Math.max(0, Number(position) || 0))
}

/** True when HTML carries visible content. An empty TipTap document is `<p></p>`. */
function htmlHasContent(value?: string) {
  if (!value) return false
  if (/<\s*(img|video|audio|iframe|embed)\b/i.test(value)) return true
  return Boolean(value.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').trim())
}
