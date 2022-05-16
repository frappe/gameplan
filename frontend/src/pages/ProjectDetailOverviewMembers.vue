<template>
  <div>
    <h2 class="text-lg font-bold">Members</h2>
    <div class="grid grid-cols-1 mt-4">
      <Dropdown
        v-for="member in project.doc.members"
        :key="member.user"
        :options="[
          member.status === 'Accepted' && {
            label: member.role ? 'Change Role' : 'Add Role',
            handler: () => {
              updateMemberRole.member = member
              updateMemberRole.show = true
            },
          },
          {
            label: 'Remove from project',
            handler: () =>
              this.$dialog({
                title: `Remove member`,
                message: `Are you sure you want to remove ${member.full_name} from this project?`,
                actions: [
                  {
                    label: 'Remove',
                    appearance: 'danger',
                    handler: ({ close }) => {
                      project.removeMember
                        .submit({ user: member.user })
                        .then(() => close())
                    },
                  },
                  { label: 'Cancel' },
                ],
              }),
          },
        ]"
      >
        <template v-slot="{ open }">
          <button
            class="flex items-center w-full p-2 transition-colors rounded-md group"
            :class="open ? 'bg-gray-100' : 'hover:bg-gray-50'"
          >
            <Avatar
              class="flex-shrink-0"
              :label="member.full_name || member.email"
              :imageURL="member.user_image"
            />
            <div class="ml-2">
              <div class="flex text-sm font-semibold text-gray-700">
                {{ member.full_name || member.email }}
              </div>
              <div class="flex text-xs text-gray-600">
                {{
                  member.status === 'Accepted'
                    ? member.role || '+ Add Role'
                    : 'Invited'
                }}
              </div>
            </div>
            <FeatherIcon
              name="chevron-down"
              class="w-4 ml-auto text-gray-700 transition-opacity"
              :class="
                open ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
              "
            />
          </button>
        </template>
      </Dropdown>
      <button
        class="flex items-center p-2 rounded-lg hover:bg-gray-50"
        @click="addMember.show = true"
      >
        <div
          class="grid w-8 h-8 text-gray-600 border border-gray-400 border-dashed rounded-full place-items-center"
        >
          <FeatherIcon name="plus" class="w-4" />
        </div>
        <div class="ml-2 text-sm font-semibold text-gray-500">Add member</div>
      </button>
    </div>

    <Dialog :options="{ title: 'Update Role' }" v-model="updateMemberRole.show">
      <template v-if="updateMemberRole.member" #body-content>
        <Input
          ref="memberRole"
          type="text"
          :label="`What is the role of ${updateMemberRole.member.full_name} in this project?`"
        />
      </template>
      <template #actions>
        <Resource
          :options="{
            method: 'frappe.client.set_value',
            onSuccess() {
              updateMemberRole.show = false
              project.get.reload()
            },
          }"
          v-slot="{ resource }"
        >
          <Button
            appearance="primary"
            @click="
              resource.submit({
                doctype: 'Team Member',
                name: updateMemberRole.member.name,
                fieldname: {
                  role: $refs.memberRole.getInputValue(),
                },
              })
            "
            :loading="resource.loading"
          >
            Update
          </Button>
        </Resource>
      </template>
    </Dialog>
    <AddMemberDialog :project="project.doc" v-model="addMember.show" />
  </div>
</template>
<script>
import { Avatar, Dropdown, Dialog, Resource } from 'frappe-ui'
import AddMemberDialog from '@/components/AddMemberDialog.vue'

export default {
  name: 'ProjectDetailOverviewMembers',
  props: ['project'],
  components: { Avatar, Dropdown, Dialog, Resource, AddMemberDialog },
  data() {
    return {
      updateMemberRole: { member: null, show: false },
      addMember: { show: false },
    }
  },
}
</script>
