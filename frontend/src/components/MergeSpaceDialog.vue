<template>
  <Dialog
    :options="{
      title: 'Merge with another space',
    }"
    @after-leave="
      () => {
        selectedSpace = null
      }
    "
    v-model="show"
  >
    <template #body-content>
      <p class="text-p-base text-ink-gray-8 mb-4">
        This will move all discussions, tasks, and pages from the
        <span class="whitespace-nowrap font-semibold">{{ space?.title }}</span> space to the
        selected space. This change is irreversible!
      </p>
      <Autocomplete
        :options="groupedSpaceOptions"
        v-model="selectedSpace"
        placeholder="Select a space"
      >
        <template #item-prefix="{ option }">
          <span class="mr-2">{{ option.icon }}</span>
        </template>
      </Autocomplete>
      <ErrorMessage class="mt-2" :message="spaces.runDocMethod.error" />
    </template>
    <template #actions>
      <Button
        class="w-full"
        variant="solid"
        :loading="spaces.runDocMethod.isLoading(spaceId, 'merge_with_project')"
        @click="submit"
      >
        {{ selectedSpace ? `Merge with ${selectedSpace?.label}` : 'Merge' }}
      </Button>
    </template>
  </Dialog>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Autocomplete } from 'frappe-ui'
import { useGroupedSpaces } from '@/data/groupedSpaces'
import { useDoctype } from 'frappe-ui/src/data-fetching'
import { GPProject } from '@/types/doctypes'
import { useSpace } from '@/data/spaces'

const props = defineProps<{
  spaceId: string
}>()

const router = useRouter()
const spaces = useDoctype<GPProject>('GP Project')
const space = useSpace(() => props.spaceId)

const selectedSpace = ref(null)
const show = defineModel<boolean>()

const groupedSpaces = useGroupedSpaces({
  filterFn: (s) => s.name.toString() !== props.spaceId.toString(),
})

const groupedSpaceOptions = computed(() => {
  return groupedSpaces.value.map((group) => ({
    group: group.title,
    items: group.spaces.map((s) => ({
      label: s.title,
      value: s.name,
      icon: s.icon,
    })),
  }))
})

function submit() {
  spaces.runDocMethod
    .submit({
      method: 'merge_with_project',
      name: props.spaceId,
      params: {
        project: selectedSpace.value?.value,
      },
      validate() {
        if (!selectedSpace.value?.value) {
          return 'Please select a project to merge'
        }
      },
    })
    .then(() => {
      if (selectedSpace.value) {
        show.value = false
        return router.replace({
          name: 'Space',
          params: { spaceId: selectedSpace.value.value },
        })
      }
    })
}
</script>
