<template>
  <Dialog
    title="Merge with another space"
    @after-leave="
      () => {
        selectedSpace = null
      }
    "
    v-model:open="show"
  >
    <p class="text-p-base text-ink-gray-7 mb-4">
      This will move all discussions, tasks, and pages from the
      <span class="whitespace-nowrap font-semibold">{{ space?.title }}</span> space to the selected
      space. This change is irreversible!
    </p>
    <Combobox
      :options="groupedSpaceOptions"
      v-model="selectedSpace"
      placeholder="Select a space"
      class="w-full"
      open-on-click
      autofocus
    />
    <ErrorMessage class="mt-2" :message="spaces.runDocMethod.error" />
    <template #actions>
      <Button
        class="w-full"
        variant="solid"
        :loading="spaces.runDocMethod.isLoading(spaceId, 'merge_with_project')"
        @click="submit"
      >
        {{ selectedSpace ? `Merge with ${useSpace(selectedSpace).value?.title}` : 'Merge' }}
      </Button>
    </template>
  </Dialog>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Combobox } from 'frappe-ui'
import { useGroupedSpaceOptions } from '@/data/groupedSpaces'
import { useDoctype } from 'frappe-ui'
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

const groupedSpaceOptions = useGroupedSpaceOptions({
  filterFn: (s) => s.name.toString() !== props.spaceId.toString(),
})

function submit() {
  spaces.runDocMethod
    .submit({
      method: 'merge_with_project',
      name: props.spaceId,
      params: {
        project: selectedSpace.value,
      },
      validate() {
        if (!selectedSpace.value) {
          return 'Please select a project to merge'
        }
      },
    })
    .then(() => {
      if (selectedSpace.value) {
        show.value = false
        return router.replace({
          name: 'Space',
          params: { spaceId: selectedSpace.value },
        })
      }
    })
}
</script>
