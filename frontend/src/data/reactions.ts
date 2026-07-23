import { computed, reactive, unref, toValue } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { useCall } from 'frappe-ui'
import { currentQuickReactionEmojis } from './reactionPreferences'
import { session } from './session'
import { useUser } from './users'

interface Reaction {
  name: string
  emoji: string
  user: string
}

interface ReactionCount {
  count: number
  users: string[]
  userReacted: boolean
}

interface PendingReaction {
  initial: boolean
  desired: boolean
}

type ReactionOperation = {
  emoji: string
  operation: 'add' | 'remove'
}

interface UseReactionsOptions {
  reactions: MaybeRefOrGetter<Reaction[]>
  doctype: MaybeRefOrGetter<string>
  name: MaybeRefOrGetter<string | number>
  readOnlyMode?: MaybeRefOrGetter<boolean>
  onUpdate: (reactions: Reaction[]) => void
}

export function useReactions(options: UseReactionsOptions) {
  const pendingReactions = reactive<Record<string, PendingReaction>>({})
  const currentUser = computed(() => unref(session.user) || '')

  const reactionsList = computed(() => toValue(options.reactions))
  const doctype = computed(() => toValue(options.doctype))
  const name = computed(() => toValue(options.name))
  const readOnlyMode = computed(() => toValue(options.readOnlyMode ?? false))

  const clearPending = () => {
    for (let key of Object.keys(pendingReactions)) {
      delete pendingReactions[key]
    }
  }

  const react = useCall<Reaction[], { operations: ReactionOperation[] }>({
    url: computed(() => `/api/v2/document/${doctype.value}/${name.value}/method/react`),
    method: 'POST',
    immediate: false,
    onSuccess(reactions) {
      if (Array.isArray(reactions)) {
        options.onUpdate(
          reactions.map((d) => ({
            name: d.name,
            emoji: d.emoji,
            user: d.user,
          })),
        )
      }
      clearPending()
    },
  })

  const buildPendingOperations = () =>
    Object.entries(pendingReactions).flatMap(([emoji, pending]) => {
      if (pending.initial === pending.desired) {
        return []
      }
      return [
        {
          emoji,
          operation: pending.desired ? 'add' : 'remove',
        } as ReactionOperation,
      ]
    })

  let submitTimeout: number | null = null

  const submitBatch = () => {
    cancelSubmit()

    submitTimeout = window.setTimeout(() => {
      const operations = buildPendingOperations()
      if (!operations.length) {
        return
      }
      react.submit({ operations })
    }, 1000)
  }

  const cancelSubmit = () => {
    if (submitTimeout) {
      window.clearTimeout(submitTimeout)
      submitTimeout = null
    }
  }

  const setPendingReaction = (emoji: string, initial: boolean, desired: boolean) => {
    if (initial === desired) {
      delete pendingReactions[emoji]
      if (!buildPendingOperations().length) {
        cancelSubmit()
      }
      return
    }
    pendingReactions[emoji] = { initial, desired }
  }

  const getUserReaction = (emoji: string) => {
    return reactionsList.value.find(
      (reaction) => reaction.user === currentUser.value && reaction.emoji === emoji,
    )
  }

  const addReaction = (emoji: string) => {
    const reactions = reactionsList.value
    const reaction = {
      emoji,
      user: currentUser.value,
      name: `new-emoji-${reactions.length}`,
    }
    options.onUpdate([...reactions, reaction])
  }

  const removeReaction = (reaction: Reaction) =>
    options.onUpdate(reactionsList.value.filter((item) => item !== reaction))

  const toggleReaction = (emoji: string) => {
    if (readOnlyMode.value) return
    const existingReaction = getUserReaction(emoji)
    const pending = pendingReactions[emoji]
    const currentState = pending ? pending.desired : !!existingReaction
    const initialState = pending ? pending.initial : !!existingReaction
    const desiredState = !currentState

    setPendingReaction(emoji, initialState, desiredState)

    if (desiredState) {
      if (!existingReaction) {
        addReaction(emoji)
      }
    } else if (existingReaction) {
      removeReaction(existingReaction)
    }

    submitBatch()
  }

  const reactionsCount = computed(() => {
    const out: Record<string, ReactionCount> = {}
    for (let reaction of reactionsList.value) {
      if (!out[reaction.emoji]) {
        out[reaction.emoji] = { count: 0, users: [], userReacted: false }
      }
      out[reaction.emoji].count++
      out[reaction.emoji].users.push(reaction.user)
      if (reaction.user === currentUser.value) {
        out[reaction.emoji].userReacted = true
      }
    }
    return out
  })

  const toolTipText = (reactions: ReactionCount) =>
    reactions.users
      .map((user) => (user ? useUser(user).full_name?.trim() : ''))
      .filter(Boolean)
      .join(', ')

  const batchRequestErrors = computed(() => {
    const error = react.error
    // A rapid second reaction makes useFetch abort the still-in-flight first
    // request (it calls abort() at the start of every execute). That surfaces a
    // DOMException "signal is aborted without reason". The cancelled operations
    // aren't lost — they stay in pendingReactions (cleared only on success) and
    // are resent in the next batch — so an abort isn't a real failure to report.
    if (!error || error.name === 'AbortError') {
      return []
    }
    const message = error.message || 'Unable to update reactions'
    return [message]
  })

  return {
    reactionsCount,
    toggleReaction,
    toolTipText,
    standardEmojis: currentQuickReactionEmojis,
    batchRequestErrors,
    isLoading: react.loading,
  }
}
