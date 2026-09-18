<template>
  <SettingsHeader>
    <div class="w-full max-w-[800px]">
      <!-- Selected community: back button, title, and the Spaces/Members switcher. On
           phones this row moves into the dialog's own header bar (the Teleport below), so
           there is one header, not two. -->
      <template v-if="selectedCommunityId">
        <Teleport v-if="isPhone" defer to="#settings-mobile-bar">
          <Button
            variant="ghost"
            icon="lucide-arrow-left"
            label="Back to communities"
            @click="showCommunities"
          />
          <h2 class="min-w-0 flex-1 truncate text-lg-medium text-ink-gray-8">
            {{ selectedCommunity?.title || 'Community' }}
          </h2>
          <Select variant="ghost" v-if="selectedCommunity" :options="viewButtons" v-model="view" />
        </Teleport>
        <div class="flex items-center gap-2 max-sm:hidden">
          <Button
            variant="subtle"
            size="xs"
            icon="lucide-chevron-left"
            label="Back to communities"
            @click="showCommunities"
          />
          <h2 class="min-w-0 truncate text-lg-semibold text-ink-gray-8">
            {{ selectedCommunity?.title || 'Community' }}
          </h2>
          <Select variant="ghost" v-if="selectedCommunity" :options="viewButtons" v-model="view" />
        </div>

        <!-- pb-3 on both controls keeps the gap to their sticky ListHeader,
             which lives at the top of the scroll viewport in each list. -->
        <CommunitySpacesListControls
          v-if="selectedCommunity && view === 'spaces'"
          class="mt-4 pb-3"
          :community-id="selectedCommunityId"
          v-model:search="spaceSearch"
          v-model:visibility-filter="spaceFilter"
        >
          <template #action>
            <!-- Icon alone on phones, where the search needs the width. -->
            <Button
              v-if="canCreateSpace"
              icon-left="lucide-plus"
              class="max-sm:hidden"
              @click="openNewSpaceDialog"
            >
              New space
            </Button>
            <Button
              v-if="canCreateSpace"
              icon="lucide-plus"
              label="New space"
              class="sm:hidden"
              @click="openNewSpaceDialog"
            />
          </template>
        </CommunitySpacesListControls>

        <CommunityMembersListControls
          v-if="selectedCommunity && view === 'members'"
          class="mt-4 pb-3"
          v-model:search="memberSearch"
        >
          <template #action>
            <Button
              v-if="canManageSelectedCommunity"
              icon-left="lucide-plus"
              class="max-sm:hidden"
              :disabled="Boolean(selectedCommunity.archived_at)"
              @click="showAddMembers = true"
            >
              Add members
            </Button>
            <Button
              v-if="canManageSelectedCommunity"
              icon="lucide-plus"
              label="Add members"
              class="sm:hidden"
              :disabled="Boolean(selectedCommunity.archived_at)"
              @click="showAddMembers = true"
            />
          </template>
        </CommunityMembersListControls>
      </template>

      <!-- Communities list -->
      <template v-else>
        <h2 class="text-lg-semibold text-ink-gray-8 max-sm:hidden">Communities</h2>

        <!-- pb-3 keeps the gap to the column header, which lives at the top
             of the scroll viewport (a sticky ListHeader in CommunitiesList)
             instead of being duplicated here. -->
        <!-- One line on every width: on phones the search box gives up its width and the
             two actions are icons. -->
        <div class="mt-4 flex items-center justify-between gap-3 pb-3">
          <CommunitiesListFilters
            class="min-w-0 flex-1 sm:flex-none"
            v-model:search="search"
            v-model:visibility-filter="visibilityFilter"
          />
          <div class="flex shrink-0 items-center gap-2">
            <!-- Which communities sit in the sidebar, and in what order, is the
                 other half of joining one; the same dialog the app menu opens. -->
            <!-- Beside "New community" the header has no room to spare, so a
                 manager gets the icon alone and the label in a tooltip. -->
            <Button
              :icon="showNewCommunityButton || isPhone ? 'lucide-settings-2' : undefined"
              :icon-left="showNewCommunityButton || isPhone ? undefined : 'lucide-settings-2'"
              :tooltip="showNewCommunityButton || isPhone ? 'Customize sidebar' : undefined"
              label="Customize sidebar"
              @click="customizeSidebar"
            />
            <Button
              v-if="showNewCommunityButton"
              icon-left="lucide-plus"
              class="max-sm:hidden"
              @click="newCommunityDialog = true"
            >
              New community
            </Button>
            <Button
              v-if="showNewCommunityButton"
              icon="lucide-plus"
              label="New community"
              class="sm:hidden"
              @click="newCommunityDialog = true"
            />
          </div>
        </div>
      </template>
    </div>
  </SettingsHeader>

  <NewCommunityDialog v-model="newCommunityDialog" @created="openCommunitySpaces" />
  <!-- Desktop has AppRail's instance. Phones have no rail, and the dialog has to mount
       inside this settings dialog: frappe-ui Dialogs stack in mount order, so one mounted
       by the layout would open underneath. -->
  <CustomizeSidebarDialog v-if="isPhone" v-model="showCustomizeSidebarDialog" />
  <NewSpaceDialog v-model="newSpaceDialog" :locked-community-id="selectedCommunityId || ''" />

  <SettingsBody>
    <div class="w-full max-w-[800px] pt-0">
      <template v-if="selectedCommunityId">
        <ConfigureEmptyState
          v-if="!selectedCommunity"
          icon="lucide-circle-alert"
          title="Community not found"
          description="This community may have been archived, deleted, or moved."
        >
          <template #actions>
            <Button @click="showCommunities">View communities</Button>
          </template>
        </ConfigureEmptyState>

        <template v-else>
          <CommunityMembersList
            v-if="view === 'members'"
            :community="selectedCommunity"
            :can-manage="canManageSelectedCommunity"
            :show-controls="false"
            v-model:search="memberSearch"
            v-model:show-add-dialog="showAddMembers"
          />
          <CommunitySpacesList
            v-else
            :community-id="selectedCommunityId"
            :can-create-space="canCreateSpace"
            :show-controls="false"
            v-model:search="spaceSearch"
            v-model:visibility-filter="spaceFilter"
            @create-space="openNewSpaceDialog"
          />
        </template>
      </template>

      <CommunitiesList
        v-else
        :show-controls="false"
        v-model:search="search"
        v-model:visibility-filter="visibilityFilter"
        @create-community="newCommunityDialog = true"
        @view-spaces="openCommunitySpaces"
        @view-members="openCommunityMembers"
        @community-merged="openCommunitySpaces"
      />
    </div>
  </SettingsBody>
