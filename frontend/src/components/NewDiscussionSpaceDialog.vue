<template>
  <Dialog title="New discussion" v-model:open="show" @close="reset">
    <template v-if="hasSpaceToPostIn">
      <p class="text-p-base text-ink-gray-6">
        Pick the space this discussion belongs to. You can change it later while writing.
      </p>
      <Combobox
        class="mt-3 w-full"
        :options="spaceOptions"
        v-model="selectedSpace"
        placeholder="Select a space"
        open-on-click
        autofocus
      >
        <template #item-prefix="{ item }">
          <SpaceIcon :icon="optionIcon(item)" class="size-4 text-ink-gray-6" />
        </template>
        <template #item-label="{ item }">
          <span class="truncate">{{ item.spaceTitle ?? item.label }}</span>
        </template>
      </Combobox>
    </template>
    <EmptyStateBox v-else>
      <span class="lucide-layers h-7 w-7 text-ink-gray-4" />
      <span class="mt-2">No space to post in</span>
      <span class="mt-1 text-p-sm text-ink-gray-5">{{ emptyStateHint }}</span>
    </EmptyStateBox>
    <template #actions>
      <Button
        v-if="hasSpaceToPostIn"
        class="w-full"
        variant="solid"
        :disabled="!selectedSpace"
        @click="startDiscussion"
      >
        Continue
      </Button>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Button, Combobox, Dialog } from 'frappe-ui'
import EmptyStateBox from './EmptyStateBox.vue'
import SpaceIcon from './SpaceIcon.vue'
import { useGroupedSpaceOptions } from '@/data/groupedSpaces'
import { canPostInSpace, getSpace, spaces } from '@/data/spaces'
import { useSessionUser } from '@/data/users'
import { isGuest } from '@/utils/permissions'

const show = defineModel<boolean>()
const router = useRouter()
const sessionUser = useSessionUser()
const selectedSpace = ref<string | null>(null)

// Grouped by community, so one searchable list answers both "which community" and
// "which space" in a single step. Same source as the composer's own space picker, so a
// space offered here is always a space the composer will accept.
const groupedSpaceOptions = useGroupedSpaceOptions({ filterFn: canPostInSpace })

// The combobox shows nothing but an option's `label` once the list closes, and a space
// title on its own does not say where the discussion is going. So the label carries
// "Community / Space", matching how notifications name a location, and the rows keep
// the plain space title in `spaceTitle` because the group header already names the
// community. A space with no community drops the separator with it.
const spaceOptions = computed(() => {
  return groupedSpaceOptions.value.map((entry) => {
    if (!('options' in entry)) return entry
    return {
      ...entry,
      options: entry.options.map((option) => ({
        ...option,
        label: [option.community, option.label].filter(Boolean).join(' / '),
        spaceTitle: option.label,
      })),
    }
  })
})

const hasSpaceToPostIn = computed(() => (spaces.data ?? []).some(canPostInSpace))

// A guest can never start a discussion, in any space, so telling them to join one is
// advice they cannot act on. Say what is actually true for them instead.
const emptyStateHint = computed(() =>
  isGuest(sessionUser)
    ? 'Guests can reply to discussions, but not start them.'
    : 'Join a space, or ask an admin to add you to one.',
)

function optionIcon(item: unknown) {
  if (!item || typeof item !== 'object' || !('icon' in item)) return null
  return (item as { icon?: string | null }).icon || null
}

function reset() {
  selectedSpace.value = null
}

function startDiscussion() {
  const spaceId = selectedSpace.value
  if (!spaceId) return
  const communityId = getSpace(spaceId)?.team
  show.value = false
  reset()

  // An uncategorized space has no community to scope the composer route with, so it
  // falls back to the legacy route the same way the rest of the app does.
  if (!communityId) {
    router.push({ name: 'LegacyNewDiscussion', query: { spaceId } })
    return
  }
  router.push({ name: 'NewDiscussion', params: { communityId }, query: { spaceId } })
}
</script>
