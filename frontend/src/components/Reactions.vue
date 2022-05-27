<template>
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
              v-for="emoji in standardEmojis"
              :key="emoji"
              @click="
                () => {
                  toggleReaction(emoji)
                  togglePopover()
                }
              "
              :disabled="
                $resources.addReaction.loading ||
                $resources.removeReaction.loading
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
        v-if="reactions.length"
        tag="div"
        class="flex items-stretch space-x-1.5"
        moveClass="transition duration-100 ease-in"
        enterActiveClass="transition duration-500 ease-out"
        enterFromClass="scale-75"
        enterToClass="scale-100"
        leaveActiveClass="transition duration-100 ease-in"
        leaveFromClass="scale-100 opacity-100"
        leaveToClass="scale-90 opacity-0"
      >
        <button
          v-for="(reactions, emoji) in reactionsCount"
          :key="emoji"
          class="flex items-center justify-center px-2 py-1 text-sm transition border rounded-full"
          :class="[
            reactions.userReacted
              ? 'bg-blue-100 border-blue-200 hover:border-blue-300'
              : 'border-gray-300 hover:border-gray-400',
          ]"
          @click="toggleReaction(emoji)"
        >
          {{ emoji }} {{ reactions.count }}
        </button>
      </TransitionGroup>
    </Transition>
  </div>
</template>
<script>
import { Popover } from 'frappe-ui'
import ReactionFaceIcon from './ReactionFaceIcon.vue'

export default {
  name: 'Reactions',
  props: ['reactions', 'doctype', 'name'],
  emits: ['update:reactions'],
  components: { ReactionFaceIcon, Popover },
  resources: {
    reactions() {
      return {
        type: 'list',
        cache: [this.doctype, this.project],
        doctype: 'Team Reaction',
        fields: ['*'],
        filters: {
          project: this.project,
          reference_doctype: this.doctype,
          reference_name: ['in', this.names],
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
    addReaction() {
      return {
        method: 'frappe.client.insert',
        makeParams(emoji) {
          return {
            doc: {
              doctype: 'Team Reaction',
              parentfield: 'reactions',
              parenttype: this.doctype,
              parent: this.name,
              emoji,
            },
          }
        },
        onSuccess(data) {
          let reactions = data.reactions.map((d) => ({
            name: d.name,
            emoji: d.emoji,
            owner: d.owner,
          }))
          this.$emit('update:reactions', reactions)
          this.$emit('change')
        },
      }
    },
    removeReaction() {
      return {
        method: 'frappe.client.delete',
        makeParams(name) {
          return {
            doctype: 'Team Reaction',
            name,
          }
        },
      }
    },
  },
  methods: {
    toggleReaction(emoji) {
      let existingReaction = this.reactions.find(
        (r) => r.owner === this.$user().name && r.emoji === emoji
      )
      if (existingReaction) {
        this.removeReaction(existingReaction)
      } else {
        this.addReaction(emoji)
      }
    },
    addReaction(emoji) {
      let reactions = [
        ...this.reactions,
        {
          emoji,
          owner: this.$user().name,
          name: `new-emoji-${this.reactions.length}`,
        },
      ]
      this.$emit('update:reactions', reactions)
      this.$resources.addReaction.submit(emoji)
    },
    removeReaction(reaction) {
      // update local
      let reactions = this.reactions.filter((r) => r !== reaction)
      this.$emit('update:reactions', reactions)

      // update server
      this.$resources.removeReaction.submit(reaction.name)
    },
  },
  computed: {
    reactionsCount() {
      let out = {}
      for (let reaction of this.reactions) {
        if (!out[reaction.emoji]) {
          out[reaction.emoji] = { count: 0, userReacted: false }
        }
        out[reaction.emoji].count++
        if (reaction.owner === this.$user().name) {
          out[reaction.emoji].userReacted = true
        }
      }
      return out
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
        '😍',
      ]
    },
  },
}
</script>
