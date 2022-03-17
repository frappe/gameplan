<template>
  <Dialog :options="{ title: 'Invite members' }" v-model="open">
    <template #body-content>
      <div>
        <InputWithPills
          class="mt-4"
          :options="getUserOptions"
          placeholder="Add member via name or email"
          v-model="invites"
        >
        </InputWithPills>
        <ErrorMessage class="mt-2" :message="resource.error" />
        <div class="mt-2">
          <Button
            v-if="invites.length"
            appearance="primary"
            @click="sendInvites"
            :loading="resource.loading"
          >
            Send invitation
          </Button>
        </div>
      </div>

      <div class="mt-4">
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
  </Dialog>
</template>
<script>
import { computed, ref } from 'vue'
import InputWithPills from './InputWithPills.vue'
import ErrorMessage from 'frappe-ui/src/components/ErrorMessage.vue'
import Avatar from 'frappe-ui/src/components/Avatar.vue'
import Badge from 'frappe-ui/src/components/Badge.vue'

export default {
  name: 'AddMemberDialog',
  props: ['project', 'team'],
  components: {
    InputWithPills,
    ErrorMessage,
    Avatar,
    Badge,
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
    users() {
      return {
        method: 'teams.api.get_system_users',
        cache: 'system_users',
        auto: true,
      }
    },
  },
  setup(props, { emit }) {
    let open = computed({
      get: () => props.modelValue,
      set: (val) => {
        emit('update:modelValue', val)
        if (!val) {
          emit('close')
        }
      },
    })
    let invites = ref([])
    return {
      open,
      invites,
    }
  },
  computed: {
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
  },
  methods: {
    getUserOptions({ query }) {
      let users = this.$resources.users.data
      let existingUsers = this.members.map((member) => member.email)

      let options = users
        .filter((user) => {
          if (existingUsers.includes(user.email)) {
            return false
          }
          if (query) {
            return user.full_name.toLowerCase().includes(query.toLowerCase())
          }
          return true
        })
        .map((user) => ({
          label: user.full_name,
          value: user.name,
        }))

      let emailRegex = /^\w+@[a-zA-Z_]+?\.[a-zA-Z]{2,3}$/
      if (emailRegex.test(query)) {
        options.push({
          label: `+ Invite ${query} via email`,
          value: query,
          displayValue: query,
        })
      }
      return options
    },
    sendInvites() {
      let emails = this.invites.map((invite) => invite.value)
      this.resource.submit({ emails }).then(() => {
        this.open = false
        this.invites = []
      })
    },
  },
}
</script>
