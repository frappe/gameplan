<template>
  <div v-if="profile" class="min-h-full bg-surface-base">
    <PageHeader>
      <Breadcrumbs class="h-7" :items="profileBreadcrumbs">
        <template #suffix="{ item }">
          <Button
            v-if="isOwnProfile && item.isPageTitle"
            variant="ghost"
            size="sm"
            icon="lucide-edit"
            label="Edit profile"
            tooltip="Edit profile"
            class="ml-1 shrink-0"
            @click="showSettingsDialog('Profile')"
          />
        </template>
      </Breadcrumbs>
    </PageHeader>

    <div class="mx-auto w-full max-w-[860px] px-3 py-4 sm:px-5 sm:py-6">
      <div class="mb-4 flex items-center justify-between gap-3">
        <TabButtons
          :buttons="[{ label: 'Profile' }, { label: 'Posts' }, { label: 'Replies' }]"
          v-model="activeTab"
        />
        <Button
          v-if="isOwnProfile && activeTab === 'Profile'"
          class="shrink-0"
          icon-left="lucide-layout-dashboard"
          :route="{ name: 'ProfileCustomize' }"
        >
          Customize
        </Button>
      </div>

      <router-view
        :profile="profileChildResource"
        :bento-cards="profileBentoCards"
        :bento-cards-loaded="profileBentoLoaded"
        :is-own-profile="isOwnProfile"
      />
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { PageHeader, Breadcrumbs, Button, TabButtons, useDoc, usePageMeta } from 'frappe-ui'
import { showSettingsDialog } from '@/components/Settings'
import { getProfileBentoCards } from '@/components/ProfileBento/profileBentoSource'
import type { ProfileBentoCard } from '@/components/ProfileBento/types'
import { useSessionUser } from '@/data/users'
import type { GPUserProfile } from '@/types/doctypes'

defineOptions({
  name: 'PersonProfile',
})

const props = defineProps<{
  personId: string
}>()

const route = useRoute()
const router = useRouter()
const sessionUser = useSessionUser()
const personId = computed(() => {
  return props.personId || route.params.personId?.toString() || 'missing-profile'
})

const profileResource = useDoc<GPUserProfile>({
  doctype: 'GP User Profile',
  name: personId,
})

const profile = computed(() => profileResource.doc)
const profileChildResource = computed(() => ({
  ...profileResource,
  doc: profile.value,
}))
const isOwnProfile = computed(() => profile.value?.user === sessionUser.name)

const profileBentoCards = ref<ProfileBentoCard[]>([])
const profileBentoLoaded = ref(false)
let profileBentoLoadId = 0
let loadedProfileBentoName = ''

const profileBreadcrumbs = computed(() => [
  { label: 'People', route: { name: 'People' } },
  {
    label: profile.value?.full_name || 'Profile',
    route: { name: 'PersonProfileProfile', params: { personId: personId.value } },
    isPageTitle: true,
  },
])

const activeTab = computed({
  get() {
    return (
      {
        PersonProfileProfile: 'Profile',
        PersonProfilePosts: 'Posts',
        PersonProfileReplies: 'Replies',
      }[route.name as string] || 'Profile'
    )
  },
  set(value) {
    let profileRoute = {
      Profile: { name: 'PersonProfileProfile' },
      Posts: { name: 'PersonProfilePosts' },
      Replies: { name: 'PersonProfileReplies' },
    }[value]
    if (profileRoute) {
      router.push(profileRoute)
    }
  },
})

watch(
  () => profile.value?.name,
  () => loadProfileBentoCards(profile.value?.name),
  { immediate: true },
)

async function loadProfileBentoCards(profileName?: string) {
  let loadId = ++profileBentoLoadId
  if (!profileName) {
    loadedProfileBentoName = ''
    profileBentoCards.value = []
    profileBentoLoaded.value = false
    return
  }

  if (profileName !== loadedProfileBentoName) {
    profileBentoCards.value = []
    profileBentoLoaded.value = false
  }

  let loadResult = await getProfileBentoCards(profileName)
  if (loadId === profileBentoLoadId) {
    loadedProfileBentoName = profileName
    profileBentoCards.value = loadResult.cards
    profileBentoLoaded.value = true
  }
}

usePageMeta(() => {
  return {
    title: [profile.value?.full_name || '', 'Profile'].join(' | '),
  }
})
</script>
