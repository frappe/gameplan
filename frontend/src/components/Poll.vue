<template>
  <div class="relative">
    <div
      v-if="highlight"
      class="absolute inset-0 translate-y- z-[5] rounded border-2 -mx-4 -mb-4 mt-11 pointer-events-none"
    />
    <!-- Mirrors the comment header (Comment.vue). Two parts matter and both were missing:
         `z-[1]`, or the option rows (positioned so the result bar can fill behind them)
         paint over this header; and `sm:pt-14`, which pads the pinned header out to the
         app header's height so scrolled-up content is masked rather than showing through
         the strip above it. The previous `pt-15` was not a real utility, so it did nothing. -->
    <div
      class="sticky -top-px z-[1] -mx-2 flex items-center bg-surface-base px-2 pb-2 pt-2 text-base text-ink-gray-8 sm:top-0 sm:pt-14"
    >
      <UserProfileLink class="mr-3" :user="owner.name">
        <UserAvatarWithHover :user="owner.name" size="lg" />
      </UserProfileLink>
      <div class="md:flex md:items-center">
        <UserProfileLink class="font-medium hover:text-ink-gray-9" :user="owner.name">
          {{ owner.full_name }}
          <span class="hidden md:inline">&nbsp;&middot;&nbsp;</span>
        </UserProfileLink>
        <div>
          <Tooltip :text="dayjsLocal(_poll.creation).format('D MMM YYYY [at] h:mm A')">
            <time class="text-ink-gray-5" :datetime="_poll.creation">
              {{ dayjsLocal(_poll.creation).fromNow() }}
            </time>
          </Tooltip>
        </div>
      </div>
      <div class="ml-auto flex items-center space-x-2">
        <Button
          v-if="!isStopped && !readOnlyMode && canDeletePoll"
          variant="ghost"
          icon-left="lucide-minus-circle"
          @click="stopPoll"
        >
          Stop Poll
        </Button>
        <Tooltip v-else text="This is a poll">
          <span class="lucide-bar-chart-2 h-4 w-4 -rotate-90" />
        </Tooltip>
        <Dropdown
          align="end"
          :button="{
            icon: 'lucide-more-horizontal',
            variant: 'ghost',
            label: 'Poll Options',
          }"
          :options="dropdownOptions"
        />
      </div>
    </div>
    <div class="text-base-semibold text-ink-gray-8">{{ _poll.title }}</div>
    <div class="mt-1 text-sm text-ink-gray-5">
      <span v-if="_poll.multiple_answers"> Multiple answers &middot; </span>
      <span v-if="_poll.anonymous"> Anonymous &middot; </span>
      <span>{{ totalLabel }}</span>
      <span v-if="_poll.stopped_at"> &middot; {{ stopTime }} </span>
    </div>
    <!-- Twitter-style: once results are visible the row itself becomes the bar, with the
         share filled in behind the label. Capped to a readable measure — a bar spanning
         the full thread width reads as a progress indicator, not a share of the vote. -->
    <div class="my-4 max-w-sm space-y-1.5">
      <div
        v-for="option in _poll.options"
        :key="option.idx"
        class="relative -mx-2 overflow-hidden rounded"
        :data-poll-option="option.title"
      >
        <div
          v-if="showResults"
          class="absolute inset-y-0 left-0 rounded transition-[width] duration-500 ease-out"
          :class="isVotedByUser(option.title) ? 'bg-surface-gray-4' : 'bg-surface-gray-2'"
          :style="{ width: `${option.percentage || 0}%` }"
          aria-hidden="true"
        />
        <div class="relative flex h-7 items-center justify-between gap-3 px-2">
          <!-- Checkbox's own label is top-aligned to the first line of a wrapping label,
               which leaves the box high against a single-line one. Pair it with our own
               <label for> instead so the row can centre them. -->
          <div class="flex min-w-0 items-center gap-2">
            <Checkbox
              size="md"
              :id="optionId(option)"
              :model-value="selectedAnswers[option.title] ?? false"
              :disabled="isOptionDisabled"
              :aria-label="option.title"
              @update:model-value="toggleOption(option, Boolean($event))"
            />
            <label
              :for="optionId(option)"
              class="truncate text-base leading-6 text-ink-gray-8 select-none"
              :class="[
                isOptionDisabled ? 'cursor-default' : 'cursor-pointer',
                { 'font-medium': isVotedByUser(option.title) },
              ]"
            >
              {{ option.title }}
            </label>
          </div>
          <span v-if="showResults" class="shrink-0 text-sm leading-6 tabular-nums text-ink-gray-7">
            {{ formatPercentage(option.percentage) }}%
          </span>
        </div>
      </div>
    </div>
    <!-- The tick moves optimistically, so a rejected vote has to say why it snapped back. -->
    <ErrorMessage class="-mt-2 mb-3" :message="voteError" />
    <div class="mt-3">
      <Reactions
        doctype="GP Poll"
        :name="poll.name"
        v-model:reactions="_poll.reactions"
        :read-only-mode="readOnlyMode"
      />
    </div>
    <Dialog title="Poll results" v-model:open="showDialog">
      <h2 class="text-xl-medium text-ink-gray-8">{{ _poll.title }}</h2>
      <div v-if="!pollResults" class="text-base text-ink-gray-6 mt-2">No votes yet</div>
      <div class="mt-6 space-y-6">
        <div v-for="option in pollResults" :key="option.title">
          <div class="flex items-center mb-2">
            <h3 class="text-base-medium text-ink-gray-8">{{ option.title }}</h3>
            <div class="mx-2 flex-1 border-b border-outline-gray-2"></div>
            <div class="text-base text-ink-gray-5">
              {{ option.votes }} {{ option.votes === 1 ? 'vote' : 'votes' }}
            </div>
            <div class="ml-1 text-base text-ink-gray-5">({{ option.percentage }}%)</div>
          </div>
          <div class="space-y-2">
            <div class="flex" v-for="voter in option.voters" :key="voter.name">
              <UserProfileLink :user="voter.name">
                <div class="flex items-center space-x-2">
                  <UserAvatar size="sm" :user="voter.name" />
                  <span class="text-base text-ink-gray-8">{{ voter.full_name }}</span>
                </div>
              </UserProfileLink>
            </div>
          </div>
        </div>
      </div>
    </Dialog>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import {
  Checkbox,
  Dropdown,
  Dialog,
  ErrorMessage,
  Tooltip,
  dayjsLocal,
  dialog,
  useDoc,
} from 'frappe-ui'
import UserAvatar from './UserAvatar.vue'
import UserAvatarWithHover from './UserAvatarWithHover.vue'
import UserProfileLink from './UserProfileLink.vue'
import { copyToClipboard } from '@/utils'
import Reactions from './Reactions.vue'
import { useUser, useSessionUser } from '@/data/users'
import { canDeleteContent } from '@/utils/permissions'
import type { GPPoll, GPPollOption } from '@/types/doctypes'
import type { Space } from '@/data/spaces'
import { subscribeToDoc, useSocket } from '@/socket'

