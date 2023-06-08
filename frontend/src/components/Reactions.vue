<template>
  <div class="flex select-none items-stretch space-x-1.5">
    <Popover class="h-full">
      <template #target="{ togglePopover, isOpen }">
        <button
          aria-label="Add a reaction"
          :disabled="$resources.batch.loading"
          @click="togglePopover()"
          class="flex h-full items-center justify-center rounded-full px-2 py-1 transition bg-gray-100 text-gray-700 hover:bg-gray-200"
          :class="{ 'bg-gray-200': isOpen }"
        >
          <ReactionFaceIcon />
        </button>
      </template>
      <template #body-main="{ togglePopover }">
        <div class="mt-1 inline-flex p-1">
          <div class="grid grid-cols-10 items-center space-x-0.5">
            <button
              class="h-6 w-6 rounded hover:bg-gray-50"
              v-for="emoji in standardEmojis"
              :key="emoji"
              @click="
                () => {
                  toggleReaction(emoji)
                  togglePopover()
                }
              "
              :disabled="$resources.batch.loading"
            >
              {{ emoji }}
            </button>
          </div>
        </div>
      </template>
    </Popover>
    <Transition
      enterActiveClass="transition duration-300 ease-out"
      enterFromClass="scale-75"
      enterToClass="scale-100"
      leaveActiveClass="transition duration-100 ease-in absolute"
      leaveFromClass="scale-100 opacity-100"
      leaveToClass="scale-90 opacity-0"
    >
      <TransitionGroup
        v-if="reactions.length"
        tag="div"
        class="flex items-stretch space-x-1.5"
        moveClass="transition duration-100 ease-in"
        enterActiveClass="transition duration-300 ease-out"
        enterFromClass="scale-75"
        enterToClass="scale-100"
        leaveActiveClass="transition duration-100 ease-in"
        leaveFromClass="scale-100 opacity-100"
        leaveToClass="scale-90 opacity-0"
      >
        <Tooltip v-for="(reactions, emoji) in reactionsCount" :key="emoji">
          <button
            class="flex items-center justify-center rounded-full px-2 py-1 text-sm transition"
            :class="[
              reactions.userReacted
                ? 'bg-amber-100 hover:bg-amber-200 text-amber-700'
                : 'bg-gray-100 hover:bg-gray-200 text-gray-700',
            ]"
            @click="toggleReaction(emoji)"
          >
            {{ emoji }} {{ reactions.count }}
          </button>
          <template #body>
            <div
              class="max-w-[30ch] rounded-lg border border-gray-100 bg-gray-800 px-2 py-1 text-center text-xs text-white shadow-xl"
            >
              {{ toolTipText(reactions) }}
            </div>
          </template>
        </Tooltip>
      </TransitionGroup>
    </Transition>
  </div>
  <div class="mt-2 space-y-2" v-if="batchRequestErrors.length">
    <ErrorMessage v-for="error in batchRequestErrors" :message="error" />
  </div>
</template>
<script>
import { Popover, Tooltip, ErrorMessage } from 'frappe-ui'
import ReactionFaceIcon from './ReactionFaceIcon.vue'
import LoadingIndicator from 'frappe-ui/src/components/LoadingIndicator.vue'

export default {
  name: 'Reactions',
  props: ['reactions', 'doctype', 'name', 'readOnlyMode'],
  emits: ['update:reactions'],
  components: {
    ReactionFaceIcon,
    Popover,
    Tooltip,
    ErrorMessage,
    LoadingIndicator,
  },
  resources: {
    batch() {
      return {
        url: 'gameplan.extends.client.batch',
        makeParams() {
          return { requests: this.changes }
        },
        onSuccess(responses) {
          this.changes = []
          for (let response of responses) {
            if (response.message?.reactions) {
              let reactions = response.message.reactions.map((d) => ({
                name: d.name,
                emoji: d.emoji,
                user: d.user,
              }))
              this.$emit('update:reactions', reactions)
            }
          }
        },
        debounce: 1000,
      }
    },
  },
  methods: {
    toggleReaction(emoji) {
      if (this.readOnlyMode) return
      let existingReaction = this.reactions.find(
        (r) => r.user === this.$user().name && r.emoji === emoji
      )
      if (existingReaction) {
        this.removeReaction(existingReaction)
      } else {
        this.addReaction(emoji)
      }
    },
    addReaction(emoji) {
      const user = this.$user().name
      let reactions = [
        ...this.reactions,
        {
          emoji,
          user,
          name: `new-emoji-${this.reactions.length}`,
        },
      ]
      this.$emit('update:reactions', reactions)
      this.changes = [
        ...(this.changes || []),
        {
          cmd: 'frappe.client.insert',
          doc: {
            doctype: 'GP Reaction',
            parentfield: 'reactions',
            parenttype: this.doctype,
            parent: this.name,
            user,
            emoji,
          },
        },
      ]
      this.$resources.batch.submit()
    },
    removeReaction(reaction) {
      // update local
      let reactions = this.reactions.filter((r) => r !== reaction)
      this.$emit('update:reactions', reactions)

      // update server
      this.changes = [
        ...(this.changes || []),
        {
          cmd: 'frappe.client.delete',
          doctype: 'GP Reaction',
          name: reaction.name,
        },
      ]
      this.$resources.batch.submit()
    },
    toolTipText(reactions) {
      return reactions.users
        .map((user) => {
          if (user) {
            return this.$user(user).full_name.trim()
          }
          return ''
        })
        .join(', ')
    },
  },
  computed: {
    reactionsCount() {
      let out = {}
      for (let reaction of this.reactions) {
        if (!out[reaction.emoji]) {
          out[reaction.emoji] = { count: 0, users: [], userReacted: false }
        }
        out[reaction.emoji].count++
        out[reaction.emoji].users.push(reaction.user)
        if (reaction.user === this.$user().name) {
          out[reaction.emoji].userReacted = true
        }
      }
      return out
    },
    batchRequestErrors() {
      if (!this.$resources.batch.data) {
        return []
      }
      return this.$resources.batch.data
        .filter((d) => d.exception)
        .map((d) => {
          let _server_messages = d._server_messages
          try {
            _server_messages = JSON.parse(_server_messages)
            return _server_messages.map((m) => JSON.parse(m).message)
          } catch (e) {}
          return d.exception
        })
        .flat()
    },
    standardEmojis() {
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
        '😂',
        '🍿',
        '🙈',
        '🌚',
        '🚀',
      ]
    },
  },
}
</script>
