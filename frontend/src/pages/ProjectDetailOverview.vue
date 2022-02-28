<template>
  <div class="container mt-6 space-y-6">
    <div class="w-1/2">
      <h2 class="text-lg font-bold">Description</h2>
      <TextEditor
        class="w-full px-3 py-2 mt-2 prose-sm prose max-w-[unset] rounded-lg bg-gray-50"
        :showBubbleMenu="true"
        :content="project.description"
        placeholder="Add a description for your project"
        @change="
          (val) => {
            $resources.updateProject.submit({ description: val })
          }
        "
      />
    </div>
    <div class="w-1/2">
      <h2 class="text-lg font-bold">Members</h2>
      <div class="grid grid-cols-3 gap-1 mt-4">
        <Dropdown
          v-for="member in project.members"
          :key="member.user"
          :options="[
            {
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
                        return $call(
                          `/api/resource/Team Project/${project.name}`,
                          {
                            run_method: 'remove_member',
                            user: member.user,
                          }
                        ).then((data) => {
                          console.log(data)
                          $refetchResource(['Team Project', project.name])
                          close()
                        })
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
                :label="member.full_name"
                :imageURL="member.user_image"
              />
              <div class="ml-2">
                <div class="text-sm font-semibold text-gray-700">
                  {{ member.full_name }}
                </div>
                <div class="flex text-xs text-gray-600">
                  {{ member.role || '+ Add Role' }}
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
        <button class="flex items-center p-2 rounded-lg hover:bg-gray-50">
          <div
            class="grid w-8 h-8 text-gray-600 border border-gray-400 border-dashed rounded-full place-items-center"
          >
            <FeatherIcon name="plus" class="w-4" />
          </div>
          <div class="ml-2 text-sm font-semibold text-gray-500">Add member</div>
        </button>
      </div>

      <Dialog
        :options="{ title: 'Update Role' }"
        v-model="updateMemberRole.show"
      >
        <template v-if="updateMemberRole.member" #body-content>
          <Input
            type="text"
            :label="`What is the role of ${updateMemberRole.member.full_name} in this project?`"
            v-model="updateMemberRole.member.role"
          />
        </template>
        <template #actions>
          <Resource
            :options="{
              method: 'frappe.client.set_value',
              params: {
                doctype: 'Team Member',
                name: updateMemberRole.member.name,
                fieldname: {
                  role: updateMemberRole.member.role,
                },
              },
              onSuccess() {
                updateMemberRole.show = false
              },
            }"
            v-slot="{ resource }"
          >
            <Button
              appearance="primary"
              @click="resource.submit()"
              :loading="resource.loading"
            >
              Update
            </Button>
          </Resource>
        </template>
      </Dialog>

      <!-- <Dialog :options="{ title: 'Add members to this project' }">
        <template #body-content> </template>
      </Dialog> -->
    </div>
    <div class="w-1/2">
      <h2 class="text-lg font-bold">Activity</h2>
      <div class="mt-6 mb-8">
        <Button
          icon-left="edit-3"
          @click="writingStatusUpdate = true"
          v-if="!writingStatusUpdate"
        >
          Write a status update
        </Button>
        <div v-if="writingStatusUpdate">
          <Input
            label="Project Status"
            type="select"
            :options="['', 'On Track', 'Off Track', 'Completed']"
            v-model="statusUpdate.status"
          />
          <div class="mt-4">
            <label for="#status-update" class="mb-2 text-sm text-gray-700">
              Summary
            </label>
            <TextEditor
              id="status-update"
              class="w-full px-3 py-2 prose-sm prose max-w-[unset] rounded-lg bg-gray-50"
              editor-class="min-h-[6rem]"
              placeholder="Project updates..."
              :showMenu="true"
              :content="statusUpdate.content"
              @change="(val) => (statusUpdate.content = val)"
            />
          </div>
          <div class="mt-4 space-x-2">
            <Button
              appearance="primary"
              @click="$resources.statusUpdate.submit()"
              :loading="$resources.statusUpdate.loading"
            >
              Submit
            </Button>
            <Button
              @click="
                () => {
                  writingStatusUpdate = false
                  statusUpdate = { content: '', status: '' }
                }
              "
            >
              Cancel
            </Button>
          </div>
        </div>
      </div>

      <div v-for="activity in $resources.activities.data" :key="activity.date">
        <div class="my-6">
          <template v-if="activity.type === 'info'">
            <div class="flex space-x-2">
              <div class="flex justify-center w-8">
                <FeatherIcon name="circle" class="w-4 text-gray-500" />
              </div>
              <div class="text-base text-gray-700">
                {{ activity.title }} by {{ activity.user }}
              </div>
            </div>
          </template>
          <template v-else-if="activity.type === 'content'">
            <div class="flex space-x-2">
              <Avatar :label="activity.user" />
              <div>
                <div class="py-1 text-lg font-semibold">
                  {{ activity.status }}
                </div>
                <div v-html="activity.content" class="prose-sm prose"></div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
<script>
import { Avatar, TextEditor, Dropdown, Dialog, Resource } from 'frappe-ui'
import InputWithSuggestions from '@/components/InputWithSuggestions.vue'

export default {
  name: 'ProjectDetailOverview',
  props: ['project'],
  components: {
    Avatar,
    TextEditor,
    Dropdown,
    Dialog,
    Resource,
    InputWithSuggestions,
  },
  data() {
    return {
      writingStatusUpdate: false,
      statusUpdate: {
        content: '',
        status: '',
      },
      updateMemberRole: { member: null, show: false },
    }
  },
  resources: {
    activities() {
      return {
        method: 'teams.api.project_activities',
        params: {
          project: this.project.name,
        },
        auto: true,
      }
    },
    updateProject() {
      return {
        method: 'frappe.client.set_value',
        makeParams(args) {
          return {
            doctype: 'Team Project',
            name: this.project.name,
            fieldname: args,
          }
        },
        debounce: 500,
      }
    },
    statusUpdate() {
      return {
        method: 'frappe.client.insert',
        params: {
          doc: {
            doctype: 'Team Project Status Update',
            project: this.project.name,
            status: this.statusUpdate.status,
            content: this.statusUpdate.content,
          },
        },
        onSuccess() {
          this.resetStatusUpdate()
          this.$resources.activities.reload()
        },
      }
    },
  },
  methods: {
    resetStatusUpdate() {
      this.writingStatusUpdate = false
      this.statusUpdate = { content: '', status: '' }
    },
  },
}
</script>
