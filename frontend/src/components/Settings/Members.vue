<template>
  <div v-if="!inviteMembers" class="flex min-h-0 flex-col p-5">
    <div class="flex items-center justify-between">
      <h2 class="text-xl font-bold leading-none">Members</h2>
      <div class="flex items-center gap-4">
        <Input
          icon-left="search"
          type="text"
          placeholder="Search by name / email"
          @input="search = $event"
          :debounce="300"
        />
        <Button icon-left="user-plus" @click="inviteMembers = true">
          Invite People
        </Button>
      </div>
    </div>
    <div
      class="mt-2 flex items-center justify-between border-b py-2 text-base text-gray-600"
    >
      <div class="w-4/5">User</div>
      <div class="w-1/5 px-3">Role</div>
    </div>
    <ul class="divide-y overflow-auto">
      <li
        class="flex items-center justify-between py-2"
        v-for="user in filteredUsers"
        :key="user.name"
      >
        <div class="w-4/5">
          <div class="text-base">
            {{ user.full_name }}
          </div>
          <div class="text-sm text-gray-600">
            {{ user.email }}
          </div>
        </div>
        <div class="flex w-1/5">
          <Dropdown
            :options="getDropdownOptions(user)"
            :button="{
              label: getUserRole(user),
              iconRight: 'chevron-down',
              appearance: 'minimal',
            }"
            placement="right"
          ></Dropdown>
        </div>
      </li>
    </ul>
  </div>
  <InvitePeople v-else @back="inviteMembers = false" />
</template>
<script>
import { h, computed } from 'vue'
import { Dropdown, FeatherIcon } from 'frappe-ui'
import InvitePeople from './InvitePeople.vue'
import { users } from '@/data/users'

export default {
  name: 'Members',
  components: { Dropdown, InvitePeople },
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
      inviteMembers: false,
    }
  },
  computed: {
    filteredUsers() {
      if (!this.search) {
        return users.data
      }
      return users.data.filter((user) => {
        let term = this.search.toLowerCase()
        return (
          user.name.toLowerCase().includes(term) ||
          user.full_name.toLowerCase().includes(term)
        )
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
            appearance: 'primary',
            handler: ({ close }) => {
              return this.$resources.changeUserRole.submit(
                { user: user.name, role },
                { onSuccess: close }
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
            appearance: 'danger',
            handler: ({ close }) => {
              return this.$resources.removeUser.submit(
                { user: user.name },
                { onSuccess: close }
              )
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
                  props.active ? 'bg-gray-100' : '',
                  'group flex w-full items-center text-red-500 rounded-md px-2 py-2 text-sm',
                ],
                onClick: () => this.removeUser(user),
              },
              'Remove'
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
        active ? 'bg-gray-100' : 'text-gray-900',
        'group flex w-full justify-between items-center rounded-md px-2 py-2 text-sm',
      ],
      onClick: !selected ? onClick : null,
    },
    [
      h('span', { class: 'whitespace-nowrap' }, role),
      selected
        ? h(FeatherIcon, {
            name: 'check',
            class: ['h-4 w-4 shrink-0 text-gray-700'],
            'aria-hidden': true,
          })
        : null,
    ]
  )
}
</script>
