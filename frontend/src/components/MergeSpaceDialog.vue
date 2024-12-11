<template>
  <Dialog
    :options="{
      title: 'Merge with another space',
    }"
    @after-leave="
      () => {
        selectedSpace = null
        projects.runDocMethod.reset()
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
      <ErrorMessage
        class="mt-2"
        :message="
          projects.runDocMethod.params?.method === 'merge_with_project' &&
          projects.runDocMethod.error
        "
      />
    </template>
    <template #actions>
      <Button
        class="w-full"
        variant="solid"
        :loading="
          projects.runDocMethod.params?.method === 'merge_with_project' &&
          projects.runDocMethod.loading
        "
        @click="submit"
      >
        {{ selectedSpace ? `Merge with ${selectedSpace.label}` : 'Merge' }}
      </Button>
    </template>
  </Dialog>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Autocomplete } from 'frappe-ui'
import { useGroupedSpaces } from '@/data/groupedSpaces'
import { projects, getProject } from '@/data/projects'

const props = defineProps<{
  spaceId: string | number
}>()

const router = useRouter()
const space = computed(() => getProject(props.spaceId))

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
  projects.runDocMethod.submit(
    {
      method: 'merge_with_project',
      name: props.spaceId,
      project: selectedSpace.value?.value,
    },
    {
      validate() {
        if (!selectedSpace.value?.value) {
          return 'Please select a project to merge'
        }
      },
      onSuccess() {
        if (selectedSpace.value) {
          show.value = false
          return router.replace({
            name: 'Space',
            params: { spaceId: selectedSpace.value.value },
          })
        }
      },
    },
  )
}
</script>
