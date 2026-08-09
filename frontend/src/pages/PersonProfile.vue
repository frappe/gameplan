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

  <!-- Offline with no cached copy of this profile is not the same as a real 404: say so,
       and offer a retry instead of the dead-end "doesn't exist" page (US6). -->
  <OfflineContentFallback
    v-else-if="profileLoadFailure"
    class="mx-auto mt-16 max-w-md px-6"
    :title="profileLoadFailure.title"
    :message="profileLoadFailure.message"
    @retry="profileResource.reload()"
  />
  <NotFound v-else-if="profileNotFound" />
</template>
<script setup lang="ts">
import { computed, inject } from 'vue'
import { routerViewLocationKey, useRoute, useRouter } from 'vue-router'
import { PageHeader, Breadcrumbs, Button, TabButtons, useDoc, usePageMeta } from 'frappe-ui'
import NotFound from '@/pages/NotFound.vue'
import OfflineContentFallback from '@/components/OfflineContentFallback.vue'
import { isBrowserOffline, isNetworkError } from '@/offline'
import { showSettingsDialog } from '@/components/Settings'
import {
  resetProfileBentoCards,
  useProfileBento,
} from '@/components/ProfileBento/profileBentoSource'
import { confirmRestoreDefaultLayout } from '@/components/ProfileBento/restoreDefaultLayout'
import { useProfileFieldEditing } from '@/components/ProfileBento/useProfileFieldEditing'
import { useSessionUser, useUser } from '@/data/users'
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
  staleOnError: true,
})

const profile = computed(() => profileResource.doc)
const profileChildResource = computed(() => ({
  ...profileResource,
  doc: profile.value,
}))
const isOwnProfile = computed(() => profile.value?.user === sessionUser.name)

// Offline/network failure with nothing cached reads as a dead end otherwise indistinguishable
// from a real 404 (US6). A genuine 404 or permission error surfaces through `profileNotFound`
// below instead - `isNetworkError` only matches the TypeError a broken connection throws, not
// an HTTP-level error response.
const profileLoadFailure = computed(() => {
  if (profile.value || !profileResource.error) return null
  if (!isBrowserOffline() && !isNetworkError(profileResource.error)) return null
  return {
    title: "Can't load this profile while offline",
    message: "This profile isn't available offline.",
  }
})
// A profile that never loaded used to render an empty page; show the not-found
// state instead. `isFinished` keeps the first paint on the loading branch.
const profileNotFound = computed(() => {
  if (profileLoadFailure.value) return false
  return !profile.value && (Boolean(profileResource.error) || profileResource.isFinished)
})

// The name comes from the users store (User.full_name), not GP User Profile.full_name.
// The latter is a copy kept in sync by a server hook, so the cached profile doc keeps
// showing the old name after a rename; the store is refreshed by the users_changed event.
//
// The fallback is on `isPlaceholder`, not on a falsy name: an id the store does not know
// gets a placeholder whose full_name is the email's local part ("faris"), which is truthy.
// That happens on every cold load before the user list arrives, and permanently for anyone
// `get_user_info` skips (it only returns holders of a Gameplan role), so the profile doc's
// own copy of the name is the better answer there.
const displayName = computed(() => {
  let user = profile.value?.user
  let storeUser = user ? useUser(user) : null
  if (storeUser && !storeUser.isPlaceholder) return storeUser.full_name
  return profile.value?.full_name || storeUser?.full_name || ''
})

const bento = useProfileBento(() => profile.value?.name)

// Offline/network failure with nothing cached for this profile's bento cards - shown by
// PersonProfileProfile.vue instead of treating an empty response as "profile has no
// content" (US6). A non-network failure (permission error, 500) gets generic copy instead.
const bentoFailure = computed(() => {
  if (!bento.failed.value) return null
  const offline = isBrowserOffline() || isNetworkError(bento.error.value)
  return offline
    ? {
        title: "Can't load this while offline",
        message: "This profile's cards haven't been saved for offline use yet.",
      }
    : {
        title: 'Could not load this profile',
        message: 'Something went wrong while loading this page. Retry to try again.',
      }
})

const fieldEditor = useProfileFieldEditing({
  profile: profileResource,
  userId: () => (isOwnProfile.value && profile.value?.user) || '',
  enabled: () => isOwnProfile.value,
  onSaved: refreshProfile,
})

const profileBreadcrumbs = computed(() => [
  { label: 'People', route: { name: 'People' } },
  {
    label: displayName.value || 'Profile',
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
 * Each tab only takes the props it declares — an object prop it doesn't declare would
 * land on its single root element as an attribute (Profile doesn't need `personId`: it
 * reads bento data straight from this component's own `bento`; Posts/Replies use it to
 * key their own offline cache).
 */
const routeProps = computed(() => {
  if (displayedRouteName.value === 'PersonProfileProfile') {
    return {
      profile: profileChildResource.value,
      bentoCards: bento.cards.value,
      bentoCardsLoaded: bento.loaded.value,
      bentoIsDefault: bento.isDefault.value,
      bentoFailure: bentoFailure.value,
      isOwnProfile: isOwnProfile.value,
      fieldEditor: fieldEditor.value,
      // Listeners belong here rather than on the router-view for the same reason
      // the props do: only the Profile tab declares them.
      onRestoreDefaultLayout: restoreDefaultLayout,
      onRetryBento: () => bento.reload(),
    }
  }
  return {
    profile: profileChildResource.value,
    personId: personId.value,
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

/**
 * Offered from the empty state, where a saved layout that hides everything is
 * the likeliest reason the page is blank. The reset drops the stored rows; the
 * reload re-reads through `useProfileBento`'s per-profile resource, so a profile
 * switch mid-flight still wins (it would just be reloading a different resource).
 */
function restoreDefaultLayout() {
  confirmRestoreDefaultLayout(async () => {
    await resetProfileBentoCards()
    bento.reload()
  })
}

/**
 * Bound cards resolve their value on the server, so an inline edit is only
 * visible once the cards are read again. The profile doc comes along for the
 * header and for fields written through `User` rather than the profile.
 */
async function refreshProfile() {
  await Promise.all([profileResource.reload(), bento.reload()])
}

usePageMeta(() => {
  return {
    title: [displayName.value, 'Profile'].join(' | '),
  }
})
</script>
