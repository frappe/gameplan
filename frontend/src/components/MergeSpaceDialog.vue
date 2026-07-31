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
    <p v-if="hasMergeTargets" class="text-p-base text-ink-gray-7 mb-4">
      This will move all discussions, tasks, and pages from the
      <span class="whitespace-nowrap font-semibold">{{ space?.title }}</span> space to the selected
      space. This change is irreversible!
    </p>
    <Combobox
      v-if="hasMergeTargets"
      :options="groupedSpaceOptions"
      v-model="selectedSpace"
      placeholder="Select a space"
      class="w-full"
      open-on-click
      autofocus
    />
    <p v-else class="text-p-base text-ink-gray-6">{{ noTargetsMessage }}</p>
    <ErrorMessage class="mt-2" :message="spaces.runDocMethod.error" />
    <template #actions>
      <Button
        class="w-full"
        variant="solid"
        :disabled="!hasMergeTargets"
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
import { getSpace, useSpace } from '@/data/spaces'
import { useSessionUser } from '@/data/users'
import { canManageSpace, isGuest } from '@/utils/permissions'

const props = defineProps<{
  spaceId: string
}>()

const router = useRouter()
const spaces = useDoctype<GPProject>('GP Project')
const space = useSpace(() => props.spaceId)
const sessionUser = useSessionUser()

const selectedSpace = ref(null)
const show = defineModel<boolean>()

/**
 * A merge empties this Space into the target, so the backend
 * (`GP Project.require_can_manage_merge`) demands manage rights on BOTH and refuses guests
 * outright. Mirroring that here keeps the picker from offering targets whose merge would
 * come back as "Only space managers can merge spaces" — an error the user had no way to
 * anticipate. `canManageSpace` reads the already-fetched space/community membership, so
 * this costs no extra request.
 */
const isGuestUser = computed(() => isGuest(sessionUser))
const canMergeThisSpace = computed(
  () => !isGuestUser.value && canManageSpace(space.value, sessionUser),
)

const groupedSpaceOptions = useGroupedSpaceOptions({
  filterFn: (s) =>
    canMergeThisSpace.value &&
    s.name.toString() !== props.spaceId.toString() &&
    s.team === space.value?.team &&
    canManageSpace(s, sessionUser),
})

const hasMergeTargets = computed(() => groupedSpaceOptions.value.length > 0)

const noTargetsMessage = computed(() => {
  if (isGuestUser.value) return 'Guests cannot merge spaces.'
  if (!canMergeThisSpace.value) {
    return 'Only space managers can merge spaces, and you do not manage this one.'
  }
  return 'There are no other spaces in this community that you manage, so there is nothing to merge into.'
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
          params: {
            communityId: getSpace(selectedSpace.value)?.team,
            spaceId: selectedSpace.value,
          },
        })
      }
    })
}
</script>
