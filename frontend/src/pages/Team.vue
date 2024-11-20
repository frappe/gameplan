<template>
  <div class="pb-20">
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
            v-if="!team.doc.members.map((m) => m.user).includes($user().name)"
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
    <CoverImage
      v-if="showCoverImage"
      :imageUrl="team.doc.cover_image"
      :imagePosition="team.doc.cover_image_position"
      :editable="true"
      @change="
        ({ imageUrl, imagePosition }) => {
          team.setValue.submit({
            cover_image: imageUrl,
            cover_image_position: imagePosition,
          })
        }
      "
    />
    <div class="mx-auto max-w-4xl px-5 pt-6">
      <div class="flex items-center justify-between px-3">
        <TabButtons :buttons="tabOptions" v-model="currentTab" />
        <Dropdown
          placement="right"
          :button="{ icon: LucideSettings2 }"
          :options="[
            { group: 'Order by', items: [{ label: 'Recent activity' }, { label: 'Created' }] },
          ]"
        />
      </div>

      <router-view :team="team" />
    </div>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { Breadcrumbs, Dropdown, TabButtons } from 'frappe-ui'
import IconPicker from '@/components/IconPicker.vue'
import LucideLogOut from '~icons/lucide/log-out.vue'
import LucideImage from '~icons/lucide/image.vue'
import LucideTrash2 from '~icons/lucide/trash-2.vue'
import LucideSettings2 from '~icons/lucide/settings-2.vue'

const currentTab = ref('discussions')
const tabOptions = [
  { label: 'Discussions', value: 'discussions' },
  { label: 'Pages', value: 'pages' },
  { label: 'Chat', value: 'chat' },
]

const props = defineProps(['team'])
let showCoverImage = ref(Boolean(props.team.doc.cover_image))

let dropdownOptions = [
  {
    label: 'Leave this space',
    icon: LucideLogOut,
    condition: () => props.team.doc.members.map((m) => m.user).includes($user().name),
    onClick: () => (showCoverImage.value = true),
  },
  {
    label: 'Set cover image',
    icon: LucideImage,
    condition: () => !props.team.doc.cover_image,
    onClick: () => (showCoverImage.value = true),
  },
  {
    label: 'Archive',
    icon: LucideTrash2,
    onClick: () => archiveTeam(),
  },
]

function updateTeamIcon(icon) {
  this.team.setValue.submit({ icon })
}

function archiveTeam() {
  this.$dialog({
    title: 'Archive Team',
    message: 'Are you sure you want to archive the team?',
    actions: [
      {
        label: 'Archive',
        variant: 'solid',
        onClick: (close) => {
          return this.team.archive.submit(null, {
            onSuccess: () => {
              this.$router.replace({ name: 'Home' })
              close()
            },
          })
        },
      },
    ],
  })
}
</script>
