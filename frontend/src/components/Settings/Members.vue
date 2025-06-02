<template>
  <div class="flex min-h-0 flex-col">
    <div class="flex items-center justify-between">
      <h2 class="text-xl font-semibold leading-none">Members</h2>
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
<script>
import { h, computed } from 'vue'
import { Dropdown } from 'frappe-ui'
import { users, activeUsers } from '@/data/users'
import LucideCheck from '~icons/lucide/check'

export default {
  name: 'Members',
  components: { Dropdown },
  resources: {
    changeUserRole() {
      return {
        url: 'gameplan.api.change_user_role',
        onSuccess(user) {
          users.setData((data) => {
            return data.map((_user) => {
              if (_user.name === user.name) {
                return user
              }
              return _user
            })
          })
        },
      }
    },
    removeUser() {
      return {
        url: 'gameplan.api.remove_user',
        onSuccess(user) {
          users.setData((data) => data.filter((_user) => _user.name !== user))
        },
      }
    },
  },
  data() {
    return {
      search: '',
    }
  },
  computed: {
    filteredUsers() {
      if (!this.search) {
        return activeUsers.value
      }
      return activeUsers.value.filter((user) => {
        let term = this.search.toLowerCase()
        return user.name.toLowerCase().includes(term) || user.full_name.toLowerCase().includes(term)
      })
    },
  },
  methods: {
    changeUserRole({ user, role }) {
      this.$dialog({
        title: 'Change Role',
        message: `Are you sure you want to change ${user.full_name}'s role to ${role}?`,
        error: computed(() => this.$resources.changeUserRole.error),
        actions: [
          {
            label: 'Change Role',
            variant: 'solid',
            onClick: (close) => {
              return this.$resources.changeUserRole.submit(
                { user: user.name, role },
                { onSuccess: close },
              )
            },
          },
          {
            label: 'Cancel',
          },
        ],
      })
    },
    removeUser(user) {
      this.$dialog({
        title: 'Remove User',
        message: `Are you sure you want to remove ${user.full_name} (${user.email})?`,
        error: computed(() => this.$resources.removeUser.error),
        actions: [
          {
            label: 'Remove User',
            variant: 'solid',
            theme: 'red',
            onClick: (close) => {
              return this.$resources.removeUser.submit({ user: user.name }, { onSuccess: close })
            },
          },
          {
            label: 'Cancel',
          },
        ],
      })
    },
    getUserRole(user) {
      return (user.role || '').replace('Gameplan', '')
    },
    getDropdownOptions(user) {
      return [
        {
          label: 'Admin',
          component: (props) =>
            RoleOption({
              role: 'Admin',
              active: props.active,
              selected: user.role === 'Gameplan Admin',
              onClick: () =>
                this.changeUserRole({
                  user: user,
                  role: 'Gameplan Admin',
                }),
            }),
        },
        {
          label: 'Member',
          component: (props) =>
            RoleOption({
              role: 'Member',
              active: props.active,
              selected: user.role === 'Gameplan Member',
              onClick: () =>
                this.changeUserRole({
                  user: user,
                  role: 'Gameplan Member',
                }),
            }),
        },
        {
          label: 'Guest',
          component: (props) =>
            RoleOption({
              role: 'Guest',
              active: props.active,
              selected: user.role === 'Gameplan Guest',
              onClick: () =>
                this.changeUserRole({
                  user: user,
                  role: 'Gameplan Guest',
                }),
            }),
        },
        {
          label: 'Remove',
          component: (props) =>
            h(
              'button',
              {
                class: [
                  props.active ? 'bg-surface-gray-2' : '',
                  'group flex w-full items-center text-ink-red-3 rounded-md px-2 py-2 text-sm',
                ],
                onClick: () => this.removeUser(user),
              },
              'Remove',
            ),
        },
      ]
    },
  },
}

function RoleOption({ active, role, onClick, selected }) {
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
