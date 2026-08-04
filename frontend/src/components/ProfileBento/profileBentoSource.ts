import { call } from 'frappe-ui'
import type { ProfileBentoCard } from './types'
import type { ProfileBentoCardSource } from './useProfileBentoCustomization'

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

export async function getProfileBentoCards(profile: string) {
  let response = await call<ProfileBentoResponse>(getProfileBentoCardsMethod, { profile })
  return getLoadResultFromResponse(response)
}

function getLoadResultFromResponse(response: ProfileBentoResponse): ProfileBentoLoadResult {
  return {
    cards: response.cards || [],
    isDefault: response.is_default,
  }
}
