<template>
  <div class="flex">
    <div class="w-5/12 h-full px-6 py-6 overflow-auto">
      <div class="relative h-full space-y-3">
        <router-link
          custom
          :to="{ name: 'ProjectDetailUpdateNew' }"
          v-slot="{ href, navigate }"
        >
          <a
            :href="href"
            @click="navigate"
            class="block p-3 rounded-xl"
            :class="
              $route.name === 'ProjectDetailUpdateNew'
                ? 'bg-gray-100'
                : 'hover:bg-gray-50'
            "
          >
            <div class="flex items-center space-x-4">
              <Avatar
                :label="$user().full_name"
                :imageURL="$user().user_image"
              />
              <div class="text-base text-gray-700">Write an update...</div>
            </div>
          </a>
        </router-link>
        <template v-for="d in activity" :key="d.key">
          <div class="px-3">
            <div class="border-t"></div>
          </div>
          <router-link
            :to="{
              name: 'ProjectDetailUpdateView',
              params: { updateId: d.name },
            }"
            class="block p-3 rounded-xl"
            :class="isActive(d) ? 'bg-gray-100' : 'hover:bg-gray-50'"
          >
            <div class="flex items-center space-x-4">
              <div>
                <UserInfo :email="d.user" :key="d.key">
                  <template v-slot="{ user }">
                    <Avatar
                      :label="user.full_name"
                      :imageURL="user.user_image"
                    />
                  </template>
                </UserInfo>
              </div>
              <UserInfo :email="d.user" :key="d.key">
                <template v-slot="{ user }">
                  <div class="flex items-center w-full">
                    <div>
                      <span class="text-base text-gray-900">
                        {{ user.full_name }}
                      </span>
                      &middot;
                      <span class="text-base text-gray-600">
                        {{ $dayjs(d.timestamp).fromNow() }}
                      </span>
                    </div>
                    <Badge
                      class="ml-auto"
                      :color="{
                        green: d.status === 'On Track',
                        red: d.status === 'Off Track',
                        yellow: d.status === 'At Risk',
                      }"
                    >
                      {{ d.status }}
                    </Badge>
                  </div>
                </template>
              </UserInfo>
            </div>
            <div class="mt-3 text-xl font-semibold">
              {{ d.title }}
            </div>
            <div
              class="mt-3 overflow-hidden prose-sm prose max-h-12"
              v-html="d.content"
            />
          </router-link>
        </template>
        <div class="h-10"></div>
      </div>
    </div>
    <div
      v-if="
        ['ProjectDetailUpdateNew', 'ProjectDetailUpdateView'].includes(
          $route.name
        )
      "
      class="w-7/12 overflow-auto border-l"
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
        onSuccess() {
          this.openLatestUpdate()
        },
      }
    },
  },
  mounted() {
    this.openLatestUpdate()
  },
  methods: {
    openLatestUpdate() {
      let latest = (this.$resources.updates.data || [])[0]
      if (latest) {
        // open latest update
        this.$router.replace({
          name: 'ProjectDetailUpdateView',
          params: { updateId: latest.name },
        })
      }
    },
    isActive(update) {
      return (
        this.$route.name === 'ProjectDetailUpdateView' &&
        this.$route.params.updateId === update.name
      )
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
            content: update.content,
            key: update.name,
          }
        }),
        // {
        //   type: 'create',
        //   icon: 'plus',
        //   user: this.project.doc.owner,
        //   timestamp: this.project.doc.creation,
        //   key: 'create',
        // },
      ]
    },
  },
}
</script>