interface Props {
  poll: GPPoll
  highlight?: boolean
  // Space the poll's discussion belongs to, for community-admin moderation.
  space?: Space | null
  // Archived space or site-wide read-only: the poll is visible but inert.
  readOnlyMode?: boolean
}

interface PollMethods {
  submitVote(params: { option: string }): void
  retractVote(params: { option?: string }): void
  stopPoll(): void
}

const props = withDefaults(defineProps<Props>(), {
  highlight: false,
  space: null,
  readOnlyMode: false,
})

const showDialog = ref(false)
const sessionUser = useSessionUser()
const socket = useSocket()
const selectedAnswers = reactive<Record<string, boolean>>({})
// An anonymous vote records the voter but not their choice, so the server can never tell
// us which option to tick. Remember it for this mount so the poll doesn't look untouched
// the instant after you vote; it is gone on the next load, which is the point of anonymity.
const anonymousChoice = ref<string | null>(null)
let voteQueue: Promise<void> = Promise.resolve()
let clickCount = 0

const pollResource = useDoc<GPPoll, PollMethods>({
  doctype: 'GP Poll',
  name: () => String(props.poll.name),
  methods: {
    submitVote: 'submit_vote',
    stopPoll: 'stop_poll',
    retractVote: 'retract_vote',
  },
})

