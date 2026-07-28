<template>
  <SettingsHeader>
    <!-- pb-3 keeps the 0.75rem gap to the column header, which now lives at the
         top of the scroll viewport (sticky) instead of inside this fixed region. -->
    <div class="pb-3">
      <div class="flex flex-col gap-4">
        <h2 class="text-lg-semibold text-ink-gray-8">Users</h2>
        <div class="flex items-center justify-between gap-3">
          <TextInput
            class="w-72"
            placeholder="Search by name or email"
            @input="search = $event.target.value"
            :debounce="300"
          >
            <template #prefix>
              <span class="lucide-search h-4 w-4 text-ink-gray-4" />
            </template>
          </TextInput>
          <Button icon-left="lucide-plus" @click="showInviteDialog = true">Invite</Button>
        </div>
      </div>

      <button
        v-if="pendingInvites.data?.length"
        class="mt-2 flex w-full items-center justify-between gap-3 rounded bg-surface-gray-2 px-3 py-2 text-left transition-colors hover:bg-surface-gray-3"
        @click="showInviteDialog = true"
      >
        <span class="flex items-center gap-2 text-base text-ink-gray-7">
          <span class="lucide-mail h-4 w-4 text-ink-gray-5" />
          {{ pendingInvitesLabel }}
        </span>
        <span class="text-base text-ink-gray-6">View</span>
      </button>
    </div>
  </SettingsHeader>

  <SettingsBody>
    <List :columns="['minmax(0,1fr)', '12.5rem', '7.5rem', '2rem']" :row-height="60">
      <!-- Sticky at the viewport top — it rests exactly where it pins, so it
           never visibly moves; the bg covers rows scrolling beneath it. -->
      <ListHeader class="sticky top-0 z-10 bg-surface-elevation-1">
        <ListHeaderCellSort :direction="directionFor('name')" @click="toggleSort('name')">
          User
          <template #suffix="{ direction }">
            <span class="size-3.5 text-ink-gray-5" :class="sortIcon(direction)" />
          </template>
        </ListHeaderCellSort>
        <ListHeaderCellSort :direction="directionFor('role')" @click="toggleSort('role')">
          Role
          <template #suffix="{ direction }">
            <span class="size-3.5 text-ink-gray-5" :class="sortIcon(direction)" />
          </template>
        </ListHeaderCellSort>
        <ListHeaderCellSort :direction="directionFor('creation')" @click="toggleSort('creation')">
          User since
          <template #suffix="{ direction }">
            <span class="size-3.5 text-ink-gray-5" :class="sortIcon(direction)" />
          </template>
        </ListHeaderCellSort>
        <ListHeaderCell />
      </ListHeader>

      <!-- Virtualized: only the rows in/near the viewport mount, so a large team
           never instantiates hundreds of role Selects at once. -->
      <ListRows :items="filteredUsers" virtual v-slot="{ item: user }">
        <ListRow>
          <ListCell>
            <UserAvatar :user="user.name" size="xl" />
            <div class="ml-3 min-w-0">
              <div class="truncate text-base text-ink-gray-8">
                {{ user.full_name }}
              </div>
              <div class="mt-1 truncate text-base text-ink-gray-6">
                {{ user.email }}
              </div>
            </div>
          </ListCell>
          <ListCell>
            <Select
              placeholder="Role"
              :options="roleOptions"
              :model-value="user.role"
              @update:model-value="(role) => onRoleChange(user, role)"
            />
          </ListCell>
          <ListCell class="text-base text-ink-gray-6">
            <span v-if="user.creation">{{ getMemberSince(user) }}</span>
          </ListCell>
          <ListCell class="justify-end">
            <Button
              variant="ghost"
              icon="lucide-trash-2"
              :label="`Disable ${user.full_name}`"
              @click="disableUser(user)"
            />
          </ListCell>
        </ListRow>
      </ListRows>
    </List>
  </SettingsBody>

  <Dialog v-model:open="showInviteDialog">
    <InvitePeople />
  </Dialog>
</template>
<script setup lang="ts">
// Declared so the parent's @close-dialog isn't treated as a failed attribute
// fallthrough (this component renders a fragment); it simply isn't emitted here.
defineEmits<{ (e: 'close-dialog'): void }>()
import { computed, ref, watch } from 'vue'
import {
  Button,
  Dialog,
  SettingsBody,
  SettingsHeader,
  Select,
  dialog,
  dayjsLocal,
  useCall,
  useList,
} from 'frappe-ui'
import {
  List,
  ListCell,
  ListHeader,
  ListHeaderCell,
  ListHeaderCellSort,
  ListRow,
  ListRows,
} from 'frappe-ui/list'
import InvitePeople from './InvitePeople.vue'
import { users, activeUsers, updateUserInfo, type UserInfo } from '@/data/users'
import { GPInvitation } from '@/types/doctypes'

type SortField = 'name' | 'role' | 'creation'
type SortDirection = 'asc' | 'desc'
type UserRow = (typeof activeUsers.value)[number]

