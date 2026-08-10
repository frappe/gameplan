<template>
  <ListRow class="h-10">
    <ListCell>
      <IconPicker :modelValue="space.icon || ''" @update:modelValue="updateIcon">
        <template #default="{ togglePopover }">
          <Button
            variant="ghost"
            size="xs"
            class="shrink-0"
            tooltip="Edit icon"
            :disabled="!canEditSpace"
            @click="togglePopover()"
          >
            <template #icon>
              <SpaceIcon :icon="space.icon" class="size-4 text-ink-gray-6" />
            </template>
          </Button>
        </template>
      </IconPicker>

      <div class="min-w-0 flex-1">
        <div class="flex min-w-0 items-center gap-1.5">
          <input
            v-model="title"
            aria-label="Space title"
            class="h-7 min-w-0 flex-1 rounded-4 border border-transparent bg-transparent py-0 pl-1 pr-2 text-base text-ink-gray-8 outline-none ring-0 transition-colors hover:border-outline-gray-2 focus:border-outline-gray-3 focus:ring-0 disabled:cursor-not-allowed disabled:text-ink-gray-6 disabled:hover:border-transparent"
            :disabled="!canEditSpace"
            @blur="saveTitle"
            @keydown.enter.prevent="saveTitle"
          />
          <span v-if="space.is_private" class="lucide-lock size-3.5 shrink-0 text-ink-gray-5" />
        </div>
        <div class="mt-1 flex flex-wrap gap-x-2 gap-y-1 text-sm text-ink-gray-5 md:hidden">
          <span class="inline-flex items-center gap-1">
            <span :class="[visibilityIcon(space.is_private), 'size-3.5']" />
            {{ visibilityLabel(space.is_private) }}
          </span>
          <span>{{ contentLabel }}</span>
          <span v-if="guestsLabel">{{ guestsLabel }}</span>
        </div>
      </div>
    </ListCell>

    <ListCell class="max-md:hidden">
      <div class="w-full truncate text-sm text-ink-gray-5">{{ contentLabel }}</div>
    </ListCell>

    <ListCell v-if="showGuests" class="max-md:hidden">
      <div class="w-full truncate text-sm text-ink-gray-5">{{ guestsLabel }}</div>
    </ListCell>

    <ListCell class="justify-end gap-1">
      <Button
        v-if="space.archived_at"
        variant="ghost"
        icon="lucide-archive-restore"
        tooltip="Unarchive space"
        :loading="isDocMethodLoading(space.name, 'unarchive')"
        @click="restoreSpace"
      />
      <SpaceOptions v-else align="end" :spaceId="space.name" />
    </ListCell>
  </ListRow>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Button, useDoctype } from 'frappe-ui'
import { ListCell, ListRow } from 'frappe-ui/list'
import IconPicker from '@/components/IconPicker.vue'
import SpaceIcon from '@/components/SpaceIcon.vue'
import SpaceOptions from '@/components/SpaceOptions.vue'
import { isDocMethodLoading, spaces, type Space, unarchiveSpace } from '@/data/spaces'
import { readOnlyMode } from '@/data/readOnlyMode'
import type { GPProject } from '@/types/doctypes'
import { visibilityIcon, visibilityLabel } from '@/utils/visibility'

const props = defineProps<{
  space: Space
  pagesCount: number
  guestsCount: number
  showGuests: boolean
}>()

const project = useDoctype<GPProject>('GP Project')
const title = ref(props.space.title)
const savingTitle = ref(false)
const canEditSpace = computed(() => !readOnlyMode && !props.space.archived_at)
const contentLabel = computed(() => {
  const counts = [
    formatNonZeroCount(props.space.discussions_count ?? 0, 'post'),
    formatNonZeroCount(props.pagesCount, 'page'),
    formatNonZeroCount(props.space.tasks_count ?? 0, 'task'),
  ].filter((count): count is string => Boolean(count))

  return counts.length ? counts.join(' / ') : 'No content'
})
const guestsLabel = computed(() =>
  props.guestsCount > 0 ? formatCount(props.guestsCount, 'guest') : '',
)

watch(
  () => props.space.title,
  (value) => {
    title.value = value
  },
)

async function updateIcon(icon: string) {
  if (!canEditSpace.value || icon === props.space.icon) return
  await project.setValue.submit({
    name: props.space.name,
    icon,
  })
  await spaces.reload()
}

async function saveTitle() {
  const nextTitle = title.value.trim()
  if (savingTitle.value || !canEditSpace.value || !nextTitle || nextTitle === props.space.title) {
    title.value = props.space.title
    return
  }

  savingTitle.value = true
  try {
    await project.setValue.submit({
      name: props.space.name,
      title: nextTitle,
    })
    await spaces.reload()
  } finally {
    savingTitle.value = false
  }
}

async function restoreSpace() {
  await unarchiveSpace(props.space)
  await spaces.reload()
}

function formatCount(count: number, label: string) {
  return `${count} ${count === 1 ? label : `${label}s`}`
}

function formatNonZeroCount(count: number, label: string) {
  return count > 0 ? formatCount(count, label) : null
}
</script>
