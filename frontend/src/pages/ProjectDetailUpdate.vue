<template>
  <div class="relative">
    <div class="container h-full mt-6">
      <Button iconLeft="edit" :route="{ name: 'ProjectDetailUpdateNew' }">
        Write a new status update
      </Button>
      <div class="relative w-1/2 h-full pr-4 mt-6 space-y-8">
        <!-- vertical line -->
        <div
          class="absolute top-0 bottom-0 border-l left-3.5 z-[-1] -translate-x-[0.5px]"
        ></div>
        <div
          class="flex items-start space-x-4"
          v-for="d in activity"
          :key="d.key"
        >
          <div>
            <div
              class="grid bg-white border border-gray-300 rounded-full place-items-center w-7 h-7"
            >
              <FeatherIcon
                :name="d.icon || 'circle'"
                class="w-3 h-3 text-gray-600"
              />
            </div>
          </div>
          <div class="flex items-start mt-1 space-x-2">
            <div>
              <div class="text-base" v-if="d.type === 'create'">
                <UserInfo :email="d.user" :key="d.key">
                  <template v-slot="{ user }">
                    <span class="font-medium text-gray-900">
                      {{ user.full_name }}
                    </span>
                    <span class="text-gray-600"> created this project </span>
                  </template>
                </UserInfo>
              </div>
              <div class="text-base" v-else-if="d.type === 'update'">
                <span class="font-medium text-gray-900">
                  {{ d.title }}
                </span>
                <span class="text-gray-600"> by </span>
                <UserInfo :email="d.user" :key="d.key">
                  <template v-slot="{ user }">
                    <span class="font-medium text-gray-900">
                      {{ user.full_name }}
                    </span>
                  </template>
                </UserInfo>
              </div>

              <div class="mt-1 mb-3" v-if="d.type === 'update'">
                <Button
                  appearance="white"
                  icon-right="chevron-right"
                  :route="{
                    name: 'ProjectDetailUpdateView',
                    params: { updateId: d.name },
                  }"
                >
                  View update
                </Button>
              </div>
              <div
                class="mt-1 text-base text-gray-600"
                :title="$dayjs(d.timestamp)"
              >
                {{ $dayjs(d.timestamp).format('d MMM, YYYY') }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div
      class="absolute top-0 bottom-0 right-0 w-1/2 border-l"
      v-if="
        $route.name in { ProjectDetailUpdateNew: 1, ProjectDetailUpdateView: 1 }
      "
    >
      <router-view :project="project" />
    </div>
  </div>
</template>
<script>
import { Avatar, TextEditor } from 'frappe-ui'
import Link from '@/components/Link.vue'

export default {
  name: 'ProjectDetailUpdate',
  props: ['project'],
  components: { TextEditor, Avatar, Link },
  resources: {
    updates() {
      return {
        type: 'list',
        cache: ['Project Updates', this.project.doc.name],
        doctype: 'Team Project Status Update',
        filters: {
          project: this.project.doc.name,
        },
        fields: ['*'],
        order_by: 'creation desc',
      }
    },
  },
  computed: {
    activity() {
      return [
        ...(this.$resources.updates.data || []).map((update) => {
          return {
            type: 'update',
            icon: 'edit',
            user: update.owner,
            timestamp: update.creation,
            title: update.title,
            status: update.status,
            name: update.name,
            key: update.name,
          }
        }),
        {
          type: 'create',
          icon: 'plus',
          user: this.project.doc.owner,
          timestamp: this.project.doc.creation,
          key: 'create',
        },
      ]
    },
  },
}
</script>
