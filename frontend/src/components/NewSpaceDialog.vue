<template>
  <Dialog title="New Space" v-model:open="show">
    <p class="text-p-base text-ink-gray-6">
      Spaces keep discussions, tasks, and pages in one place. Use them to group by team, project or
      any topic.
    </p>
    <div class="mt-3 space-y-2">
      <div class="space-x-2 flex items-center w-full">
        <IconPicker v-model="newSpace.doc.icon" v-slot="{ isOpen }">
          <Button>
            <template #icon>
              <span v-if="newSpace.doc.icon">{{ newSpace.doc.icon }}</span>
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
      <div class="flex gap-2">
        <div class="size-7 shrink-0"></div>
        <div class="w-full">
          <Combobox placeholder="Category" :options="categoryOptions" v-model="selectedCategory" />
        </div>
      </div>
      <div class="flex items-center space-x-2">
        <div class="w-7 h-7"></div>
        <div>
          <FormControl
            type="checkbox"
            label="Keep it private &mdash; Only visible to members"
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
        <Button variant="solid" @click="submit" :loading="newSpace.loading">Submit</Button>
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
import { useNewDoc } from 'frappe-ui'
import { GPProject, GPTeam } from '@/types/doctypes'
import { spaces } from '@/data/spaces'
import { computed, h, ref, watch } from 'vue'
import { activeTeams, teams } from '@/data/teams'
import { until } from '@vueuse/core'

const props = defineProps<{
  category?: string
}>()

const show = defineModel<boolean>()
const newSpace = useNewDoc<GPProject>('GP Project', {
  title: '',
  icon: '',
  team: '',
  is_private: 0,
})
const selectedCategory = ref<string | null>(null)

watch(show, (value: boolean) => {
  if (value) {
    if (props.category) {
      selectCategory(props.category)
    } else {
      selectedCategory.value = null
    }
  }
})

const categoryOptions = computed((): ComboboxOption[] => {
  let categories = activeTeams.value.map((team) => ({
    label: team.title,
    value: team.name,
  }))

  const createNewOption = {
    type: 'custom' as const,
    key: 'create_new',
    label: 'Create new',
    slots: {
      prefix: () => h('span', { class: 'lucide-plus' }),
      label: ({ query }) => `Create New: ${query}`,
    },
    condition: ({ query }) =>
      query.length > 0 && !activeTeams.value.map((team) => team.title).includes(query),
    onClick: async ({ query }) => {
      let currentActiveTeamsCount = activeTeams.value.length
      const team = (await teams.insert.submit({ title: query })) as unknown as GPTeam
      if (team) {
        await until(() => activeTeams.value.length > currentActiveTeamsCount).toBeTruthy()
        selectCategory(team.name)
      }
    },
  } as ComboboxOption

  return [...categories, createNewOption]
})

function selectCategory(categoryId: string) {
  let categoryOption = categoryOptions.value.find((option) =>
    option.type === 'custom' ? option.key === categoryId : option.value === categoryId,
  )
  if (categoryOption && categoryOption.type !== 'custom') {
    selectedCategory.value = categoryOption.value
  }
}

function submit() {
  if (selectedCategory.value) {
    newSpace.doc.team = selectedCategory.value
  }
  newSpace.submit().then(() => {
    // TODO: useNewDoc should automatically reload related resources
    spaces.reload()
    show.value = false
  })
}
</script>
