import { computed, reactive, ref } from 'vue'
import { useLocalStorage } from '@vueuse/core'
import {
  activeCommunities,
  getActiveCommunity,
  getCommunity,
  navigationCommunities,
} from './communities'
import { session } from './session'

const selectedCommunityId = useLocalStorage<string | null>('gameplan:communityId', null)
const routeCommunityId = ref<string | null>(null)

const joinedCommunityId = computed(() => {
  if (selectedCommunityId.value && getActiveCommunity(selectedCommunityId.value)) {
    return selectedCommunityId.value
  }

  return activeCommunities.value[0]?.name ?? null
})

const communityId = computed(() => {
  if (routeCommunityId.value && getCommunity(routeCommunityId.value)) {
    return routeCommunityId.value
  }

  if (session.canBrowsePublicWeb) {
    return navigationCommunities.value[0]?.name ?? null
  }

  return joinedCommunityId.value
})

const communityDoc = computed(() => {
  if (!communityId.value) {
    return null
  }

  return getCommunity(communityId.value) ?? null
})

export const communityState = reactive({
  id: communityId,
  joinedId: joinedCommunityId,
  doc: communityDoc,
  change(communityId?: string | null) {
    selectedCommunityId.value = communityId ? String(communityId) : null
    routeCommunityId.value = selectedCommunityId.value
  },
  scope(communityId?: string | null) {
    routeCommunityId.value = communityId ? String(communityId) : null
  },
})