const roleOptions = [
  { label: 'Admin', value: 'Gameplan Admin', icon: 'lucide-shield-check' },
  { label: 'User', value: 'Gameplan Member', icon: 'lucide-user' },
  { label: 'Guest', value: 'Gameplan Guest', icon: 'lucide-user-lock' },
]

// Index used to rank roles (Admin first) when sorting by role.
const roleRank: Record<string, number> = Object.fromEntries(
  roleOptions.map((option, index) => [option.value, index]),
)

const search = ref('')
const sortField = ref<SortField>('name')
const sortDirection = ref<SortDirection>('asc')
const showInviteDialog = ref(false)

const pendingInvites = useList<GPInvitation>({
  doctype: 'GP Invitation',
  fields: ['name'],
  filters: { status: 'Pending' },
  cacheKey: 'pending-invitations',
})
const pendingInvitesLabel = computed(() => {
  const count = pendingInvites.data?.length ?? 0
  return `${count} pending invite${count === 1 ? '' : 's'}`
})

// Invites are sent/revoked inside the dialog, so refresh the count on close.
watch(showInviteDialog, (open, wasOpen) => {
  if (wasOpen && !open) pendingInvites.reload()
})

// `users` is a useCall resource (no setData); refetch after mutations so the
// list — role labels and membership — reflects the server-side change.
//
// change_user_role and disable_user are both GP User Profile doc methods, so
// their URLs are keyed on the target profile. `targetProfile` is swapped in
// per row (set right before submit) rather than going through a full useDoc,
// since neither call needs the target's doc data loaded — only the ability
// to invoke a method on it.
const targetProfile = ref('')
function profileMethodUrl(method: string) {
  return computed(() => `/api/v2/document/GP User Profile/${targetProfile.value}/method/${method}`)
}
const changeUserRoleCall = useCall<UserInfo, { role: string }>({
  url: profileMethodUrl('change_user_role'),
  method: 'POST',
  immediate: false,
  onSuccess: updateUserInfo,
})
const disableUserCall = useCall<unknown>({
  url: profileMethodUrl('disable_user'),
  method: 'POST',
  immediate: false,
  onSuccess: () => users.reload(),
})

const filteredUsers = computed(() => {
  let list = activeUsers.value
  if (search.value) {
    const term = search.value.toLowerCase()
    list = list.filter(
      (user) =>
        user.name.toLowerCase().includes(term) || user.full_name.toLowerCase().includes(term),
    )
  }
  return [...list].sort(compareUsers)
})

function toggleSort(field: SortField) {
  if (sortField.value === field) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
    return
  }

  sortField.value = field
  sortDirection.value = defaultSortDirection(field)
}

function directionFor(field: SortField) {
  return sortField.value === field ? sortDirection.value : null
}

function compareUsers(a: UserRow, b: UserRow) {
  let result = 0
  if (sortField.value === 'role') {
    const rankA = roleRank[a.role] ?? Number.MAX_SAFE_INTEGER
    const rankB = roleRank[b.role] ?? Number.MAX_SAFE_INTEGER
    result = rankA - rankB
  } else if (sortField.value === 'creation') {
    result = (a.creation || '').localeCompare(b.creation || '')
  } else {
    result = (a.full_name || '').localeCompare(b.full_name || '')
  }

  return sortDirection.value === 'asc' ? result : -result
}

function defaultSortDirection(field: SortField): SortDirection {
  return field === 'creation' ? 'desc' : 'asc'
}

function sortIcon(direction: SortDirection | null) {
  if (!direction) return 'lucide-arrow-up-down'
  return direction === 'asc' ? 'lucide-arrow-up' : 'lucide-arrow-down'
}

function getMemberSince(user: UserRow) {
  return dayjsLocal(user.creation).format('MMM YYYY')
}

function changeUserRole(user: UserRow, role: string) {
  dialog.confirm({
    title: 'Change Role',
    message: `Are you sure you want to change ${user.full_name}'s role to ${role}?`,
    confirmLabel: 'Change Role',
    onConfirm: () => {
      targetProfile.value = user.user_profile
      changeUserRoleCall.submit({ role })
    },
  })
}

function onRoleChange(user: UserRow, role: unknown) {
  // Select emits SelectOptionValue | undefined; narrow to the string role id.
  if (typeof role !== 'string') return
  const isValidRole = roleOptions.some((option) => option.value === role)
  if (!isValidRole || role === user.role) return
  changeUserRole(user, role)
}

function disableUser(user: UserRow) {
  dialog.danger({
    title: 'Disable user',
    message: `${user.full_name} (${user.email}) will be disabled and can no longer sign in to Gameplan. You can re-enable them later from the Frappe admin.`,
    confirmLabel: 'Disable',
    onConfirm: () => {
      targetProfile.value = user.user_profile
      disableUserCall.submit()
    },
  })
}
</script>
