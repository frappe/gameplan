<template>
  <div class="relative">
    <div
      v-if="highlight"
      class="absolute inset-0 translate-y- z-[5] rounded border-2 -mx-4 -mb-4 mt-11 pointer-events-none"
    />
    <div
      class="pb-2 flex items-center text-base text-ink-gray-8 pt-15 top-0 sticky bg-surface-white"
    >
      <UserInfo :email="_poll.owner" v-slot="{ user }">
        <UserProfileLink class="mr-3" :user="user.name">
          <UserAvatarWithHover :user="user.name" size="lg" />
        </UserProfileLink>
        <div class="md:flex md:items-center">
          <UserProfileLink class="font-medium hover:text-ink-blue-4" :user="user.name">
            {{ user.full_name }}
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
      </UserInfo>
      <div class="ml-auto flex items-center space-x-2">
        <Button v-if="!isStopped && $isSessionUser(_poll.owner)" variant="ghost" @click="stopPoll">
          <template #prefix><LucideMinusCircle class="w-4" /></template>
          Stop Poll
        </Button>
        <Tooltip v-else text="This is a poll">
          <LucideBarChart2 class="h-4 w-4 -rotate-90" />
        </Tooltip>
        <Dropdown
          placement="right"
          :button="{
            icon: 'more-horizontal',
            variant: 'ghost',
            label: 'Poll Options',
          }"
          :options="dropdownOptions"
        />
      </div>
    </div>
    <div class="text-base text-ink-gray-8 font-semibold">{{ _poll.title }}</div>
    <div class="mt-1 text-sm text-ink-gray-5">
      <span v-if="_poll.multiple_answers"> Multiple answers &middot; </span>
      <span v-if="_poll.anonymous"> Anonymous &middot; </span>
      <span> {{ _poll.total_votes }} {{ _poll.total_votes === 1 ? 'vote' : 'votes' }} </span>
      <span v-if="_poll.stopped_at"> &middot; {{ stopTime }} </span>
    </div>
    <div class="my-4 space-y-2">
      <button
        class="group flex items-center text-ink-gray-8"
        v-for="option in _poll.options"
        :key="option.idx"
        @click="submitVote(option)"
        :disabled="participated || isStopped || $resources.poll.submitVote.loading"
      >
        <div
          class="mr-2 h-4 w-4 rounded-full border-2 text-sm"
          :class="
            isVotedByUser(option.title)
              ? 'border-gray-900 bg-surface-gray-7'
              : participated || isStopped
                ? 'border-outline-gray-2'
                : 'border-outline-gray-2 group-hover:border-outline-gray-3'
          "
        >
          <LucideCheck
            v-if="isVotedByUser(option.title)"
            class="h-3 w-3 text-ink-white"
            :stroke-width="2.5"
          />
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
      <Reactions doctype="GP Poll" :name="poll.name" :reactions="_poll.reactions" />
    </div>
    <Dialog :options="{ title: 'Poll results' }" v-model="showDialog">
      <template #body-content>
        <h2 class="text-lg font-medium text-ink-gray-8">{{ _poll.title }}</h2>
        <div v-if="!pollResults" class="text-base text-ink-gray-6 mt-2">No votes yet</div>
        <div class="mt-6 space-y-6">
          <div v-for="option in pollResults" :key="option.title">
            <div class="flex items-center mb-2">
              <h3 class="text-base text-ink-gray-8 font-medium">{{ option.title }}</h3>
              <div class="mx-2 flex-1 border-b border-outline-gray-2"></div>
              <div class="text-base text-ink-gray-5">
                {{ option.votes }} {{ option.votes === 1 ? 'vote' : 'votes' }}
              </div>
              <div class="ml-1 text-base text-ink-gray-5">({{ option.percentage }}%)</div>
            </div>
            <div class="space-y-2">
              <div class="flex" v-for="user in option.voters" :key="user">
                <UserInfo :email="user" v-slot="{ user: _user }">
                  <UserProfileLink :user="_user.name">
                    <div class="flex items-center space-x-2">
                      <UserAvatar size="sm" :user="_user.name" />
                      <span class="text-base text-ink-gray-8">{{ _user.full_name }}</span>
                    </div>
                  </UserProfileLink>
                </UserInfo>
              </div>
            </div>
          </div>
        </div>
      </template>
    </Dialog>
  </div>
</template>
<script>
import { Dropdown, Dialog, Tooltip, dayjsLocal } from 'frappe-ui'
import UserAvatar from './UserAvatar.vue'
import UserProfileLink from './UserProfileLink.vue'
import { copyToClipboard } from '@/utils'
import Reactions from './Reactions.vue'

