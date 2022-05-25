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
            <div class="flex items-stretch mt-3 space-x-1.5">
              <Popover>
                <template #target="{ togglePopover }">
                  <button
                    @click="togglePopover()"
                    class="flex items-center justify-center h-full px-2 py-1 transition border border-gray-300 rounded-full hover:border-gray-400"
                  >
                    <ReactionFaceIcon />
                  </button>
                </template>
                <template #content="{ togglePopover }">
                  <div
                    class="inline-flex p-1 bg-white border border-gray-100 rounded-lg shadow-xl"
                  >
                    <div class="grid grid-cols-8 items-center space-x-0.5">
                      <button
                        class="w-6 h-6 rounded hover:bg-gray-50"
                        v-for="emoji in reactions"
                        :key="emoji"
                        @click="
                          () => {
                            toggleReaction(d, emoji)
                            togglePopover()
                          }
                        "
                        :disabled="
                          $resources.reactions.insert.loading ||
                          $resources.reactions.delete.loading
                        "
                      >
                        {{ emoji }}
                      </button>
                    </div>
                  </div>
                </template>
              </Popover>
              <Transition
                enterActiveClass="transition duration-500 ease-out"
                enterFromClass="scale-75"
                enterToClass="scale-100"
                leaveActiveClass="transition duration-100 ease-in absolute"
                leaveFromClass="scale-100 opacity-100"
                leaveToClass="scale-90 opacity-0"
              >
                <TransitionGroup
                  v-if="$resources.reactions.data?.[d.name]"
                  tag="div"
                  class="flex items-stretch space-x-1.5"
                  moveClass="transition duration-100 ease-in"
                  enterActiveClass="transition duration-500 ease-out"
                  enterFromClass="scale-75"
                  enterToClass="scale-100"
                  leaveActiveClass="transition duration-100 ease-in absolute"
                  leaveFromClass="scale-100 opacity-100"
                  leaveToClass="scale-90 opacity-0"
                >
                  <button
                    v-for="(reactions, reaction) in $resources.reactions.data[
                      d.name
                    ]"
                    :key="reaction"
                    class="flex items-center justify-center px-2 py-1 text-sm transition border rounded-full"
                    :class="[
                      reactions.userReacted
                        ? 'bg-blue-100 border-blue-200 hover:border-blue-300'
                        : 'border-gray-300 hover:border-gray-400',
                    ]"
                    @click="toggleReaction(d, reaction)"
                  >
                    {{ reaction }} {{ reactions.length }}
                  </button>
                </TransitionGroup>
              </Transition>
            </div>
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
import { Avatar, TextEditor, Popover } from 'frappe-ui'
import Link from '@/components/Link.vue'
import ReactionFaceIcon from '@/components/ReactionFaceIcon.vue'

export default {
  name: 'ProjectDetailUpdate',
  props: ['project'],
  components: { TextEditor, Avatar, Link, ReactionFaceIcon, Popover },
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
    reactions() {
      if (!this.$resources.updates.data) {
        return
      }
      return {
        type: 'list',
        cache: ['Reactions', this.project.doc.name],
        doctype: 'Team Reaction',
        fields: ['*'],
        filters: {
          reference_doctype: 'Team Project Status Update',
          reference_name: [
            'in',
            this.$resources.updates.data.map((d) => d.name),
          ],
        },
        order_by: 'creation asc',
        transform(data) {
          let reactions = {}
          for (let reaction of data) {
            if (!reactions[reaction.reference_name]) {
              reactions[reaction.reference_name] = {}
            }
            if (reactions[reaction.reference_name][reaction.emoji] == null) {
              reactions[reaction.reference_name][reaction.emoji] = []
            }
            reactions[reaction.reference_name][reaction.emoji].push(reaction)
            if (reaction.owner === this.$user().name) {
              reactions[reaction.reference_name][
                reaction.emoji
              ].userReacted = true
            }
          }
          return reactions
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
    toggleReaction(update, emoji) {
      let reactions =
        this.$resources.reactions.data?.[update.name]?.[emoji] || []
      let existingReaction = reactions.find(
        (r) => r.owner === this.$user().name && r.emoji === emoji
      )
      if (existingReaction) {
        this.removeReaction(update, existingReaction)
      } else {
        this.addReaction(update, emoji)
      }
    },
    addReaction(update, emoji) {
      this.$resources.reactions.insert.submit({
        reference_doctype: 'Team Project Status Update',
        reference_name: update.name,
        emoji: emoji,
      })
    },
    removeReaction(update, reaction) {
      // update local
      this.$resources.reactions.data[update.name][reaction.emoji].splice(
        this.$resources.reactions.data[update.name][reaction.emoji].indexOf(
          reaction
        ),
        1
      )
      // update server
      this.$resources.reactions.delete.submit(reaction.name)
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
    reactions() {
      return [
        '👍',
        '👎',
        '💖',
        '🔥',
        '👏🏻',
        '🤔',
        '😱',
        '🤯',
        '😡',
        '⚡️',
        '🥳',
        '🎉',
        '💩',
        '🤩',
        '😢',
        '😍',
      ]
    },
  },
}
</script>
