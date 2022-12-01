<template>
  <div>
    <div class="flex items-center space-x-2">
      <h2 class="text-2xl font-bold text-gray-900">Members</h2>
      <Button icon="plus" @click="addMember.show = true" />
    </div>
    <div class="mt-4 grid grid-cols-1">
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
            class="group flex w-full items-center rounded-md p-2 transition-colors"
            :class="open ? 'bg-gray-100' : 'hover:bg-gray-50'"
          >
            <UserAvatar :user="member.email" />
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
              class="ml-auto w-4 text-gray-700 transition-opacity"
              :class="
                open ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
              "
            />
          </button>
        </template>
      </Dropdown>
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
            url: 'frappe.client.set_value',
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
import { Dropdown, Dialog, Resource } from 'frappe-ui'
import AddMemberDialog from '@/components/AddMemberDialog.vue'

export default {
  name: 'ProjectOverviewMembers',
  props: ['project'],
  components: { Dropdown, Dialog, Resource, AddMemberDialog },
  data() {
    return {
      updateMemberRole: { member: null, show: false },
      addMember: { show: false },
    }
  },
}
</script>
