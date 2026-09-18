import { call } from 'frappe-ui'
import { useCall } from '@/data/offlineRevalidation'
import { computed, MaybeRefOrGetter, toValue, watch } from 'vue'
import type { ProfileBentoCard } from './types'
import type { ProfileBentoCardSource } from './useProfileBentoCustomization'
import { session } from '@/data/session'

interface ProfileBentoResponse {
  profile: string
  cards: ProfileBentoCard[]
  /** False once a layout has been saved; `cards` is then the stored rows. */
  is_default: boolean
}

/** What every read path here returns. The server always says which layout it sent. */
export interface ProfileBentoLoadResult {
  cards: ProfileBentoCard[]
  isDefault: boolean
}

const getBentoCardsMethod =
  'gameplan.gameplan.doctype.gp_user_profile.gp_user_profile.get_my_bento_cards'
const getProfileBentoCardsMethod =
  'gameplan.gameplan.doctype.gp_user_profile.gp_user_profile.get_bento_cards'
const saveBentoCardsMethod =
  'gameplan.gameplan.doctype.gp_user_profile.gp_user_profile.save_my_bento_cards'
const resetBentoCardsMethod =
  'gameplan.gameplan.doctype.gp_user_profile.gp_user_profile.reset_my_bento_cards'

export function createServerProfileBentoSource(): ProfileBentoCardSource {
  return {
    async load() {
      let response = await call<ProfileBentoResponse>(getBentoCardsMethod)
      return getLoadResultFromResponse(response)
    },
    async save(cards) {
      let response = await call<ProfileBentoResponse>(saveBentoCardsMethod, {
        cards,
      })
      invalidateProfileBentoCall(response.profile)
    },
    reset: resetProfileBentoCards,
  }
}

/**
 * Throws away the session user's saved layout. The response is the computed
 * default the profile falls back to, in the same shape `load` returns, so a
 * caller can show the restored layout without reading it again.
 */
export async function resetProfileBentoCards() {
  let response = await call<ProfileBentoResponse>(resetBentoCardsMethod)
  invalidateProfileBentoCall(response.profile)
  return getLoadResultFromResponse(response)
}

function getLoadResultFromResponse(response: ProfileBentoResponse): ProfileBentoLoadResult {
  return {
    cards: response.cards || [],
    isDefault: response.is_default,
  }
}

// One `get_bento_cards` fetch per profile, keyed by profile and session user so another
// account on this browser can't read the cards offline. Revisiting a profile reuses its call
// instead of racing a fresh request.
const bentoCalls: Record<string, ReturnType<typeof createProfileBentoCall>> = {}

function createProfileBentoCall(profile: string) {
  return useCall<ProfileBentoResponse>({
    // A full path: unlike call(), useCall doesn't prefix /api/method/ to a method name.
    url: `/api/v2/method/${getProfileBentoCardsMethod}`,
    params: { profile },
    cacheKey: ['ProfileBento', profile, session.user],
    staleOnError: true,
    immediate: false,
  })
}

function getProfileBentoCall(profile: string) {
  if (!bentoCalls[profile]) {
    bentoCalls[profile] = createProfileBentoCall(profile)
  }
  return bentoCalls[profile]
}

/**
 * Reloads a profile's cached cards after save/reset, in place, so a profile page already
 * showing them (e.g. behind the settings dialog) updates too. Without it, a call from an
 * earlier visit is already finished and would keep showing the pre-save layout.
 */
function invalidateProfileBentoCall(profile: string) {
  bentoCalls[profile]?.reload()
}

/** A profile's bento cards, read from its shared call above, so a revisit reuses it. */
export function useProfileBento(profile: MaybeRefOrGetter<string | undefined>) {
  const bentoCall = computed(() => {
    let name = toValue(profile)
    return name ? getProfileBentoCall(name) : null
  })

  const cards = computed<ProfileBentoCard[]>(() => bentoCall.value?.data?.cards || [])
  const isDefault = computed(() => bentoCall.value?.data?.is_default ?? true)
  // Resolves on failure too (not just success) - the forever-skeleton bug this replaces
  // came from the old plain `call()` throwing uncaught and never flipping its "loaded" ref.
  // `data != null` lets a cache hit show immediately without waiting for the network leg
  // that staleOnError may still be racing in the background.
  const loaded = computed(() => {
    let current = bentoCall.value
    if (!current) return false
    return current.data != null || Boolean(current.isFinished)
  })
  const failed = computed(() => {
    let current = bentoCall.value
    return Boolean(current && current.error && current.data == null)
  })
  const error = computed(() => bentoCall.value?.error ?? null)

  watch(
    () => toValue(profile),
    (name) => {
      if (!name) return
      let current = getProfileBentoCall(name)
      if (!current.isFinished && !current.loading) current.reload()
    },
    { immediate: true },
  )

  function reload() {
    return bentoCall.value?.reload()
  }

  return { cards, isDefault, loaded, failed, error, reload }
}
