<template>
  <Dialog v-model:open="show" size="md" bare @after-leave="reset">
    <!-- Fixed height: the body never resizes when the filter narrows, when rows
         are selected, or while the user list loads. dvh (not vh) because the
         mobile keyboard opens over this dialog the moment the search focuses. -->
    <div class="flex flex-col" style="height: min(560px, calc(100dvh - 8rem))">
      <div
        class="flex shrink-0 items-center justify-between border-b border-outline-gray-1 px-4 py-3"
      >
        <Dialog.Title as-child>
          <h2 class="text-lg font-medium text-ink-gray-9">Add members</h2>
        </Dialog.Title>
        <Dialog.Close as-child>
          <Button variant="ghost" label="Close" icon="lucide-x" />
        </Dialog.Close>
      </div>

      <!-- Named for the dialog itself: without a description reka logs a missing
           aria-describedby warning, and a screen reader gets only the title. -->
      <Dialog.Description as-child>
        <p class="sr-only">Search people and select who to add to {{ community.title }}.</p>
      </Dialog.Description>

      <div class="shrink-0 space-y-3 border-b border-outline-gray-1 px-4 py-3">
        <TextInput
          v-model="search"
          class="w-full"
          placeholder="Search by name or email"
          aria-label="Search people"
          autofocus
        >
          <template #prefix>
            <span class="lucide-search size-4 text-ink-gray-4" aria-hidden="true" />
          </template>
        </TextInput>

        <!-- Fixed height so the bar never changes the body's size. -->
        <div class="flex h-7 items-center justify-between gap-3">
          <Checkbox
            size="sm"
            :label="selectAllLabel"
            :model-value="allMatchesSelected"
            :indeterminate="someMatchesSelected"
            :disabled="!matches.length"
            @update:model-value="setMatchesSelected"
          />
          <div class="flex items-center gap-2">
            <span class="text-base text-ink-gray-5" aria-live="polite">
              {{ selected.length }} selected
            </span>
            <Button variant="ghost" size="sm" :disabled="!selected.length" @click="selected = []">
              Clear
            </Button>
          </div>
        </div>
      </div>

      <ScrollArea class="min-h-0 flex-1" viewport-class="px-2 py-2">
        <div v-if="!usersReady" class="space-y-1" role="status" aria-label="Loading people">
          <div v-for="n in 8" :key="n" class="flex h-13 items-center gap-3 px-3">
            <Skeleton class="size-7 shrink-0 rounded-full" />
            <div class="min-w-0 flex-1 space-y-2">
              <Skeleton class="h-3.5 w-40 rounded-4" />
              <Skeleton class="h-3 w-56 rounded-4" />
            </div>
          </div>
        </div>

        <EmptyStateBox v-else-if="!addableUsers.length" class="mt-6">
          <span class="lucide-users size-5 text-ink-gray-4" aria-hidden="true" />
          <div class="mt-2 text-p-sm text-ink-gray-5">
            Everyone already belongs to this community.
          </div>
        </EmptyStateBox>

        <EmptyStateBox v-else-if="!matches.length" class="mt-6">
          <span class="lucide-search-x size-5 text-ink-gray-4" aria-hidden="true" />
          <div class="mt-2 text-p-sm text-ink-gray-5">No people match your search.</div>
          <Button class="mt-3" @click="search = ''">Clear search</Button>
        </EmptyStateBox>

        <!-- list-row-px-2 matches the viewport's px-2 gutter, the same rule as
             Search.vue: row content and the checkbox column line up with the
             search field above.
             The row carries no hover or selected surface: the checkbox is the
             only selection state, so a 700-row list never washes grey. -->
        <List
          v-else
          selectable
          v-model:selection="selected"
          :columns="['auto', 'minmax(0,1fr)']"
          :row-height="52"
          divider="inset"
          aria-label="People you can add"
          class="list-row-px-2 sm:[&_[data-slot=list-row]:hover]:bg-transparent"
        >
          <!-- Virtualized: a full user list would otherwise mount one avatar per
               person at once. ListRows windows against the ScrollArea viewport. -->
          <ListRows :items="matches" virtual row-key="name" v-slot="{ item: user }">
            <ListRow :value="user.name" :aria-label="`${user.full_name}, ${user.email}`">
              <ListCell>
                <UserAvatar :user="user.name" size="lg" class="shrink-0" />
              </ListCell>
              <ListCell>
                <div class="min-w-0">
                  <div class="truncate text-base text-ink-gray-8">{{ user.full_name }}</div>
                  <div class="mt-0.5 truncate text-sm text-ink-gray-5">{{ user.email }}</div>
                </div>
              </ListCell>
            </ListRow>
          </ListRows>
        </List>
      </ScrollArea>

      <!-- Stacked below sm: a right-aligned button leaves a dead strip beside it
           on a phone, so the button takes the full width and the error sits
           above it. -->
      <div
        class="flex shrink-0 flex-col gap-2 border-t border-outline-gray-1 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-3"
      >
        <!-- min-h-5 holds one line of error text, so a failed submit does not
             resize the footer. -->
        <div class="min-h-5 min-w-0 sm:flex-1">
          <ErrorMessage :message="submitError" />
        </div>
        <!-- min-w-32: the label grows leftwards as the count changes, so nothing
             else in the footer moves. -->
        <Button
          variant="solid"
          class="w-full shrink-0 sm:w-auto sm:min-w-32"
          :disabled="!selected.length"
          :loading="isAdding"
          @click="submit"
        >
          {{ submitLabel }}
        </Button>
      </div>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  Button,
  Checkbox,
  Dialog,
  ErrorMessage,
  ScrollArea,
  Skeleton,
  TextInput,
  toast,
  useDoctype,
} from 'frappe-ui'
import { List, ListCell, ListRow, ListRows } from 'frappe-ui/list'
import UserAvatar from '@/components/UserAvatar.vue'
import EmptyStateBox from '@/components/EmptyStateBox.vue'
import { communities, type Community } from '@/data/communities'
import { activeUsers, usersReady, useUser } from '@/data/users'
import type { GPTeam } from '@/types/doctypes'