const _poll = computed(() => pollResource.doc || props.poll)
const owner = computed(() => useUser(_poll.value.owner))
const participated = computed(() =>
  _poll.value.votes.some((vote) => vote.user === sessionUser.name),
)
const voteError = computed(
  () => pollResource.submitVote.error?.message || pollResource.retractVote.error?.message || null,
)
// An anonymous poll records that you voted but not what you chose, so there is no answer
// to replace or retract: that vote is final. Every other poll lets you change your mind.
const voteIsFinal = computed(() => Boolean(_poll.value.anonymous) && participated.value)
// Tallies stay hidden until the viewer has skin in the game, so early voters can't
// be nudged by the running result. A stopped poll has nothing left to influence.
const showResults = computed(() => participated.value || isStopped.value)
// Deliberately not disabled while a vote is in flight: the tick updates optimistically,
// so greying every option for the round trip just makes a click flicker. Overlapping
// clicks are handled by queueing them instead (see queueVote).
const isOptionDisabled = computed(() => isStopped.value || props.readOnlyMode || voteIsFinal.value)
const canDeletePoll = computed(() => canDeleteContent(_poll.value, props.space, sessionUser))
const isStopped = computed(
  () => Boolean(_poll.value.stopped_at) && dayjsLocal().isAfter(_poll.value.stopped_at),
)
const totalLabel = computed(() => {
  const total = _poll.value.total_votes || 0
  if (!_poll.value.multiple_answers) {
    return `${total} ${total === 1 ? 'vote' : 'votes'}`
  }

  const voters = new Set(_poll.value.votes.map((vote) => vote.user)).size
  return `${total} ${total === 1 ? 'answer' : 'answers'} from ${voters} ${
    voters === 1 ? 'person' : 'people'
  }`
})
const stopTime = computed(() => {
  const timestamp = _poll.value.stopped_at
  if (dayjsLocal().diff(timestamp, 'day') < 7) {
    return `Ended ${dayjsLocal(timestamp).fromNow()}`
  }
  if (dayjsLocal().diff(timestamp, 'year') < 1) {
    return `Ended at ${dayjsLocal(timestamp).format('D MMM, h:mm A')}`
  }
  return `Ended at ${dayjsLocal(timestamp).format('D MMM YYYY, h:mm A')}`
})
const pollResults = computed(() => {
  if (!pollResource.doc || _poll.value.anonymous) return null
  return _poll.value.options.map((option) => ({
    title: option.title,
    votes: option.votes,
    percentage: option.percentage,
    voters: _poll.value.votes
      .filter((vote) => vote.option === option.title)
      .map((vote) => useUser(vote.user)),
  }))
})
const dropdownOptions = computed(() => [
  {
    label: 'Show results',
    icon: 'lucide-bar-chart-2',
    condition: () => !_poll.value.anonymous,
    onClick: () => {
      showDialog.value = true
    },
  },
  {
    label: 'Retract vote',
    icon: 'lucide-corner-up-left',
    condition: () =>
      !props.readOnlyMode &&
      !_poll.value.anonymous &&
      !_poll.value.multiple_answers &&
      participated.value &&
      (!_poll.value.stopped_at || dayjsLocal().isBefore(_poll.value.stopped_at)),
    onClick: () => {
      dialog.danger({
        title: 'Retract vote',
        message: 'Are you sure you want to retract your vote?',
        confirmLabel: 'Retract vote',
        onConfirm: () => retractVote(),
      })
    },
  },
  {
    label: 'Copy link',
    icon: 'lucide-link',
    onClick: copyLink,
  },
  {
    label: 'Delete',
    icon: 'lucide-trash',
    condition: () => !props.readOnlyMode && canDeletePoll.value,
    onClick: () => {
      dialog.danger({
        title: 'Delete poll',
        message: 'Are you sure you want to delete this poll?',
        onConfirm: async () => {
          await pollResource.delete.submit()
        },
      })
    },
  },
])

watch(
  () => _poll.value.votes.map((vote) => `${vote.user}:${vote.option}`).join('|'),
  syncSelectedAnswers,
  { immediate: true },
)

let unsubscribeFromPoll: (() => void) | null = null
onMounted(() => {
  unsubscribeFromPoll = subscribeToDoc('GP Poll', String(props.poll.name))
  socket?.on('doc_update', handlePollUpdate)
})
onUnmounted(() => {
  socket?.off('doc_update', handlePollUpdate)
  unsubscribeFromPoll?.()
})

async function handlePollUpdate(data: { doctype?: string; name?: string | number }) {
  if (data.doctype === 'GP Poll' && String(data.name) === String(props.poll.name)) {
    await reloadPoll()
  }
}

