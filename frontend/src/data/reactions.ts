import { computed, reactive, shallowRef, unref, toValue, watch } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { toast, useCall } from 'frappe-ui'
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

const BATCH_DELAY = 1000

export function useReactions(options: UseReactionsOptions) {
  const currentUser = computed(() => unref(session.user) || '')

  const doctype = computed(() => toValue(options.doctype))
  const name = computed(() => toValue(options.name))
  const readOnlyMode = computed(() => toValue(options.readOnlyMode ?? false))

  // What the reactions look like on the server. Follows the caller's data, and also
  // takes each response directly, so a confirmed tap stays visible even when the
  // caller's copy is not reactive.
  const serverReactions = shallowRef<Reaction[]>([])
  watch(
    () => toValue(options.reactions),
    (reactions) => {
      serverReactions.value = reactions ?? []
    },
    { immediate: true },
  )

  // Taps the server has not confirmed yet, as emoji -> whether the user wants to
  // have reacted with it. `queued` waits for the next batch; `sending` is the batch
  // in flight. Only one batch is in flight at a time, because a second submit on
  // the same call would abort the first.
  const queued = reactive(new Map<string, boolean>())
  const sending = reactive(new Map<string, boolean>())

  const hasReacted = (emoji: string) =>
    serverReactions.value.some(
      (reaction) => reaction.user === currentUser.value && reaction.emoji === emoji,
    )
  // The user's reaction once the batch in flight lands.
  const settledState = (emoji: string) => sending.get(emoji) ?? hasReacted(emoji)
  const displayedState = (emoji: string) => queued.get(emoji) ?? settledState(emoji)

  const react = useCall<Reaction[], { operations: ReactionOperation[] }>({
    url: computed(() => `/api/v2/document/${doctype.value}/${name.value}/method/react`),
    method: 'POST',
    immediate: false,
    onSuccess(reactions) {
      if (Array.isArray(reactions)) {
        const confirmed = reactions.map((r) => ({ name: r.name, emoji: r.emoji, user: r.user }))
        serverReactions.value = confirmed
        options.onUpdate(confirmed)
      }
      settle()
    },
    onError() {
      // Dropping the batch is the rollback: those emojis fall back to server state.
      toast.error('Could not save your reaction')
      settle()
    },
  })

  let submitTimeout: number | null = null

  const send = () => {
    submitTimeout = null
    // A batch is in flight: settle() sends these once it lands.
    if (sending.size || !queued.size) return
    for (const [emoji, wanted] of queued) {
      sending.set(emoji, wanted)
    }
    queued.clear()
    const operations = [...sending].map(
      ([emoji, wanted]): ReactionOperation => ({ emoji, operation: wanted ? 'add' : 'remove' }),
    )
    react.submit({ operations })
  }

  const settle = () => {
    sending.clear()
    // Taps made while the batch was in flight go out now, unless more taps are
    // still being collected.
    if (!submitTimeout) send()
  }

  const scheduleSend = () => {
    if (submitTimeout) window.clearTimeout(submitTimeout)
    submitTimeout = queued.size ? window.setTimeout(send, BATCH_DELAY) : null
  }

  const toggleReaction = (emoji: string) => {
    if (readOnlyMode.value) return
    const wanted = !displayedState(emoji)
    // Toggling back before the batch goes out cancels the tap instead of sending it.
    if (wanted === settledState(emoji)) {
      queued.delete(emoji)
    } else {
      queued.set(emoji, wanted)
    }
    scheduleSend()
  }

  const reactionsCount = computed(() => {
    const me = currentUser.value
    const pending = new Map([...sending, ...queued])
    const reactions: Pick<Reaction, 'emoji' | 'user'>[] = serverReactions.value.filter(
      (reaction) => reaction.user !== me || pending.get(reaction.emoji) !== false,
    )
    for (const [emoji, wanted] of pending) {
      if (
        wanted &&
        !reactions.some((reaction) => reaction.user === me && reaction.emoji === emoji)
      ) {
        reactions.push({ emoji, user: me })
      }
    }

    const out: Record<string, ReactionCount> = {}
    for (let reaction of reactions) {
      if (!out[reaction.emoji]) {
        out[reaction.emoji] = { count: 0, users: [], userReacted: false }
      }
      out[reaction.emoji].count++
      out[reaction.emoji].users.push(reaction.user)
      if (reaction.user === me) {
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

  return {
    reactionsCount,
    toggleReaction,
    toolTipText,
    standardEmojis: currentQuickReactionEmojis,
  }
}
