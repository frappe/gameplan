<template>
  <Dialog :options="{ title: 'Manage Guests' }" v-model="inviteGuestDialog">
    <template #body-content>
      <div class="my-4 space-y-2">
        <div
          class="flex items-center gap-4"
          v-for="user in users"
          :key="user.name"
        >
          <UserAvatar :user="user.pending ? user.email : user.user" />
          <div class="text-base">
            <span class="text-gray-900">
              {{ user.pending ? user.email : $user(user.user).full_name }}
            </span>
            <span class="text-gray-600" v-if="user.pending"> (Pending)</span>
          </div>
          <div class="ml-auto">
            <Tooltip :text="user.pending ? 'Remove invite' : 'Remove user'">
              <Button icon="x" label="Remove" @click="remove(user)" />
            </Tooltip>
          </div>
        </div>
      </div>
      <Input
        label="Email"
        v-model="email"
        placeholder="jane@example.com"
        @input="email = $event"
        @keydown.enter="invite"
      />
      <ErrorMessage class="mt-2" :message="project.inviteGuest.error" />
    </template>
    <template #actions>
      <Button
        appearance="primary"
        @click="invite"
        :loading="project.inviteGuest.loading"
      >
        Invite
      </Button>
      <Button @click="inviteGuestDialog = false">Cancel</Button>
    </template>
  </Dialog>
</template>
<script setup>
import { createListResource, Tooltip } from 'frappe-ui'
import { ref, computed } from 'vue'

const props = defineProps(['modelValue', 'project'])
const emit = defineEmits(['update:modelValue'])

let guests = createListResource({
  type: 'list',
  doctype: 'GP Guest Access',
  filters: { project: props.project.name },
  fields: ['user', 'project', 'name'],
})
guests.reload()

let pending = createListResource({
  type: 'list',
  doctype: 'GP Invitation',
  filters: {
    projects: ['like', `%${props.project.name}%`],
    role: 'Gameplan Guest',
    status: 'Pending',
  },
  fields: ['email', 'projects', 'name'],
  transform(data) {
    return data.map((d) => ({ ...d, pending: true }))
  },
})
pending.reload()

let users = computed(() => {
  return [...guests.data, ...pending.data]
})

let inviteGuestDialog = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})
let email = ref('')

function invite() {
  props.project.inviteGuest.submit(
    { email: email.value },
    {
      onSuccess() {
        email.value = ''
        pending.reload()
      },
    }
  )
}

function remove(user) {
  if (user.pending) {
    $dialog({
      title: 'Delete Invitation',
      message: 'Are you sure you want to delete this invitation?',
      actions: [
        {
          label: 'Delete',
          appearance: 'danger',
          handler: ({ close }) => {
            return pending.delete.submit(user.name).then(close)
          },
        },
        {
          label: 'Cancel',
        },
      ],
    })
  } else {
    $dialog({
      title: 'Remove Guest User',
      message: 'Are you sure you want to remove this guest user?',
      actions: [
        {
          label: 'Delete',
          appearance: 'danger',
          handler: ({ close }) => {
            return props.project.removeGuest.submit(
              { email: user.user },
              {
                onSuccess() {
                  guests.reload()
                  close()
                },
              }
            )
          },
        },
        {
          label: 'Cancel',
        },
      ],
    })
  }
}
</script>
