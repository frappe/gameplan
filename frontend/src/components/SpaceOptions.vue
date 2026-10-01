<template>
  <!-- No permitted action, no trigger: a member browsing a community's spaces in
       settings would otherwise open an empty menu. -->
  <DropdownMoreOptions
    v-if="permittedOptions.length"
    :label="`${space?.title} Space Options`"
    v-bind="$attrs"
    button-size="xs"
    :options="permittedOptions"
  />

  <MergeSpaceDialog
    v-model="showSpaceMergeDialog"
    :spaceId="props.spaceId"
    @merged="emit('merged', $event)"
  />
  <ChangeSpaceCategoryDialog v-model="showSpaceCategoryDialog" :spaceId="props.spaceId" />
  <SpaceAccessDialog v-model="showSpaceAccessDialog" :spaceId="props.spaceId" />
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { useDoctype, dialog } from 'frappe-ui'
import DropdownMoreOptions from './DropdownMoreOptions.vue'
import MergeSpaceDialog from './MergeSpaceDialog.vue'
import ChangeSpaceCategoryDialog from './ChangeSpaceCategoryDialog.vue'
import SpaceAccessDialog from './SpaceAccessDialog.vue'
import { useSpacePermissions, archiveSpace } from '@/data/spaces'
import { GPProject } from '@/types/doctypes'
import { useCommandPaletteCommands } from './CommandPalette/registry'

defineOptions({
  inheritAttrs: false,
})

const props = defineProps<{
  spaceId: string
}>()
const emit = defineEmits<{
  (event: 'merged', spaceId: string): void
}>()

const { space, canEditSettings, canManageAccess } = useSpacePermissions(() => props.spaceId)
const spaces = useDoctype<GPProject>('GP Project')

const showSpaceMergeDialog = ref(false)
const showSpaceCategoryDialog = ref(false)
const showSpaceAccessDialog = ref(false)

const options = computed(() => [
  {
    label: 'Manage access',
    icon: 'lucide-users',
    onClick: () => (showSpaceAccessDialog.value = true),
    condition: () => canManageAccess.value,
  },
  {
    label: 'Change Community',
    icon: 'lucide-log-out',
    onClick: () => (showSpaceCategoryDialog.value = true),
    condition: () => canEditSettings.value,
  },
  {
    label: 'Merge',
    icon: 'lucide-merge',
    onClick: () => (showSpaceMergeDialog.value = true),
    condition: () => canEditSettings.value,
  },
  {
    label: 'Archive',
    icon: 'lucide-archive',
    onClick: () => space.value && archiveSpace(space.value),
    condition: () => canEditSettings.value,
  },
  {
    label: 'Delete',
    icon: 'lucide-trash-2',
    onClick: () => {
      let message = `This will permanently delete the space and all its content. This action cannot be undone.`
      if (space.value?.discussions_count && space.value?.tasks_count) {
        message = `This will permanently delete the space and all its content. This space has ${space.value?.discussions_count} discussions and ${space.value?.tasks_count} tasks. This action cannot be undone.`
      } else if (space.value?.discussions_count) {
        message = `This will permanently delete the space and all its content. This space has ${space.value?.discussions_count} discussions. This action cannot be undone.`
      }
      dialog.danger({
        title: 'Delete space',
        message,
        onConfirm: () => spaces.delete.submit({ name: props.spaceId }),
      })
    },
    condition: () => canEditSettings.value,
  },
])

const permittedOptions = computed(() =>
  options.value.filter((option) => !option.condition || option.condition()),
)

useCommandPaletteCommands(
  computed(() =>
    options.value.map((option) => ({
      title: `${option.label} space`,
      name: `space-${option.label.toLowerCase().replace(/\W+/g, '-')}`,
      group: 'Space',
      icon: option.icon,
      aliases: spaceActionAliases(option.label),
      onClick: option.onClick,
      condition: option.condition,
      defaultScore: option.label === 'Delete' ? 1 : 2,
    })),
  ),
)

function spaceActionAliases(label: string) {
  const aliases: Record<string, string[]> = {
    'Manage access': ['space access', 'guests', 'members'],
    'Change Community': ['move space', 'change category'],
    Merge: ['merge space'],
    Archive: ['archive space', 'read only'],
    Delete: ['delete space', 'remove space'],
  }

  return aliases[label] || []
}
</script>
