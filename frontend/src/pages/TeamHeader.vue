<template>
  <header class="sticky top-0 z-10 border-b bg-white px-5 py-2.5">
    <div class="flex items-center justify-between">
      <Breadcrumbs
        class="h-7"
        :items="[
          {
            label: team.doc.title,
            route: { name: 'Team', params: { teamId: team.doc.name } },
          },
        ]"
      >
        <template #prefix>
          <IconPicker
            v-model="team.doc.icon"
            @update:modelValue="team.setValueDebounced.submit({ icon: team.doc.icon })"
            v-slot="{ isOpen }"
          >
            <button
              class="mr-2 flex rounded-sm text-2xl leading-none"
              :class="isOpen ? 'bg-gray-200' : 'hover:bg-gray-100'"
            >
              {{ team.doc.icon }}
            </button>
          </IconPicker>
        </template>
      </Breadcrumbs>

      <div class="flex items-center space-x-2">
        <TeamMembers :team="team" />
        <Button
          v-if="!team.doc.members.map((m) => m.user).includes(sessionUser.name)"
          variant="solid"
          :loading="team.join.loading"
          @click="
            () => {
              team.join.submit()
            }
          "
        >
          Join this space
        </Button>
        <Dropdown
          v-if="!team.doc.archived_at"
          placement="left"
          :options="dropdownOptions"
          :button="{
            label: 'Options',
            variant: 'ghost',
            icon: 'more-horizontal',
          }"
        />
      </div>
    </div>
  </header>
</template>
<script setup lang="ts">
import { Breadcrumbs, Dropdown } from 'frappe-ui'
import { useTeam } from '@/data/teams'
import { useSessionUser } from '@/data/users'
import LucideLogOut from '~icons/lucide/log-out.vue'
import LucideImage from '~icons/lucide/image.vue'
import LucideTrash2 from '~icons/lucide/trash-2.vue'
import LucideMoreHorizontal from '~icons/lucide/more-horizontal.vue'
import LucideSettings2 from '~icons/lucide/settings-2.vue'
import { createDialog } from '@/utils/dialogs'
import router from '@/router'
import { ref } from 'vue'

const props = defineProps<{
  teamId: string
}>()

let sessionUser = useSessionUser()
let team = useTeam(props.teamId)

let dropdownOptions = [
  {
    label: 'Leave this space',
    icon: LucideLogOut,
    condition: () => team.doc.members.map((m) => m.user).includes(sessionUser.value.name),
    onClick: () => {},
  },
  {
    label: 'Archive',
    icon: LucideTrash2,
    onClick: () => archiveTeam(),
  },
]

function archiveTeam() {
  createDialog({
    title: 'Archive Team',
    message: 'Are you sure you want to archive the team?',
    actions: [
      {
        label: 'Archive',
        variant: 'solid',
        onClick: (close) => {
          return team.archive.submit(null, {
            onSuccess: () => {
              router.replace({ name: 'Home' })
              close()
            },
          })
        },
      },
    ],
  })
}
</script>
