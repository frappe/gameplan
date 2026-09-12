import { call, useCall } from 'frappe-ui'
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
      await call<ProfileBentoResponse>(saveBentoCardsMethod, {
        cards,
      })
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
  return getLoadResultFromResponse(response)
}

function getLoadResultFromResponse(response: ProfileBentoResponse): ProfileBentoLoadResult {
  return {
    cards: response.cards || [],
    isDefault: response.is_default,
  }
}

// One `get_bento_cards` fetch per profile, keyed by profile name + session user (an
// offline cache scoped any other way could leak one account's cached cards to a second
// account sharing the browser - review finding from PR #516). Shared by `useProfileBento`
// (the live page) and `prefetchProfileBento` (the background cache warmer) so both read
// and write the same IndexedDB entry instead of racing two independent requests for the
// same profile.
const bentoCalls: Record<string, ReturnType<typeof createProfileBentoCall>> = {}

function createProfileBentoCall(profile: string) {
  return useCall<ProfileBentoResponse>({
    // `useCall` takes `url` verbatim - unlike `call()` (used by createServerProfileBentoSource
    // below), it does not prefix a dotted method path with /api/method/ itself. A bare method
    // name here would resolve relative to whatever page the app is currently on and hit the
    // SPA's own catch-all route (200, HTML) instead of the API - see the same trap called out
    // in Notifications.vue's markAllAsRead.
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
 * Reactive bento-card read for one profile (`PersonProfile.vue`'s Profile tab). Cards come
 * straight off the shared per-profile call above instead of being copied into local refs,
 * so revisiting a profile already viewed this session reuses its resource rather than
 * re-racing a fresh request against whatever that earlier visit's request was doing - the
 * out-of-order-response guard the old `loadProfileBentoCards` needed is gone because each
 * profile now owns an isolated resource instead of sharing one mutable ref.
 */
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

/**
 * Warms a profile's bento-card cache ahead of a visit, for the background prefetcher.
 * Same cache key path as `useProfileBento`, so a later visit to this profile reads
 * whatever this fetched.
 */
export function prefetchProfileBento(personId: string) {
  return getProfileBentoCall(personId).reload()
}
