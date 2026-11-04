import { call, useCall } from 'frappe-ui'
import { computed, MaybeRefOrGetter, toValue, watch } from 'vue'
import type { ProfileBentoCard } from './types'
import type { ProfileBentoCardSource } from './useProfileBentoCustomization'
import { onReconnect } from '@/data/online'

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
      bentoCalls[response.profile]?.reload()
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
  bentoCalls[response.profile]?.reload()
  return getLoadResultFromResponse(response)
}

function getLoadResultFromResponse(response: ProfileBentoResponse): ProfileBentoLoadResult {
  return {
    cards: response.cards || [],
    isDefault: response.is_default,
  }
}

// One `get_bento_cards` fetch per profile. Revisiting a profile reuses its call instead of
// racing a fresh request.
const bentoCalls: Record<string, ReturnType<typeof createProfileBentoCall>> = {}

function createProfileBentoCall(profile: string) {
  return useCall<ProfileBentoResponse, { profile: string }>({
    // A full path: unlike call(), useCall doesn't prefix /api/method/ to a method name.
    url: `/api/v2/method/${getProfileBentoCardsMethod}`,
    params: { profile },
    cacheKey: ['ProfileBento', profile],
    immediate: false,
  })
}

/** A profile's bento cards, read from its shared call above, so a revisit reuses it. */
export function useProfileBento(profile: MaybeRefOrGetter<string | undefined>) {
  const bentoCall = computed(() => {
    let name = toValue(profile)
    return name ? (bentoCalls[name] ??= createProfileBentoCall(name)) : null
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
    (_name, _previous, onCleanup) => {
      const current = bentoCall.value
      if (!current) return
      onCleanup(
        onReconnect(() => {
          if (!current.loading) current.reload()
        }),
      )
      if (!current.loading) current.reload()
    },
    { immediate: true },
  )

  return { cards, isDefault, loaded, failed, error, reload: () => bentoCall.value?.reload() }
}