/**
 * Every poll type votes through the same checkbox. What differs is what a tick means:
 * on a multiple-answer poll each option stands alone, on a single-answer poll ticking a
 * new option replaces the previous answer, and an anonymous vote is confirmed once and
 * never changed.
 */
async function toggleOption(option: GPPollOption, checked: boolean) {
  // Drive the tick from our own state rather than the checkbox's: a cancelled dialog or a
  // rejected request has to snap it back, and syncSelectedAnswers is the one thing that
  // knows what the server actually recorded.
  if (checked && !_poll.value.multiple_answers) {
    // One answer per voter, so the previous tick has to clear the moment the new one
    // lands — submit_vote drops it server-side, but not until the round trip returns.
    for (const title of Object.keys(selectedAnswers)) selectedAnswers[title] = false
  }
  selectedAnswers[option.title] = checked
  const click = ++clickCount

  await queueVote(async () => {
    if (!checked) {
      await retractVote(_poll.value.multiple_answers ? option.title : undefined)
      return
    }

    if (_poll.value.anonymous) {
      await confirmAnonymousVote(option)
      return
    }

    // On a single-answer poll submit_vote replaces this voter's previous answer itself,
    // so one call covers changing your mind as well as casting a first vote.
    await castVote(option.title)
  })

  // Only the newest click reconciles against the server. An earlier one settling late
  // would otherwise overwrite the tick the user has since moved, undoing it on screen.
  if (click === clickCount) syncSelectedAnswers()
}

/**
 * Run vote actions one at a time. The options stay enabled during a request so a click
 * registers instantly, which means a fast toggle can fire a second action before the
 * first returns — and `submit_vote` / `retract_vote` both read-modify-write the vote
 * table, so overlapping calls would race on stale rows.
 */
function queueVote(action: () => Promise<void>) {
  // Swallow at the tail so one failure neither stalls the queue nor stops the caller
  // reconciling — the failed call's `error` is what surfaces to the user.
  voteQueue = voteQueue.then(action, action).catch(() => {})
  return voteQueue
}

function confirmAnonymousVote(option: GPPollOption) {
  return new Promise<void>((resolve) => {
    dialog.confirm({
      title: 'Anonymous poll',
      message: `This poll is anonymous. Once you vote, you cannot retract your vote. You are voting for "${option.title}". Continue?`,
      confirmLabel: `Vote for "${option.title}"`,
      onConfirm: async () => {
        anonymousChoice.value = option.title
        await castVote(option.title)
        resolve()
      },
      onCancel: () => resolve(),
    })
  })
}

async function castVote(option: string) {
  await pollResource.submitVote.submit({ option })
  await reloadPoll()
}

async function retractVote(option?: string) {
  await pollResource.retractVote.submit({ option })
  await reloadPoll()
}

function stopPoll() {
  dialog.danger({
    title: 'Stop poll',
    message: 'After the poll is stopped, no one will be able to vote on it. Continue?',
    confirmLabel: 'Stop',
    onConfirm: async () => {
      await pollResource.stopPoll.submit()
      await reloadPoll()
    },
  })
}

async function reloadPoll() {
  await pollResource.reload()
  syncSelectedAnswers()
}

function syncSelectedAnswers() {
  const optionTitles = new Set(_poll.value.options.map((option) => option.title))
  for (const title of Object.keys(selectedAnswers)) {
    if (!optionTitles.has(title)) delete selectedAnswers[title]
  }
  for (const title of optionTitles) {
    selectedAnswers[title] = isVotedByUser(title)
  }
}

function isVotedByUser(option: string) {
  if (_poll.value.anonymous) return anonymousChoice.value === option
  return _poll.value.votes.some((vote) => vote.option === option && vote.user === sessionUser.name)
}

function formatPercentage(percentage?: number) {
  return Math.round(percentage || 0)
}

/** Ties each option's <label for> to its checkbox. Both parts are numeric, so it is a
 *  valid id even though option titles are free text. */
function optionId(option: GPPollOption) {
  return `poll-${props.poll.name}-option-${option.idx}`
}

function copyLink() {
  const location = window.location
  const url = `${location.origin}${location.pathname}?poll=${props.poll.name}`
  copyToClipboard(url)
}
</script>
