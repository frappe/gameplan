import type { GPUserProfile } from '@/types/doctypes'
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

/** True when HTML carries visible content. An empty TipTap document is `<p></p>`. */
function htmlHasContent(value?: string) {
  if (!value) return false
  if (/<\s*(img|video|audio|iframe|embed)\b/i.test(value)) return true
  return Boolean(value.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').trim())
}
