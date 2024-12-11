<template>
  <PageHeader>
    <Breadcrumbs class="h-7" :items="[{ label: 'Spaces', route: { name: 'Spaces' } }]" />
    <Button variant="solid" @click="newSpaceDialog = true">
      <template #prefix><LucidePlus class="h-4 w-4" /></template>
      Add new
    </Button>
  </PageHeader>
  <NewSpaceDialog v-model="newSpaceDialog" />
  <div class="mx-auto max-w-3xl sm:px-5 pb-80">
    <div class="mt-5 flex px-2.5">
      <TabButtons :buttons="[{ label: 'Active' }, { label: 'Archived' }]" v-model="currentTab" />
    </div>
    <div v-for="group in groupedSpaces" :key="group.name">
      <div class="p-3 pt-8 text-ink-gray-9 text-base">{{ group.title || group.name }}</div>
      <div class="border-b mx-3"></div>
      <router-link
        v-for="(d, index) in group.spaces"
        :key="d.name"
        :to="{
          name: 'Space',
          params: {
            spaceId: d.name,
          },
        }"
        class="group relative block rounded-[10px] transition hover:bg-surface-gray-2"
      >
        <div class="flex h-full items-center space-x-4 overflow-hidden px-3 py-2">
          <span class="font-[emoji] text-2xl self-start mt-0.5">
            {{ d.icon }}
          </span>
          <div class="min-w-0 flex-1">
            <div class="flex min-w-0 items-center">
              <div class="overflow-hidden text-ellipsis whitespace-nowrap text-ink-gray-9">
                <span class="overflow-hidden text-ellipsis whitespace-nowrap text-base font-medium">
                  {{ d.title }}
                  <LucideLock
                    v-if="d.is_private"
                    class="h-3 w-3 text-ink-gray-6 inline ml-1 mb-0.5"
                  />
                </span>
              </div>
            </div>
            <div class="mt-1 flex min-w-0 items-center justify-between">
              <div
                class="overflow-hidden text-ellipsis whitespace-nowrap text-base text-ink-gray-5"
              >
                <span>
                  {{ d.members.length }} {{ d.members.length == 1 ? 'member' : 'members' }}
                </span>
              </div>
            </div>
          </div>
          <div class="ml-auto">
            <div class="flex items-center space-x-1" v-if="!d.archived_at" @click.prevent>
              <Button
                class="w-16"
                v-if="hasJoined(d)"
                @click="leaveSpace(d)"
                :loading="isMethodLoading(d.name, 'leave')"
              >
                Leave
              </Button>
              <Button
                class="w-16"
                v-else
                @click="joinSpace(d)"
                :loading="isMethodLoading(d.name, 'join')"
              >
                Join
              </Button>
              <SpaceOptions placement="right" :spaceId="d.name" />
            </div>
            <div v-else @click.prevent>
              <Button @click="unarchiveSpace(d)">Unarchive</Button>
            </div>
          </div>
        </div>
        <!-- <div
          class="mx-3 h-px border-t border-outline-gray-modals"
          v-if="index < projects.data.length - 1"
        ></div> -->
      </router-link>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { Breadcrumbs, TabButtons } from 'frappe-ui'
import { useGroupedSpaces } from '@/data/groupedSpaces'
import { projects as spaces } from '@/data/projects'
import { useSessionUser } from '@/data/users'
import NewSpaceDialog from '@/components/NewSpaceDialog.vue'
import SpaceOptions from '@/components/SpaceOptions.vue'
import PageHeader from '@/components/PageHeader.vue'
import { GPProject } from '@/types/GPProject'
import LucideLock from '~icons/lucide/lock'

const sessionUser = useSessionUser()
const currentTab = ref('Active')

const groupedSpaces = useGroupedSpaces({
  filterFn: (space) => (currentTab.value == 'Active' ? !space.archived_at : space.archived_at),
})

const newSpaceDialog = ref(false)

function joinSpace(space) {
  spaces.runDocMethod.submit({
    method: 'join',
    name: space.name,
  })
}

function leaveSpace(space) {
  spaces.runDocMethod.submit({
    method: 'leave',
    name: space.name,
  })
}

function unarchiveSpace(space) {
  spaces.runDocMethod.submit({
    method: 'unarchive',
    name: space.name,
  })
}

function isMethodLoading(docname, method) {
  return (
    spaces.runDocMethod.loading &&
    spaces.runDocMethod.params.method === method &&
    spaces.runDocMethod.params.dn === docname
  )
}

function hasJoined(space: GPProject) {
  return space.members.find((member) => member.user === sessionUser.name)
}
</script>
