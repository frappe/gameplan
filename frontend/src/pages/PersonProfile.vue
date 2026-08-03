<template>
  <div v-if="profile" class="min-h-full bg-surface-base">
    <PageHeader>
      <Breadcrumbs class="h-7" :items="profileBreadcrumbs">
        <!-- Breadcrumbs renders `suffix` inside the crumb's router-link, so this
             click has to be kept from also following it — that navigation would
             land back on the profile and close the settings dialog immediately. -->
        <template #suffix="{ item }">
          <Button
            v-if="isOwnProfile && item.isPageTitle"
            variant="ghost"
            size="sm"
            icon="lucide-edit"
            label="Edit profile"
            tooltip="Edit profile"
            class="ml-1 shrink-0"
            @click.stop.prevent="showSettingsDialog('Profile')"
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
        <!-- Hidden below `md`, where the customize page refuses to open anyway. -->
        <Button
          v-if="isOwnProfile && activeTab === 'Profile'"
          class="hidden shrink-0 md:inline-flex"
          icon-left="lucide-layout-dashboard"
          :route="{ name: 'ProfileCustomize' }"
        >
          Customize
        </Button>
      </div>

      <router-view v-bind="routeProps" />
    </div>
  </div>

  <NotFound v-else-if="profileNotFound" />
</template>
<script setup lang="ts">
import { computed, inject, ref, watch } from 'vue'
import { routerViewLocationKey, useRoute, useRouter } from 'vue-router'
import { PageHeader, Breadcrumbs, Button, TabButtons, useDoc, usePageMeta } from 'frappe-ui'
import NotFound from '@/pages/NotFound.vue'
import { showSettingsDialog } from '@/components/Settings'
import { getProfileBentoCards } from '@/components/ProfileBento/profileBentoSource'
import { useProfileFieldEditing } from '@/components/ProfileBento/useProfileFieldEditing'
import type { ProfileBentoCard } from '@/components/ProfileBento/types'
import { useSessionUser } from '@/data/users'
import type { GPUserProfile } from '@/types/doctypes'

defineOptions({
  name: 'PersonProfile',
})

const props = defineProps<{
  personId: string
}>()

interface ProfileMethods {
  setImage: (data: { image: string | null }) => void
  setCoverImagePosition: (data: { position: number }) => void
}

const route = useRoute()
const router = useRouter()
const sessionUser = useSessionUser()
const personId = computed(() => {
  return props.personId || route.params.personId?.toString() || 'missing-profile'
})

const profileResource = useDoc<GPUserProfile, ProfileMethods>({
  doctype: 'GP User Profile',
  name: personId,
  methods: {
    setImage: 'set_image',
    setCoverImagePosition: 'set_cover_image_position',
  },
})

const profile = computed(() => profileResource.doc)
const profileChildResource = computed(() => ({
  ...profileResource,
  doc: profile.value,
}))
const isOwnProfile = computed(() => profile.value?.user === sessionUser.name)
// A profile that never loaded used to render an empty page; show the not-found
// state instead. `isFinished` keeps the first paint on the loading branch.
const profileNotFound = computed(() => {
  return !profile.value && (Boolean(profileResource.error) || profileResource.isFinished)
})

const profileBentoCards = ref<ProfileBentoCard[]>([])
const profileBentoLoaded = ref(false)
let profileBentoLoadId = 0
let loadedProfileBentoName = ''

const fieldEditor = useProfileFieldEditing({
  profile: profileResource,
  userId: () => (isOwnProfile.value && profile.value?.user) || '',
  enabled: () => isOwnProfile.value,
  onSaved: refreshProfile,
})

const profileBreadcrumbs = computed(() => [
  { label: 'People', route: { name: 'People' } },
  {
    label: profile.value?.full_name || 'Profile',
    route: { name: 'PersonProfileProfile', params: { personId: personId.value } },
    isPageTitle: true,
  },
])

/**
 * Which tab is on screen. Not the same as `route.name`: `App.vue` keeps this page
 * rendered behind the settings overlay with `<router-view :route>`, and there
 * `useRoute()` reports the /settings URL while the nested view still shows a
 * profile tab. A router-view provides the location it displays, so read that.
 */
const displayedRoute = inject(routerViewLocationKey)
const displayedRouteName = computed(() => displayedRoute?.value.name ?? route.name)

/**
 * Only the Profile tab takes the bento props. Posts and Replies render a single
 * root element, so anything they do not declare would land on it as an attribute.
 */
const routeProps = computed(() => {
  let baseProps = { profile: profileChildResource.value }
  if (displayedRouteName.value !== 'PersonProfileProfile') return baseProps
  return {
    ...baseProps,
    bentoCards: profileBentoCards.value,
    bentoCardsLoaded: profileBentoLoaded.value,
    isOwnProfile: isOwnProfile.value,
    fieldEditor: fieldEditor.value,
  }
})

const activeTab = computed({
  get() {
    return (
      {
        PersonProfileProfile: 'Profile',
        PersonProfilePosts: 'Posts',
        PersonProfileReplies: 'Replies',
      }[displayedRouteName.value as string] || 'Profile'
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

/**
 * Bound cards resolve their value on the server, so an inline edit is only
 * visible once the cards are read again. The profile doc comes along for the
 * header and for fields written through `User` rather than the profile.
 */
async function refreshProfile() {
  await Promise.all([profileResource.reload(), loadProfileBentoCards(profile.value?.name)])
}

usePageMeta(() => {
  return {
    title: [profile.value?.full_name || '', 'Profile'].join(' | '),
  }
})
</script>
