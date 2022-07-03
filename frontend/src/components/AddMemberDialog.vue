<template>
  <Dialog
    :options="{ title: 'Invite members' }"
    @close="resetValues"
    v-model="open"
  >
    <template #body-content>
      <ul v-if="invites.length" class="flex flex-wrap gap-2 py-2">
        <li
          class="flex items-center p-1 space-x-2 bg-gray-100 rounded"
          v-for="user in invites"
          :key="user.email"
          :title="user.email"
        >
          <Avatar
            v-if="user.user_image"
            size="sm"
            :imageURL="user.user_image"
          />
          <span class="text-base" :class="{ 'ml-2': !user.user_image }">
            {{ user.full_name || user.email }}
          </span>
          <button
            @click="invites = invites.filter((a) => a != user)"
            class="grid w-4 h-4 text-gray-700 rounded hover:bg-gray-300 place-items-center"
          >
            <FeatherIcon class="w-3" name="x" />
          </button>
        </li>
      </ul>
      <div>
        <Combobox v-model="selectedUser">
          <ComboboxInput
            class="w-full form-input"
            @change="
              (e) => {
                inviteQuery = e.target.value
                addMembersIntent = true
              }
            "
            placeholder="Add member via name or email"
            autocomplete="off"
          />
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
            class="h-[7rem] overflow-y-auto"
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
                class="flex items-center px-3 py-2 space-x-2 text-base rounded-md cursor-default select-none"
                :class="{
                  'bg-gray-100': active,
                  'text-gray-900': !active,
                }"
                :title="user.email"
              >
                <Avatar
                  v-if="user.user_image"
                  size="sm"
                  :imageURL="user.user_image"
                />
                <FeatherIcon
                  v-else-if="user.icon"
                  :name="user.icon"
                  class="w-4 h-4 text-gray-700"
                />
                <div
                  v-else
                  class="grid w-5 h-5 bg-gray-100 border rounded-full place-items-center"
                >
                  <FeatherIcon class="w-3 h-3 text-gray-500" name="user" />
                </div>
                <span>
                  {{ user.full_name || user.email }}
                </span>
              </li>
            </ComboboxOption>
          </ComboboxOptions>
        </Combobox>
        <ErrorMessage class="mt-2" :message="resource.error" />
      </div>
      <div class="mt-4" v-show="!addMembersIntent">
        <h4 class="text-base font-medium">Members</h4>
        <ul role="list" class="mt-2 divide-y">
          <li
            class="flex items-center w-full py-2 space-x-2"
            v-for="member in members"
            :key="member.name"
          >
            <Avatar
              :imageURL="member.user_image"
              :label="member.full_name || member.email"
            />
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
    <template #actions>
      <Button
        v-if="invites.length"
        appearance="primary"
        @click="sendInvites"
        :loading="resource.loading"
      >
        Send invitation
      </Button>
      <Button v-if="invites.length" @click="open = false"> Cancel </Button>
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
  props: ['project', 'team'],
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
  resources: {
    project() {
      return {
        type: 'document',
        doctype: 'Team Project',
        name: this.project?.name,
      }
    },
    team() {
      return {
        type: 'document',
        doctype: 'Team',
        name: this.team?.name,
      }
    },
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
    resource() {
      if (this.team) {
        return this.$resources.team.inviteMembers
      }
      if (this.project) {
        return this.$resources.project.inviteMembers
      }
    },
    members() {
      if (this.team) {
        return this.team.members
      }
      if (this.project) {
        return this.project.members
      }
    },
    invitableUsers() {
      let memberEmails = this.members.map((m) => m.email)
      return Object.values(this.$users.data)
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
          let emailRegex = /^\w+@[a-zA-Z_]+?\.[a-zA-Z]{2,3}$/
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
      this.resource.submit({ emails }).then(() => {
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
