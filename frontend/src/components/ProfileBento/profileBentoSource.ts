import { call } from 'frappe-ui'
import type { ProfileBentoCard } from './types'
import type {
  ProfileBentoCardLoadResult,
  ProfileBentoCardSource,
} from './useProfileBentoCustomization'

interface ProfileBentoResponse {
  profile: string
  cards: ProfileBentoCard[]
  /** False once a layout has been saved; `cards` is then the stored rows. */
  is_default: boolean
}

const getBentoCardsMethod =
  'gameplan.gameplan.doctype.gp_user_profile.gp_user_profile.get_my_bento_cards'
const getProfileBentoCardsMethod =
  'gameplan.gameplan.doctype.gp_user_profile.gp_user_profile.get_bento_cards'
const saveBentoCardsMethod =
  'gameplan.gameplan.doctype.gp_user_profile.gp_user_profile.save_my_bento_cards'

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
  }
}

export async function getProfileBentoCards(profile: string) {
  let response = await call<ProfileBentoResponse>(getProfileBentoCardsMethod, { profile })
  return getLoadResultFromResponse(response)
}

function getLoadResultFromResponse(
  response: ProfileBentoResponse,
): Extract<ProfileBentoCardLoadResult, { cards: ProfileBentoCard[] }> {
  return {
    cards: response.cards || [],
    isDefault: response.is_default,
  }
}
