<template>
  <div
    v-if="showControls"
    class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
  >
    <div>
      <h2 class="text-lg-medium text-ink-gray-9">Members</h2>
      <p class="mt-1 text-base text-ink-gray-5">
        Members can access public spaces in this community.
      </p>
    </div>
    <Button
      v-if="canManage"
      icon-left="lucide-user-plus"
      :disabled="Boolean(community.archived_at)"
      @click="showAddDialog = true"
    >
      Add members
    </Button>
  </div>

  <CommunityMembersListControls v-if="showControls" v-model:search="search" />

  <List
    v-if="filteredMembers.length"
    :columns="['1.25rem', 'minmax(12rem,1fr)', 'minmax(12rem,1fr)', '8rem', '1.5rem']"
    class="max-md:list-cols-[1.25rem_minmax(0,1fr)]"
  >
    <!-- Sticky at the settings scroll-viewport top — it rests exactly where it
         pins, so it never visibly moves. -->
    <ListHeader class="sticky top-0 z-10 bg-surface-elevation-1 max-md:hidden">
      <ListHeaderCell class="col-span-2">Member</ListHeaderCell>
      <ListHeaderCell>Email</ListHeaderCell>
      <ListHeaderCell>Role</ListHeaderCell>
      <ListHeaderCell />
    </ListHeader>
    <MemberRow
      v-for="member in filteredMembers"
      :key="member.user"
      :community="community"
      :member="member"
      :can-manage="canManage"
    />
  </List>

  <ConfigureEmptyState
    v-else-if="!communityMembers.length"
    icon="lucide-users"
    title="No members yet"
    description="Add members so they can access public spaces here."
  >
    <template v-if="canManage" #actions>
      <Button
        icon-left="lucide-user-plus"
        :disabled="Boolean(community.archived_at)"
        @click="showAddDialog = true"
      >
        Add members
      </Button>
    </template>
  </ConfigureEmptyState>

  <ConfigureEmptyState
    v-else
    icon="lucide-search-x"
    title="No members match your search"
    description="Try a different name or email."
  >
    <template #actions>
      <Button @click="search = ''">Clear search</Button>
    </template>
  </ConfigureEmptyState>

  <CommunityGuestsList class="mt-10" :community="community" :can-manage="canManage" />

  <AddCommunityMembersDialog v-if="canManage" v-model="showAddDialog" :community="community" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button } from 'frappe-ui'
import { List, ListHeader, ListHeaderCell } from 'frappe-ui/list'
import type { Community } from '@/data/communities'
import { useUser } from '@/data/users'
import AddCommunityMembersDialog from './AddCommunityMembersDialog.vue'
import ConfigureEmptyState from './ConfigureEmptyState.vue'
import CommunityGuestsList from './CommunityGuestsList.vue'
import CommunityMembersListControls from './CommunityMembersListControls.vue'
import MemberRow from './MemberRow.vue'

const props = withDefaults(
  defineProps<{
    community: Community
    canManage: boolean
    // When false, the parent owns the title + controls; we only render the list.
    showControls?: boolean
  }>(),
  {
    showControls: true,
  },
)

// Models so the Settings dialog can hoist the search + Add users into its fixed
// header while this component still renders the list and owns the add dialog.
const search = defineModel<string>('search', { default: '' })
const showAddDialog = defineModel<boolean>('showAddDialog', { default: false })

const communityMembers = computed(() => {
  const seen = new Set<string>()

  return props.community.members
    .filter((member) => {
      if (!member.user || seen.has(member.user)) return false
      seen.add(member.user)
      return true
    })
    .sort((a, b) => {
      return useUser(a.user).full_name.localeCompare(useUser(b.user).full_name)
    })
})

const filteredMembers = computed(() => {
  const term = search.value.trim().toLowerCase()
  if (!term) return communityMembers.value
  return communityMembers.value.filter((member) => {
    const user = useUser(member.user)
    return (
      user.full_name.toLowerCase().includes(term) || (user.email || '').toLowerCase().includes(term)
    )
  })
})
</script>
