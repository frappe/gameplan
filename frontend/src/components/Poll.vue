<template>
  <div class="relative">
    <div
      v-if="highlight"
      class="absolute inset-0 translate-y- z-[5] rounded border-2 -mx-4 -mb-4 mt-11 pointer-events-none"
    />
    <div
      class="pb-2 flex items-center text-base text-ink-gray-8 pt-15 top-0 sticky bg-surface-base"
    >
      <UserProfileLink class="mr-3" :user="owner.name">
        <UserAvatarWithHover :user="owner.name" size="lg" />
      </UserProfileLink>
      <div class="md:flex md:items-center">
        <UserProfileLink class="font-medium hover:text-ink-blue-8" :user="owner.name">
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
    <div class="my-4 space-y-2">
      <Checkbox
        v-if="supportsMultipleAnswers"
        v-for="option in _poll.options"
        :key="option.idx"
        v-model="selectedAnswers[option.title]"
        :aria-label="option.title"
        :disabled="isStopped || readOnlyMode || actionLoading"
        @update:model-value="toggleAnswer(option, $event)"
      >
        <template #label>
          <span class="flex items-baseline">
            <span class="text-base text-ink-gray-8">{{ option.title }}</span>
            <span class="ml-1 text-base text-ink-gray-5" v-if="participated">
              ({{ option.percentage }}%)
            </span>
          </span>
        </template>
      </Checkbox>
      <button
        v-else
        class="group flex items-center text-ink-gray-8"
        v-for="option in _poll.options"
        :key="option.idx"
        @click="submitVote(option)"
        :disabled="voteIsFinal || isStopped || readOnlyMode || actionLoading"
      >
        <div
          class="mr-2 h-4 w-4 rounded-full border-2 text-sm"
          :class="
            isVotedByUser(option.title)
              ? 'border-outline-gray-9 bg-surface-gray-10'
              : voteIsFinal || isStopped || readOnlyMode
                ? 'border-outline-gray-2'
                : 'border-outline-gray-2 group-hover:border-outline-gray-3'
          "
        >
          <span v-if="isVotedByUser(option.title)" class="lucide-check h-3 w-3 text-ink-base" />
        </div>
        <div class="flex items-baseline">
          <div class="text-base text-ink-gray-8">{{ option.title }}</div>
          <div class="ml-1 text-base text-ink-gray-5" v-if="participated">
            ({{ option.percentage }}%)
          </div>
        </div>
      </button>
    </div>
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
import { Checkbox, Dropdown, Dialog, Tooltip, dayjsLocal, dialog, useDoc } from 'frappe-ui'
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
const supportsMultipleAnswers = computed(
  () => Boolean(_poll.value.multiple_answers) && !Boolean(_poll.value.anonymous),
)
// An anonymous poll records that you voted but not what you chose, so there is no answer
// to replace or retract: that vote is final. Every other poll lets you change your mind.
const voteIsFinal = computed(() => Boolean(_poll.value.anonymous) && participated.value)
const actionLoading = computed(
  () =>
    pollResource.submitVote.loading ||
    pollResource.retractVote.loading ||
    pollResource.stopPoll.loading,
)
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
        onConfirm: () => pollResource.delete.submit(),
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

async function submitVote(option: GPPollOption) {
  // Already this voter's answer — the server would no-op, so skip the round trip.
  if (isVotedByUser(option.title)) return
  if (_poll.value.anonymous) {
    dialog.confirm({
      title: 'Anonymous poll',
      message: `This poll is anonymous. Once you vote, you cannot retract your vote. You are voting for "${option.title}". Continue?`,
      confirmLabel: `Vote for "${option.title}"`,
      onConfirm: () => castVote(option.title),
    })
    return
  }
  await castVote(option.title)
}

async function toggleAnswer(option: GPPollOption, checked: boolean) {
  if (checked) {
    await castVote(option.title)
  } else {
    await retractVote(option.title)
  }
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
  return _poll.value.votes.some((vote) => vote.option === option && vote.user === sessionUser.name)
}

function copyLink() {
  const location = window.location
  const url = `${location.origin}${location.pathname}?poll=${props.poll.name}`
  copyToClipboard(url)
}
</script>
