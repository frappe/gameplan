<template>
  <Dialog title="Space access" v-model:open="show">
    <template v-if="space">
      <div class="mt-2 space-y-6">
        <section>
          <div class="flex items-center justify-between gap-3">
            <div>
              <h3 class="text-base-medium text-ink-gray-7">Access</h3>
              <p class="mt-1 text-p-sm text-ink-gray-5">{{ accessDescription }}</p>
            </div>
            <Badge>
              <template #prefix>
                <span :class="[accessIcon, 'size-3']" />
              </template>
              {{ accessLabel }}
            </Badge>
          </div>
        </section>

        <section v-if="space.is_private" class="space-y-3">
          <div>
            <h3 class="text-base-medium text-ink-gray-7">Users</h3>
            <p class="mt-1 text-p-sm text-ink-gray-5">
              Add community users who should be able to open this private space.
            </p>
          </div>

          <div v-if="canManageMembers" class="flex items-end gap-2">
            <Combobox
              :options="addableUsers"
              v-model="selectedUser"
              placeholder="Jane Doe"
              class="w-full"
              open-on-click
              autofocus
            >
              <template #item-prefix="{ item }">
                <UserAvatar :user="item.value" size="xs" />
              </template>
            </Combobox>
            <Button
              class="ml-auto w-13 shrink-0"
              @click="addMember"
              :loading="spaces.runDocMethod.isLoading(space.name, 'add_member')"
            >
              Add
            </Button>
          </div>

          <div class="space-y-2">
            <div class="flex items-center gap-3" v-for="member in space.members" :key="member.user">
              <UserAvatar :user="member.user" />
              <div class="min-w-0 text-p-base">
                <div class="truncate text-ink-gray-8">
                  {{ useUser(member.user).full_name }}
                </div>
                <div class="truncate text-sm text-ink-gray-5">
                  {{ useUser(member.user).email }}
                </div>
              </div>
            </div>
            <EmptyStateBox v-if="!space.members.length" class="py-6">
              <span class="lucide-users size-5 text-ink-gray-4" />
              <div class="mt-2 text-p-sm text-ink-gray-5">
                No users have been added to this private space.
              </div>
            </EmptyStateBox>
          </div>
        </section>

        <section class="space-y-3">
          <div>
            <h3 class="text-base-medium text-ink-gray-7">Guests</h3>
            <p class="mt-1 text-p-sm text-ink-gray-5">
              Guests can only access this space, not every space in the community.
            </p>
          </div>

          <div v-if="canInvite" class="flex items-end gap-2">
            <TextInput
              class="w-full"
              v-model="guestEmail"
              placeholder="jane@example.com"
              @keydown.enter="invite"
            />
            <Button
              class="ml-auto w-13 shrink-0"
              @click="invite"
              :loading="spaces.runDocMethod.isLoading(space.name, 'invite_guest')"
            >
              Invite
            </Button>
          </div>

          <div class="space-y-2">
            <div class="flex items-center gap-3" v-for="user in guestsAndInvites" :key="user.name">
              <UserAvatar :user="user.pending ? user.email : user.user" />
              <div class="min-w-0 text-base">
                <div class="truncate text-ink-gray-8">
                  {{ user.pending ? user.email : useUser(user.user).full_name }}
                </div>
                <div class="truncate text-sm text-ink-gray-5">
                  {{ user.pending ? 'Pending invitation' : useUser(user.user).email }}
                </div>
              </div>
              <div v-if="canInvite" class="ml-auto flex">
                <Tooltip :text="user.pending ? 'Delete invite' : 'Remove guest'">
                  <Button
                    :label="user.pending ? 'Delete invite' : 'Remove guest'"
                    icon="lucide-x"
                    @click="remove(user)"
                  />
                </Tooltip>
              </div>
            </div>
            <div v-if="!guestsAndInvites.length" class="text-p-sm text-ink-gray-5">
              No guests have access to this space.
            </div>
          </div>
        </section>
        <ErrorMessage class="mt-2" :message="spaces.runDocMethod.error" />
        <Dialog v-bind="removeDialog.options || {}" v-model:open="removeDialog.open" />
      </div>
    </template>
  </Dialog>
</template>
<script setup lang="ts">
import { ref, computed, reactive, watch } from 'vue'
import { Badge, Combobox, toast, Tooltip, TextInput, useDoctype, useList } from 'frappe-ui'
import EmptyStateBox from '@/components/EmptyStateBox.vue'
import { getCommunity } from '@/data/communities'
import { useSpace } from '@/data/spaces'
import { useSessionUser, useUser, users } from '@/data/users'
import { canInviteGuests, canManageSpace } from '@/utils/permissions'
import { GPGuestAccess, GPInvitation, GPProject } from '@/types/doctypes'

