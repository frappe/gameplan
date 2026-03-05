<template>
  <div class="flex min-h-0 flex-col">
    <div class="flex items-center justify-between">
      <h2 class="text-xl font-semibold leading-none text-ink-gray-9">Members</h2>
      <div class="flex items-center gap-4">
        <FormControl placeholder="Search" @input="search = $event.target.value" :debounce="300">
          <template #prefix>
            <LucideSearch class="h-4 w-4 text-ink-gray-4" />
          </template>
        </FormControl>
      </div>
    </div>
    <ul class="mt-6 divide-y overflow-auto pb-16">
      <li
        class="flex items-center justify-between p-2"
        v-for="user in filteredUsers"
        :key="user.name"
      >
        <div class="flex w-4/5 items-center">
          <UserAvatar :user="user.name" size="xl" />
          <div class="ml-3">
            <div class="text-base text-ink-gray-8">
              {{ user.full_name }}
            </div>
            <div class="mt-1 text-base text-ink-gray-6">
              {{ user.email }}
            </div>
          </div>
        </div>
        <div class="flex w-1/5 justify-end">
          <Dropdown
            :options="getDropdownOptions(user)"
            :button="{
              label: getUserRole(user),
              iconRight: 'chevron-down',
              variant: 'ghost',
            }"
            placement="right"
          ></Dropdown>
        </div>
      </li>
    </ul>
  </div>
</template>
<script setup lang="ts">
import { computed, h, ref } from 'vue'
import { Dropdown, useCall } from 'frappe-ui'
import { users, activeUsers } from '@/data/users'
import { createDialog } from '@/utils/dialogs'
import LucideCheck from '~icons/lucide/check'

type MemberRole = 'Gameplan Admin' | 'Gameplan Member' | 'Gameplan Guest'

type MemberUser = {
  name: string
  full_name: string
  email: string
  role?: MemberRole
}

type DropdownRenderProps = {
  active: boolean
}

const search = ref('')

const changeUserRoleCall = useCall<undefined, { user: string; role: MemberRole }>({
  url: '/api/v2/method/gameplan.api.change_user_role',
  method: 'POST',
  immediate: false,
  onSuccess: () => {
    users.reload()
  },
})

const removeUserCall = useCall<undefined, { user: string }>({
  url: '/api/v2/method/gameplan.api.remove_user',
  method: 'POST',
  immediate: false,
  onSuccess: () => {
    users.reload()
  },
})

const filteredUsers = computed(() => {
  let term = search.value.trim().toLowerCase()
  if (!term) {
    return activeUsers.value
  }
  return activeUsers.value.filter((user) => {
    return user.name.toLowerCase().includes(term) || user.full_name.toLowerCase().includes(term)
  })
})

function changeUserRole({ user, role }: { user: MemberUser; role: MemberRole }) {
  createDialog({
    title: 'Change Role',
    message: `Are you sure you want to change ${user.full_name}'s role to ${role}?`,
    actions: [
      {
        label: 'Change Role',
        variant: 'solid',
        loading: changeUserRoleCall.loading,
        onClick: ({ close }) => {
          return changeUserRoleCall.submit({ user: user.name, role }).then(close)
        },
      },
      {
        label: 'Cancel',
      },
    ],
  })
}

function removeUser(user: MemberUser) {
  createDialog({
    title: 'Remove User',
    message: `Are you sure you want to remove ${user.full_name} (${user.email})?`,
    actions: [
      {
        label: 'Remove User',
        variant: 'solid',
        theme: 'red',
        loading: removeUserCall.loading,
        onClick: ({ close }) => {
          return removeUserCall.submit({ user: user.name }).then(close)
        },
      },
      {
        label: 'Cancel',
      },
    ],
  })
}

function getUserRole(user: MemberUser) {
  return (user.role || '').replace('Gameplan', '')
}

function getDropdownOptions(user: MemberUser) {
  return [
    {
      label: 'Admin',
      component: (props: DropdownRenderProps) =>
        RoleOption({
          role: 'Admin',
          active: props.active,
          selected: user.role === 'Gameplan Admin',
          onClick: () =>
            changeUserRole({
              user,
              role: 'Gameplan Admin',
            }),
        }),
    },
    {
      label: 'Member',
      component: (props: DropdownRenderProps) =>
        RoleOption({
          role: 'Member',
          active: props.active,
          selected: user.role === 'Gameplan Member',
          onClick: () =>
            changeUserRole({
              user,
              role: 'Gameplan Member',
            }),
        }),
    },
    {
      label: 'Guest',
      component: (props: DropdownRenderProps) =>
        RoleOption({
          role: 'Guest',
          active: props.active,
          selected: user.role === 'Gameplan Guest',
          onClick: () =>
            changeUserRole({
              user,
              role: 'Gameplan Guest',
            }),
        }),
    },
    {
      label: 'Remove',
      component: (props: DropdownRenderProps) =>
        h(
          'button',
          {
            class: [
              props.active ? 'bg-surface-gray-2' : '',
              'group flex w-full items-center text-ink-red-3 rounded-md px-2 py-2 text-sm',
            ],
            onClick: () => removeUser(user),
          },
          'Remove',
        ),
    },
  ]
}

function RoleOption({
  active,
  role,
  onClick,
  selected,
}: {
  active: boolean
  role: 'Admin' | 'Member' | 'Guest'
  onClick: () => void
  selected: boolean
}) {
  return h(
    'button',
    {
      class: [
        active ? 'bg-surface-gray-2' : 'text-ink-gray-8',
        'group flex w-full justify-between items-center rounded-md px-2 py-2 text-sm',
      ],
      onClick: !selected ? onClick : null,
    },
    [
      h('span', { class: 'whitespace-nowrap' }, role),
      selected
        ? h(LucideCheck, {
            class: ['h-4 w-4 shrink-0 text-ink-gray-6'],
            'aria-hidden': true,
          })
        : null,
    ],
  )
}
</script>
