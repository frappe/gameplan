<template>
  <Dialog title="New Space" v-model:open="show">
    <p class="text-p-base text-ink-gray-6">
      Spaces keep discussions, tasks, and pages in one place. Use them to group by community,
      project, or any topic.
    </p>
    <div class="mt-3 space-y-2">
      <div class="space-x-2 flex items-center w-full">
        <IconPicker v-model="newSpace.doc.icon" v-slot="{ togglePopover }">
          <Button @click="togglePopover()">
            <template #icon>
              <SpaceIcon v-if="newSpace.doc.icon" :icon="newSpace.doc.icon" class="size-4" />
              <span v-else class="lucide-plus h-4 w-4" />
            </template>
          </Button>
        </IconPicker>
        <TextInput
          class="w-full"
          placeholder="Space name"
          id="new-space-name"
          v-model="newSpace.doc.title"
          autofocus
        />
      </div>
      <div v-if="!isCommunityLocked" class="flex gap-2">
        <div class="size-7 shrink-0"></div>
        <div class="w-full">
          <Combobox
            placeholder="Community"
            :options="communityOptions"
            v-model="selectedCommunity"
          />
        </div>
      </div>
      <div class="flex items-center space-x-2">
        <div class="w-7 h-7"></div>
        <div>
          <FormControl
            type="checkbox"
            label="Keep it private &mdash; Only visible to users"
            v-model="newSpace.doc.is_private"
          />
        </div>
      </div>
    </div>
    <div class="mt-4">
      <ErrorMessage :message="newSpace.error" />
    </div>

    <template #actions>
      <div class="flex items-center space-x-2 justify-end">
        <Button>Cancel</Button>
        <Button variant="solid" @click="submit" :loading="newSpace.loading" :disabled="!isOnline">
          Submit
        </Button>
      </div>
    </template>
  </Dialog>
</template>
<script setup lang="ts">
import {
  Dialog,
  ErrorMessage,
  FormControl,
  TextInput,
  Combobox,
  type ComboboxOption,
} from 'frappe-ui'
import IconPicker from './IconPicker.vue'
import SpaceIcon from './SpaceIcon.vue'
import { useNewDoc } from 'frappe-ui'
import { GPProject, GPTeam } from '@/types/doctypes'
import { spaces } from '@/data/spaces'
import { computed, h, ref, watch } from 'vue'
import { activeCommunities, communities } from '@/data/communities'
import { isGameplanAdmin } from '@/data/users'
import { until } from '@vueuse/core'
import { isOnline } from '@/data/online'

const props = defineProps<{
  // When set, the dialog always creates in this community and hides the community picker.
  lockedCommunityId?: string
}>()

const show = defineModel<boolean>()
const newSpace = useNewDoc<GPProject>('GP Project', {
  title: '',
  icon: '',
  team: '',
  is_private: 0,
})
const selectedCommunity = ref<string | null>(null)

const isCommunityLocked = computed(() => Boolean(props.lockedCommunityId))

watch(show, (value: boolean) => {
  if (value) {
    if (props.lockedCommunityId) {
      selectCommunity(props.lockedCommunityId)
    } else {
      selectedCommunity.value = null
    }
  }
})

const communityOptions = computed((): ComboboxOption[] => {
  let options = activeCommunities.value.map((community) => ({
    label: community.title,
    value: community.name,
  }))

  // Users can create spaces, but creating a new community is global-admin only.
  if (!isGameplanAdmin()) return options

  const createNewOption = {
    type: 'custom' as const,
    key: 'create_new',
    label: 'Create new',
    disabled: !isOnline.value,
    slots: {
      prefix: () => h('span', { class: 'lucide-plus' }),
      label: ({ query }) => `Create New: ${query}`,
    },
    condition: ({ query }) =>
      query.length > 0 &&
      !activeCommunities.value.map((community) => community.title).includes(query),
    onClick: async ({ query }) => {
      let currentActiveCommunitiesCount = activeCommunities.value.length
      const community = (await communities.insert.submit({ title: query })) as unknown as GPTeam
      if (community) {
        await until(
          () => activeCommunities.value.length > currentActiveCommunitiesCount,
        ).toBeTruthy()
        selectCommunity(community.name)
      }
    },
  } as ComboboxOption

  return [...options, createNewOption]
})

function selectCommunity(communityId: string) {
  let option = communityOptions.value.find((option) =>
    option.type === 'custom' ? option.key === communityId : option.value === communityId,
  )
  if (option && option.type !== 'custom') {
    selectedCommunity.value = option.value
  }
}

function submit() {
  if (!isOnline.value) return
  const community = props.lockedCommunityId || selectedCommunity.value
  if (community) {
    newSpace.doc.team = community
  }
  newSpace.submit().then(() => {
    // TODO: useNewDoc should automatically reload related resources
    spaces.reload()
    show.value = false
  })
}
</script>