const props = defineProps<{ spaceId: string }>()
const show = defineModel<boolean>()
const space = useSpace(() => props.spaceId)
const spaces = useDoctype<GPProject>('GP Project')
const sessionUser = useSessionUser()
const canManageMembers = computed(() => canManageSpace(space.value, sessionUser))
const canInvite = computed(() => canInviteGuests(space.value, sessionUser))

type GuestAccess = GPGuestAccess & { pending: false }
let guests = useList<GuestAccess>({
  doctype: 'GP Guest Access',
  filters: () => ({ project: props.spaceId }),
  fields: ['user', 'project', 'name'],
  transform(data) {
    return data.map((d) => ({ ...d, pending: false }))
  },
  immediate: false,
})

type PendingInvitation = GPInvitation & { pending: true }
let pending = useList<PendingInvitation>({
  doctype: 'GP Invitation',
  filters: () => {
    return {
      projects: ['like', `%${props.spaceId}%`],
      role: 'Gameplan Guest',
      status: 'Pending',
    }
  },
  fields: ['email', 'projects', 'name'],
  transform(data) {
    return data.map((d) => ({ ...d, pending: true }))
  },
  immediate: false,
})

watch(show, (value) => {
  if (value && !guests.isFinished) {
    guests.fetch()
    pending.fetch()
  }
})

let guestsAndInvites = computed(() => {
  return [...(guests.data || []), ...(pending.data || [])]
})

const accessLabel = computed(() => (space.value?.is_private ? 'Private' : 'Public'))
const accessIcon = computed(() => (space.value?.is_private ? 'lucide-lock' : 'lucide-globe-2'))
const accessDescription = computed(() => {
  if (space.value?.is_private) {
    return 'Only selected community users and invited guests can view this space.'
  }
  return 'Every community user can view this space. Guests need an explicit invite.'
})

let addableUsers = computed(() => {
  let communityMembers = getCommunity(space.value?.team || '')?.members || []
  let communityMemberNames = new Set(communityMembers.map((member) => member.user))

  return (users.data || [])
    .filter((user) => user.enabled && !space.value?.members.find((m) => m.user === user.name))
    .filter((user) => user.isNotGuest && communityMemberNames.has(user.name))
    .map((user) => ({ value: user.name, label: user.full_name }))
})

let selectedUser = ref<string | null>(null)
let guestEmail = ref('')

function addMember() {
  if (space.value && selectedUser.value) {
    spaces.runDocMethod
      .submit({
        name: space.value.name,
        method: 'add_member',
        params: { user: selectedUser.value },
      })
      .then(() => {
        let fullName = useUser(selectedUser.value).full_name
        let spaceName = useSpace(space.value?.name).value?.title
        selectedUser.value = null
        toast.success(`${fullName} added to ${spaceName}`)
        guests.reload()
      })
  }
}

function invite() {
  if (space.value) {
    spaces.runDocMethod
      .submit({
        name: space.value.name,
        method: 'invite_guest',
        params: { email: guestEmail.value },
      })
      .then(() => {
        guestEmail.value = ''
        pending.reload()
      })
  }
}

let removeDialog = reactive({
  open: false,
  options: null,
})

function remove(user: GuestAccess | PendingInvitation) {
  if (user.pending) {
    removeDialog.options = {
      title: 'Delete Invitation',
      message: 'Are you sure you want to delete this invitation?',
      actions: [
        {
          label: 'Delete',
          variant: 'solid',
          theme: 'red',
          onClick: ({ close }) => {
            return pending.delete.submit({ name: user.name }).then(close)
          },
        },
      ],
    }
  } else {
    removeDialog.options = {
      title: 'Remove Guest User',
      message: `${useUser(user.user).full_name} will lose access to this space.`,
      actions: [
        {
          label: 'Remove',
          variant: 'solid',
          theme: 'red',
          onClick: ({ close }) => {
            if (!space.value) return
            return spaces.runDocMethod
              .submit({
                name: space.value.name,
                method: 'remove_guest',
                params: {
                  email: user.user,
                },
              })
              .then(() => {
                guests.reload()
                close()
              })
          },
        },
      ],
    }
  }
  removeDialog.open = true
}
</script>
