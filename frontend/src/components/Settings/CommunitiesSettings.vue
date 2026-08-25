<template>
  <SettingsHeader>
    <div class="w-full max-w-[800px]">
      <!-- Selected community: back button, title, and the Spaces/Members switcher. -->
      <template v-if="selectedCommunityId">
        <div class="flex items-center gap-2">
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

        <!-- md:pb-3 on both controls keeps the gap to their sticky ListHeader,
             which lives at the top of the scroll viewport in each list. -->
        <CommunitySpacesListControls
          v-if="selectedCommunity && view === 'spaces'"
          class="mt-4 md:pb-3"
          :community-id="selectedCommunityId"
          v-model:search="spaceSearch"
          v-model:visibility-filter="spaceFilter"
        >
          <template #action>
            <Button v-if="canCreateSpace" icon-left="lucide-plus" @click="openNewSpaceDialog">
              New space
            </Button>
          </template>
        </CommunitySpacesListControls>

        <CommunityMembersListControls
          v-if="selectedCommunity && view === 'members'"
          class="mt-4 md:pb-3"
          v-model:search="memberSearch"
        >
          <template #action>
            <Button
              v-if="canManageSelectedCommunity"
              icon-left="lucide-plus"
              :disabled="Boolean(selectedCommunity.archived_at)"
              @click="showAddMembers = true"
            >
              Add members
            </Button>
          </template>
        </CommunityMembersListControls>
      </template>

      <!-- Communities list -->
      <template v-else>
        <h2 class="text-lg-semibold text-ink-gray-8">Communities</h2>

        <!-- md:pb-3 keeps the gap to the column header, which lives at the top
             of the scroll viewport (a sticky ListHeader in CommunitiesList)
             instead of being duplicated here. -->
        <div class="mt-4 flex items-center justify-between gap-3 md:pb-3">
          <CommunitiesListFilters
            v-model:search="search"
            v-model:visibility-filter="visibilityFilter"
          />
          <div class="flex shrink-0 items-center gap-2">
            <!-- Which communities sit in the sidebar, and in what order, is the
                 other half of joining one; the same dialog the app menu opens. -->
            <Button icon-left="lucide-settings-2" @click="customizeSidebar">
              Customize sidebar
            </Button>
            <Button
              v-if="showNewCommunityButton"
              icon-left="lucide-plus"
              @click="newCommunityDialog = true"
            >
              New community
            </Button>
          </div>
        </div>
      </template>
    </div>
  </SettingsHeader>

  <NewCommunityDialog v-model="newCommunityDialog" @created="openCommunitySpaces" />
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
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, SettingsBody, SettingsHeader, Select } from 'frappe-ui'
import NewSpaceDialog from '@/components/NewSpaceDialog.vue'
import { openCustomizeSidebarDialog } from '@/components/AppRail/customizeSidebar'
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