</template>

<script setup lang="ts">
// Declared so the parent's @close-dialog isn't treated as a failed attribute
// fallthrough (this component renders a fragment); it simply isn't emitted here.
defineEmits<{ (e: 'close-dialog'): void }>()
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, SettingsBody, SettingsHeader, Select } from 'frappe-ui'
import NewSpaceDialog from '@/components/NewSpaceDialog.vue'
import { useMediaQuery } from '@vueuse/core'
import CustomizeSidebarDialog from '@/components/AppRail/CustomizeSidebarDialog.vue'
import {
  openCustomizeSidebarDialog,
  showCustomizeSidebarDialog,
} from '@/components/AppRail/customizeSidebar'
import { mobileBarTaken } from './index'
import { communities } from '@/data/communities'
import { useSessionUser } from '@/data/users'
import { canManageCommunity, isGlobalAdmin } from '@/utils/permissions'
import CommunitiesList from '@/pages/Configure/CommunitiesList.vue'
import CommunitiesListFilters from '@/pages/Configure/CommunitiesListFilters.vue'
import ConfigureEmptyState from '@/pages/Configure/ConfigureEmptyState.vue'
import CommunityMembersList from '@/pages/Configure/CommunityMembersList.vue'
import CommunityMembersListControls from '@/pages/Configure/CommunityMembersListControls.vue'
import CommunitySpacesList from '@/pages/Configure/CommunitySpacesList.vue'
import CommunitySpacesListControls from '@/pages/Configure/CommunitySpacesListControls.vue'
import NewCommunityDialog from '@/pages/Configure/NewCommunityDialog.vue'

