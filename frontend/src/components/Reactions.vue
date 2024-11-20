<template>
  <ReactionsUI
    :reactionsCount="reactionsCount"
    :toggleReaction="toggleReaction"
    :toolTipText="toolTipText"
    :standardEmojis="standardEmojis"
    :isLoading="$resources.batch.loading"
  />
  <div class="mt-2 space-y-2" v-if="batchRequestErrors.length">
    <ErrorMessage v-for="error in batchRequestErrors" :message="error" />
  </div>
</template>
<script setup>
import { useScreenSize } from '@/utils/composables'
import { defineAsyncComponent, computed } from 'vue'

const screenSize = useScreenSize()
const ReactionsMobile = defineAsyncComponent(() => import('./ReactionsMobile.vue'))
const ReactionsDesktop = defineAsyncComponent(() => import('./ReactionsDesktop.vue'))
const ReactionsUI = computed(() => {
  if (screenSize.width < 640) {
    return ReactionsMobile
  } else {
    return ReactionsDesktop
  }
})
</script>
<script>
export default {
  name: 'Reactions',
  props: ['reactions', 'doctype', 'name', 'readOnlyMode'],
  emits: ['update:reactions'],
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
            if (response?.message?.reactions) {
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
        (r) => r.user === this.$user().name && r.emoji === emoji,
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
        .filter((d) => d?.exception)
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
