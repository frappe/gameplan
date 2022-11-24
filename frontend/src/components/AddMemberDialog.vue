<template>
  <Dialog
    :options="{ title: 'Invite members' }"
    @close="resetValues"
    v-model="open"
  >
    <template #body-content>
      <ul v-if="invites.length" class="flex flex-wrap gap-2 py-2">
        <li
          class="flex items-center space-x-2 rounded bg-gray-100 p-1"
          v-for="user in invites"
          :key="user.email"
          :title="user.email"
        >
          <UserAvatar :user="user.name" size="sm" />
          <span class="text-base" :class="{ 'ml-2': !user.user_image }">
            {{ user.full_name || user.email }}
          </span>
          <button
            @click="invites = invites.filter((a) => a != user)"
            class="grid h-4 w-4 place-items-center rounded text-gray-700 hover:bg-gray-300"
          >
            <FeatherIcon class="w-3" name="x" />
          </button>
        </li>
      </ul>
      <div>
        <Combobox v-model="selectedUser">
          <ComboboxInput as="template">
            <Input
              :debounce="200"
              @input="
                (value) => {
                  inviteQuery = value
                  addMembersIntent = true
                }
              "
              :value="inviteQuery"
              placeholder="Add member via name or email"
              autocomplete="off"
            />
          </ComboboxInput>
          <div
            v-if="addMembersIntent"
            class="mt-3 mb-1 text-sm font-semibold text-gray-500"
          >
            {{
              filteredUsers.length === 0
                ? 'Keep typing to invite via email'
                : 'Select a person to invite'
            }}
          </div>
          <ComboboxOptions
            class="max-h-[8rem] overflow-y-auto"
            :static="true"
            v-if="addMembersIntent"
          >
            <ComboboxOption
              as="template"
              v-slot="{ selected, active }"
              v-for="user in filteredUsers"
              :key="user.name"
              :value="user"
            >
              <li
                class="flex cursor-default select-none items-center space-x-2 rounded-md px-3 py-2 text-base"
                :class="{
                  'bg-gray-100': active,
                  'text-gray-900': !active,
                }"
                :title="user.email"
              >
                <UserAvatar
                  v-if="user.user_image"
                  :user="user.name"
                  size="sm"
                />
                <FeatherIcon
                  v-else-if="user.icon"
                  :name="user.icon"
                  class="h-4 w-4 text-gray-700"
                />
                <div
                  v-else
                  class="grid h-5 w-5 place-items-center rounded-full border bg-gray-100"
                >
                  <FeatherIcon class="h-3 w-3 text-gray-500" name="user" />
                </div>
                <span>
                  {{ user.full_name || user.email }}
                </span>
              </li>
            </ComboboxOption>
          </ComboboxOptions>
        </Combobox>
        <ErrorMessage class="mt-2" :message="resource.inviteMembers.error" />
      </div>
      <div class="mt-4" v-show="!addMembersIntent">
        <h4 class="text-base font-medium">Members</h4>
        <ul role="list" class="mt-2 divide-y">
          <li
            class="flex w-full items-center space-x-2 py-2"
            v-for="member in members"
            :key="member.name"
          >
            <UserAvatar :user="member.email" />
            <div>
              <div class="text-base font-medium text-gray-800">
                {{ member.full_name || member.email }}
              </div>
              <div class="text-sm text-gray-600">
                {{ member.full_name ? member.email : '' }}
              </div>
            </div>
            <Badge class="!ml-auto" v-if="member.status == 'Invited'">
              Pending invite
            </Badge>
          </li>
        </ul>
      </div>
    </template>
    <template #actions v-if="invites.length">
      <Button
        appearance="primary"
        @click="sendInvites"
        :loading="resource.inviteMembers.loading"
      >
        Send invitation
      </Button>
      <Button @click="open = false"> Cancel </Button>
    </template>
  </Dialog>
</template>
<script>
import { Avatar, ErrorMessage, Badge } from 'frappe-ui'
import {
  Combobox,
  ComboboxInput,
  ComboboxOptions,
  ComboboxOption,
} from '@headlessui/vue'
import InputWithPills from './InputWithPills.vue'

export default {
  name: 'AddMemberDialog',
  props: ['resource', 'modelValue'],
  components: {
    InputWithPills,
    ErrorMessage,
    Avatar,
    Badge,
    Combobox,
    ComboboxInput,
    ComboboxOptions,
    ComboboxOption,
  },
  data() {
    return {
      invites: [],
      inviteQuery: '',
      selectedUser: null,
      addMembersIntent: false,
    }
  },
  watch: {
    selectedUser(user) {
      if (user === null) return
      if (!this.invites.includes(user)) {
        this.invites.push(user)
        this.inviteQuery = ''
        this.selectedUser = null
      }
    },
  },
  computed: {
    open: {
      get() {
        return this.modelValue
      },
      set(val) {
        this.$emit('update:modelValue', val)
        if (!val) {
          this.$emit('close')
        }
      },
    },
    members() {
      return this.resource.doc.members.map((member) => {
        let { full_name, user_image } = this.$user(member.email)
        return {
          ...member,
          full_name,
          user_image,
        }
      })
    },
    invitableUsers() {
      let memberEmails = this.members.map((m) => m.email)
      memberEmails = memberEmails.concat(this.invites.map((user) => user.email))

      return this.$users.data
        .filter((user) => !memberEmails.includes(user.email))
        .sort((a, b) => a.full_name - b.full_name)
    },
    filteredUsers() {
      if (!this.inviteQuery) {
        return this.invitableUsers
      } else {
        let users = this.invitableUsers.filter((user) => {
          let searchTexts = [user.full_name.toLowerCase(), user.email]
          return searchTexts.some((text) => text.includes(this.inviteQuery))
        })
        if (users.length == 0) {
          // https://stackoverflow.com/a/46181
          let emailRegex =
            /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/

          if (emailRegex.test(this.inviteQuery)) {
            users.push({
              icon: 'mail',
              email: this.inviteQuery,
            })
          }
        }
        return users
      }
    },
  },
  methods: {
    sendInvites() {
      let emails = this.invites.map((user) => user.email)
      this.resource.inviteMembers.submit({ emails }).then(() => {
        this.invites = []
        this.addMembersIntent = false
      })
    },
    resetValues() {
      this.open = false
      this.invites = []
      this.inviteQuery = ''
      this.selectedUser = null
      this.addMembersIntent = false
    },
  },
}
</script>