type CommunityView = 'spaces' | 'members'

const route = useRoute()
const router = useRouter()
const sessionUser = useSessionUser()

// The selected community and its Spaces/Users view are derived from the URL, so
// entering a community, switching views, and going "back" are all real router
// navigations (browser/OS back button included). The list is shown when no
// community is in the URL (the plain /settings/communities tab).
const selectedCommunityId = computed(() =>
  route.name === 'SettingsCommunity' ? String(route.params.communityId) : null,
)
const view = computed<CommunityView>({
  get: () => (route.params.view === 'members' ? 'members' : 'spaces'),
  set: (nextView) => {
    if (!selectedCommunityId.value) return
    router.push({
      name: 'SettingsCommunity',
      params: { communityId: selectedCommunityId.value, view: nextView },
    })
  },
})
// Filter state; controls live in the fixed header for each view.
const search = ref('')
const visibilityFilter = ref<'All' | 'Public' | 'Private' | 'Archived'>('All')
const spaceSearch = ref('')
const spaceFilter = ref<'All' | 'Public' | 'Private' | 'Archived'>('All')
const memberSearch = ref('')
const showAddMembers = ref(false)
const newSpaceDialog = ref(false)
const newCommunityDialog = ref(false)

// The dialog itself is mounted once in AppRail; this only flips its shared flag.
function customizeSidebar() {
  openCustomizeSidebarDialog()
}

// Same breakpoint the templates use for their sm: variants; decides icon-only buttons
// and whether the community header rides in the dialog's phone bar.
const isPhone = useMediaQuery('(max-width: 639px)')
watch(
  () => Boolean(isPhone.value && selectedCommunityId.value),
  (taken) => (mobileBarTaken.value = taken),
  { immediate: true },
)
onBeforeUnmount(() => (mobileBarTaken.value = false))

const viewButtons = [
  { label: 'Spaces', value: 'spaces' },
  { label: 'Members', value: 'members' },
]

const selectedCommunity = computed(() => {
  if (!selectedCommunityId.value) return null
  return (communities.data || []).find((community) => community.name === selectedCommunityId.value)
})
const canManageSelectedCommunity = computed(() =>
  canManageCommunity(selectedCommunity.value, sessionUser),
)
const showNewCommunityButton = computed(
  () => !selectedCommunityId.value && isGlobalAdmin(sessionUser),
)
const canCreateSpace = computed(() =>
  Boolean(
    selectedCommunity.value &&
    canManageSelectedCommunity.value &&
    !selectedCommunity.value.archived_at,
  ),
)
function openCommunitySpaces(communityId: string) {
  router.push({ name: 'SettingsCommunity', params: { communityId, view: 'spaces' } })
}

function openCommunityMembers(communityId: string) {
  router.push({ name: 'SettingsCommunity', params: { communityId, view: 'members' } })
}

function showCommunities() {
  router.push({ name: 'SettingsTab', params: { tab: 'communities' } })
}

// Clear a community's search/filter state when entering, leaving, or switching
// views, so stale filters never carry over between communities.
function resetCommunityFilters() {
  spaceSearch.value = ''
  spaceFilter.value = 'All'
  memberSearch.value = ''
}
watch([selectedCommunityId, view], resetCommunityFilters)

function openNewSpaceDialog() {
  if (!canCreateSpace.value) return
  newSpaceDialog.value = true
}
</script>