export default {
  name: 'Poll',
  props: {
    poll: {
      type: Object,
      required: true,
    },
    highlight: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['vote'],
  components: {
    UserProfileLink,
    UserAvatar,
    Dropdown,
    Tooltip,
    Reactions,
    Dialog,
  },
  data() {
    return {
      showDialog: false,
    }
  },
  setup() {
    return {
      dayjsLocal,
    }
  },
  resources: {
    poll() {
      return {
        type: 'document',
        doctype: 'GP Poll',
        name: this.poll.name,
        realtime: true,
        whitelistedMethods: {
          submitVote: 'submit_vote',
          stopPoll: 'stop_poll',
          retractVote: 'retract_vote',
        },
      }
    },
  },
  methods: {
    submitVote(option) {
      if (this._poll.anonymous) {
        this.$dialog({
          title: 'Anonymous poll',
          message: `This poll is anonymous. Once you vote, you cannot retract your vote. You are voting for "${option.title}". Continue?`,
          actions: [
            {
              label: `Vote for "${option.title}"`,
              variant: 'solid',
              onClick: (close) => {
                this.$resources.poll.submitVote.submit({ option: option.title }).then(close)
              },
            },
          ],
        })
      } else {
        if (this.$resources.poll.doc) {
          this.$resources.poll.submitVote.submit({ option: option.title })
        } else {
          this.$resources.poll.get.fetch().then(() => {
            this.$resources.poll.submitVote.submit({ option: option.title })
          })
        }
      }
    },
    stopPoll() {
      this.$dialog({
        title: 'Stop poll',
        message: 'After the poll is stopped, no one will be able to vote on it. Continue?',
        actions: [
          {
            label: 'Stop',
            variant: 'solid',
            theme: 'red',
            onClick: (close) => this.$resources.poll.stopPoll.submit().then(close),
          },
        ],
      })
    },
    isVotedByUser(option) {
      return this._poll.votes.find(
        (vote) => vote.option === option && vote.user === this.$user().name,
      )
    },
    copyLink() {
      let location = window.location
      let url = `${location.origin}${location.pathname}?poll=${this.poll.name}`
      copyToClipboard(url)
    },
  },
  computed: {
    participated() {
      return this._poll.votes.some((d) => d.user === this.$user().name) ?? false
    },
    pollResults() {
      if (!this.$resources.poll.doc || this._poll.anonymous) return null
      return this._poll.options.map((option) => {
        return {
          title: option.title,
          votes: option.votes,
          percentage: option.percentage,
          voters: this._poll.votes
            .filter((vote) => vote.option === option.title)
            .map((vote) => vote.user),
        }
      })
    },
    dropdownOptions() {
      return [
        {
          label: 'Show results',
          icon: 'bar-chart-2',
          condition: () => !this._poll.anonymous,
          onClick: () => {
            this.showDialog = true
          },
        },
        {
          label: 'Retract vote',
          icon: 'corner-up-left',
          condition: () =>
            !this._poll.anonymous &&
            this.participated &&
            (!this._poll.stopped_at || dayjsLocal().isBefore(this._poll.stopped_at)),
          onClick: () => {
            this.$dialog({
              title: 'Retract vote',
              message: 'Are you sure you want to retract your vote?',
              actions: [
                {
                  label: 'Retract vote',
                  variant: 'solid',
                  theme: 'red',
                  onClick: (close) => this.$resources.poll.retractVote.submit().then(close),
                },
              ],
            })
          },
        },
        {
          label: 'Copy link',
          icon: 'link',
          onClick: this.copyLink,
        },
        {
          label: 'Delete',
          icon: 'trash',
          condition: () => this.$isSessionUser(this._poll.owner),
          onClick: () => {
            this.$dialog({
              title: 'Delete poll',
              message: 'Are you sure you want to delete this poll?',
              actions: [
                {
                  label: 'Delete',
                  variant: 'solid',
                  theme: 'red',
                  onClick: (close) => this.$resources.poll.delete.submit().then(close),
                },
              ],
            })
          },
        },
      ]
    },
    isStopped() {
      return this._poll.stopped_at && dayjsLocal().isAfter(this._poll.stopped_at)
    },
    stopTime() {
      let timestamp = this._poll.stopped_at
      if (dayjsLocal().diff(timestamp, 'day') < 7) {
        return `Ended ${dayjsLocal(timestamp).fromNow()}`
      }
      if (dayjsLocal().diff(timestamp, 'year') < 1) {
        return `Ended at ${dayjsLocal(timestamp).format('D MMM, h:mm A')}`
      }
      return `Ended at ${dayjsLocal(timestamp).format('D MMM YYYY, h:mm A')}`
    },
    _poll() {
      return this.$resources.poll.doc || this.poll
    },
  },
}
</script>
