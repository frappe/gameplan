<template>
  <!-- No `title` prop: the header carries controls, so the panel keeps its own
       heading and hides it on phones, where the page header names the tab. -->
  <PanelHeader>
    <div class="w-full max-w-[800px]">
      <!-- Selected community: back button, title, and the Spaces/Members switcher.
           On a phone this is the page's own header (see below), so there is one
           header, not two. -->
      <template v-if="selectedCommunityId">
        <!-- The page header a phone would otherwise get from pages/SettingsPage.vue:
             back goes to the communities list rather than the More menu, and the
             community's own title and view switcher ride along. -->
        <PageHeaderMobile v-if="isPhone">
          <template #prefix>
            <!-- Walks history like every other page's back button, and falls back to
                 the communities list when there is none (a cold deep link). -->
            <PageHeaderBackButton
              label="Back to communities"
              :to="{ name: 'SettingsTab', params: { tab: 'communities' } }"
            />
          </template>
          <template #default>{{ selectedCommunity?.title || 'Community' }}</template>
          <template #suffix>
            <Select
              variant="ghost"
              v-if="selectedCommunity"
              :options="viewButtons"
              v-model="view"
            />
          </template>
        </PageHeaderMobile>
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
              :icon="isPhone ? 'lucide-plus' : undefined"
              :icon-left="isPhone ? undefined : 'lucide-plus'"
              label="New space"
              :disabled="!isOnline"
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
              :icon="isPhone ? 'lucide-plus' : undefined"
              :icon-left="isPhone ? undefined : 'lucide-plus'"
              label="Add members"
              :disabled="Boolean(selectedCommunity.archived_at) || !isOnline"
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
              :icon="isPhone ? 'lucide-plus' : undefined"
              :icon-left="isPhone ? undefined : 'lucide-plus'"
              label="New community"
              :disabled="!isOnline"
              @click="newCommunityDialog = true"
            />
          </div>
        </div>
      </template>
    </div>
  </PanelHeader>

  <NewCommunityDialog v-model="newCommunityDialog" @created="openCommunitySpaces" />
  <!-- Desktop has AppRail's instance. Phones have no rail, and the dialog has to mount
       inside this settings dialog: frappe-ui Dialogs stack in mount order, so one mounted
       by the layout would open underneath. -->
  <CustomizeSidebarDialog v-if="isPhone" v-model="showCustomizeSidebarDialog" />
  <NewSpaceDialog v-model="newSpaceDialog" :locked-community-id="selectedCommunityId || ''" />

  <PanelBody>
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
  </PanelBody>
</template>

<script setup lang="ts">
// Declared so the parent's @close-dialog isn't treated as a failed attribute
// fallthrough (this component renders a fragment); it simply isn't emitted here.
defineEmits<{ (e: 'close-dialog'): void }>()
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, PageHeaderBackButton, PageHeaderMobile, Select } from 'frappe-ui'
import NewSpaceDialog from '@/components/NewSpaceDialog.vue'
import CustomizeSidebarDialog from '@/components/AppRail/CustomizeSidebarDialog.vue'
import {
  openCustomizeSidebarDialog,
  showCustomizeSidebarDialog,
} from '@/components/AppRail/customizeSidebar'
import { panelOwnsPageHeader } from './index'
import PanelHeader from './PanelHeader.vue'
import PanelBody from './PanelBody.vue'
import { communities } from '@/data/communities'
import { useSessionUser } from '@/data/users'
import { canManageCommunity, isGlobalAdmin } from '@/utils/permissions'
import { isOnline } from '@/data/online'
import { useIsMobile } from '@/utils/useIsMobile'
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
    // replace, not push: the URL carries the view so it can be linked to, but
    // switching Spaces/Members inside one community is not navigation. Pushing it
    // stacked a history entry per toggle, so going back walked through the toggles
    // instead of leaving the community.
    router.replace({
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

// Decides icon-only buttons and, with a community open, that this panel draws the
// phone page header itself (back to the list, the community title, the switcher).
const isPhone = useIsMobile()
watch(
  () => Boolean(isPhone.value && selectedCommunityId.value),
  (owns) => (panelOwnsPageHeader.value = owns),
  { immediate: true },
)
onBeforeUnmount(() => (panelOwnsPageHeader.value = false))

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