const props = defineProps<{
  community: Community
}>()

const show = defineModel<boolean>()

const teams = useDoctype<GPTeam>('GP Team')
const search = ref('')
const selected = ref<string[]>([])
const submitError = ref<Error | string>()

const searchTerm = computed(() => search.value.trim().toLowerCase())

const addableUsers = computed(() => {
  const existingMembers = new Set(props.community.members.map((member) => member.user))
  return activeUsers.value
    .filter((user) => user.isNotGuest && !existingMembers.has(user.name))
    .sort((a, b) => a.full_name.localeCompare(b.full_name))
})

const matches = computed(() => {
  const term = searchTerm.value
  if (!term) return addableUsers.value
  return addableUsers.value.filter(
    (user) =>
      user.full_name.toLowerCase().includes(term) ||
      (user.email || '').toLowerCase().includes(term),
  )
})

const matchNames = computed(() => new Set(matches.value.map((user) => user.name)))
const selectedSet = computed(() => new Set(selected.value))

const allMatchesSelected = computed(
  () => matches.value.length > 0 && matches.value.every((user) => selectedSet.value.has(user.name)),
)

const someMatchesSelected = computed(
  () => !allMatchesSelected.value && matches.value.some((user) => selectedSet.value.has(user.name)),
)

const selectAllLabel = computed(() => {
  if (!matches.value.length) return 'Select all'
  if (!searchTerm.value) return `Select all ${matches.value.length} people`
  return `Select ${matches.value.length} matching`
})

const submitLabel = computed(() => {
  const count = selected.value.length
  if (!count) return 'Add members'
  return count === 1 ? 'Add 1 member' : `Add ${count} members`
})

const isAdding = computed(() => teams.runDocMethod.isLoading(props.community.name, 'add_members'))

/**
 * Add or remove exactly the users the current search matches, leaving every other
 * pick alone — the same rule as frappe-ui's own `List.toggleSelectAll`.
 *
 * Driven by the checkbox's own value rather than by toggling the current state, so
 * it stays correct even though `Checkbox` emits `update:modelValue` twice per click.
 */
function setMatchesSelected(checked: boolean | 1 | 0 | undefined) {
  if (checked) {
    selected.value = [...new Set([...selected.value, ...matchNames.value])]
  } else {
    selected.value = selected.value.filter((name) => !matchNames.value.has(name))
  }
}

function successMessage(users: string[]) {
  if (users.length === 1) {
    return `${useUser(users[0]).full_name} added to ${props.community.title}`
  }
  return `${users.length} members added to ${props.community.title}`
}

async function submit() {
  const users = [...selected.value]
  if (!users.length) return

  submitError.value = undefined
  try {
    await teams.runDocMethod.submit({
      name: props.community.name,
      method: 'add_members',
      params: { users },
    })
  } catch (error) {
    // Kept in a local ref rather than read off `teams.runDocMethod.error`, which
    // outlives the dialog and would reappear on the next open.
    submitError.value = error as Error
    return
  }
  await communities.reload()
  toast.success(successMessage(users))
  show.value = false
}

function reset() {
  search.value = ''
  selected.value = []
  submitError.value = undefined
}
</script>
