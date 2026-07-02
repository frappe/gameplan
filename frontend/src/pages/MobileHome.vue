<template>
  <MobileHeader title="Communities">
    <template #left>
      <GameplanLogo class="ml-1 size-7 rounded-[7px]" />
    </template>
    <template #right>
      <Button
        v-if="manageableCommunities.length"
        variant="ghost"
        size="md"
        :loading="updateJoinedTeams.loading"
        @click="toggleEditMode"
      >
        {{ editMode ? 'Done' : 'Edit' }}
      </Button>
    </template>
  </MobileHeader>

  <div class="pb-24 pt-5">
    <nav v-if="visibleCommunities.length">
      <MobileListRow
        v-for="(community, index) in visibleCommunities"
        :key="community.name"
        height="fixed"
        :border="index > 0"
        @click="onCommunityClick(community.name)"
      >
        <template #icon>
          <CommunityImage :community="community" class="size-7 bg-surface-gray-1" />
        </template>
        {{ community.title }}
        <template #trailing>
          <span
            v-if="editMode && community.is_private"
            class="size-4 shrink-0 text-ink-gray-4 lucide-lock"
            aria-hidden="true"
          />
          <span
            v-if="!editMode && getCommunityUnreadCount(community.name) > 0"
            class="shrink-0 text-md text-ink-gray-5"
          >
            {{ getCommunityUnreadCount(community.name) }}
          </span>
          <Switch
            v-if="editMode"
            size="sm"
            :label="community.title"
            :model-value="isSelected(community.name)"
            class="shrink-0 [&_label]:sr-only"
            @click.stop
            @update:model-value="setCommunitySelected(community.name, $event)"
          />
        </template>
      </MobileListRow>
    </nav>

    <div v-else class="px-3 py-10 text-base leading-relaxed text-ink-gray-5">
      No communities available. Ask an admin.
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Button, Switch, toast, useCall, usePageMeta } from 'frappe-ui'
import CommunityImage from '@/components/CommunityImage.vue'
import GameplanLogo from '@/components/GameplanLogo.vue'
import MobileHeader from '@/components/MobileHeader.vue'
import MobileListRow from '@/components/MobileListRow.vue'
import {
  activeCommunities,
  availableCommunities,
  communities,
  navigationCommunities,
} from '@/data/communities'
import { communityState } from '@/data/communityState'
import { getSpaceUnreadCount, spaces } from '@/data/spaces'
import { session } from '@/data/session'

const router = useRouter()
const editMode = ref(false)
const selectedCommunityNames = ref<string[]>([])

const manageableCommunities = computed(() => {
  if (session.canBrowsePublicWeb) return []

  return availableCommunities.value.filter((community) => !community.archived_at)
})

const visibleCommunities = computed(() => {
  return editMode.value ? manageableCommunities.value : navigationCommunities.value
})

const updateJoinedTeams = useCall<string[], { teams: string[] }>({
  url: '/api/v2/method/GP Team/update_joined_teams',
  method: 'POST',
  immediate: false,
})

function onCommunityClick(communityId: string) {
  if (editMode.value) {
    toggleCommunity(communityId)
    return
  }

  if (session.canBrowsePublicWeb) {
    communityState.scope(communityId)
  } else {
    communityState.change(communityId)
  }
  router.push({ name: 'Discussions', params: { communityId } })
}

async function toggleEditMode() {
  if (!editMode.value) {
    selectedCommunityNames.value = activeCommunities.value.map((community) => community.name)
    editMode.value = true
    return
  }

  await save()
}

function isSelected(communityName: string) {
  return selectedCommunityNames.value.includes(communityName)
}

function toggleCommunity(communityName: string) {
  if (isSelected(communityName)) {
    selectedCommunityNames.value = selectedCommunityNames.value.filter(
      (name) => name !== communityName,
    )
  } else {
    selectedCommunityNames.value = [...selectedCommunityNames.value, communityName]
  }
}

function setCommunitySelected(communityName: string, selected: boolean) {
  if (selected === isSelected(communityName)) return
  toggleCommunity(communityName)
}

async function save() {
  if (selectedCommunityNames.value.length === 0) {
    toast.error('Select at least one community')
    return
  }

  let previousCommunityId = communityState.id

  try {
    await updateJoinedTeams.submit({ teams: selectedCommunityNames.value })
    await communities.reload()

    if (previousCommunityId && !selectedCommunityNames.value.includes(previousCommunityId)) {
      communityState.change(activeCommunities.value[0]?.name ?? null)
    }

    editMode.value = false
    toast.success('Communities updated')
  } catch {
    toast.error('Failed to update communities')
  }
}

function getCommunityUnreadCount(communityId: string) {
  return (spaces.data || [])
    .filter((space) => !space.archived_at && space.team === communityId)
    .reduce((total, space) => total + getSpaceUnreadCount(space.name), 0)
}

usePageMeta(() => ({ title: 'Communities' }))
</script>
