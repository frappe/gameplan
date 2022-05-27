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
        <template v-for="d in $resources.updates.data" :key="d.name">
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
                <UserInfo :email="d.owner">
                  <template v-slot="{ user }">
                    <Avatar
                      :label="user.full_name"
                      :imageURL="user.user_image"
                    />
                  </template>
                </UserInfo>
              </div>
              <UserInfo :email="d.owner">
                <template v-slot="{ user }">
                  <div class="flex items-center w-full">
                    <div>
                      <span class="text-base text-gray-900">
                        {{ user.full_name }}
                      </span>
                      &middot;
                      <span class="text-base text-gray-600">
                        {{ $dayjs(d.creation).fromNow() }}
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

            <Reactions
              v-model:reactions="d.reactions"
              doctype="Team Project Status Update"
              :name="d.name"
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
import Reactions from '@/components/Reactions.vue'

export default {
  name: 'ProjectDetailUpdate',
  props: ['project'],
  components: {
    TextEditor,
    Avatar,
    Link,
    Reactions,
  },
  resources: {
    updates() {
      return {
        type: 'list',
        cache: ['Project Updates', this.project.doc.name],
        doctype: 'Team Project Status Update',
        filters: {
          project: this.project.doc.name,
        },
        fields: [
          'name',
          'owner',
          'creation',
          'modified',
          'title',
          'status',
          'content',
          'reactions.name as reaction_name',
          'reactions.emoji as reaction_emoji',
          'reactions.owner as reaction_owner',
        ],
        order_by: 'creation desc',
        transform(data) {
          let updates = {}
          for (let d of data) {
            if (!updates[d.name]) {
              updates[d.name] = d
              updates[d.name].reactions = []
            }
            if (d.reaction_emoji) {
              updates[d.name].reactions.push({
                name: d.reaction_name,
                emoji: d.reaction_emoji,
                owner: d.reaction_owner,
              })
            }
          }
          return Object.values(updates)
        },
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
}
</script>
