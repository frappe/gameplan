<template>
  <div class="py-6">
    <div class="mb-2 flex items-center text-base text-gray-900">
      <UserInfo :email="_poll.owner" v-slot="{ user }">
        <UserProfileLink class="mr-3" :user="user.name">
          <UserAvatar :user="user.name" />
        </UserProfileLink>
        <div class="md:flex md:items-center">
          <UserProfileLink
            class="font-medium hover:text-blue-600"
            :user="user.name"
          >
            {{ user.full_name }}
            <span class="hidden md:inline">&nbsp;&middot;&nbsp;</span>
          </UserProfileLink>
          <div>
            <time
              class="text-gray-600"
              :datetime="_poll.creation"
              :title="$dayjs(_poll.creation)"
            >
              {{ $dayjs(_poll.creation).fromNow() }}
            </time>
          </div>
        </div>
      </UserInfo>
      <div class="ml-auto flex items-center space-x-2">
        <Tooltip text="This is a poll">
          <FeatherIcon name="bar-chart-2" class="h-4 w-4 -rotate-90" />
        </Tooltip>
        <Dropdown
          placement="right"
          :button="{
            icon: 'more-horizontal',
            appearance: 'minimal',
            label: 'Poll Options',
          }"
          :options="[
            {
              label: 'Retract vote',
              icon: 'edit',
            },
            {
              label: 'Copy link',
              icon: 'link',
              handler: copyLink,
            },
            {
              label: 'Delete',
              icon: 'trash',
              handler: () => {
                $dialog({
                  title: 'Delete poll',
                  message: 'Are you sure you want to delete this poll?',
                  actions: [
                    {
                      label: 'Delete',
                      appearance: 'danger',
                      handler: ({ close }) => {
                        return this.$resources.poll.delete.submit().then(close)
                      },
                    },
                    {
                      label: 'Cancel',
                    },
                  ],
                })
              },
              condition: () => $isSessionUser(_poll.owner),
            },
          ]"
        />
      </div>
    </div>
    <div class="text-base font-semibold">{{ _poll.title }}</div>
    <div class="mt-0.5 text-sm text-gray-600">
      {{ _poll.total_votes }} {{ _poll.total_votes === 1 ? 'vote' : 'votes' }}
    </div>
    <div class="mt-2 space-y-2">
      <button
        class="group flex items-center text-gray-900"
        v-for="option in _poll.options"
        :key="option.idx"
        @click="submitVote(option)"
        :disabled="participated || $resources.poll.submitVote.loading"
      >
        <div
          class="mr-2 h-4 w-4 rounded-full border-2 text-sm"
          :class="
            isVotedByUser(option.title)
              ? 'border-gray-900 bg-gray-900'
              : participated
              ? 'border-gray-300'
              : 'border-gray-300 group-hover:border-gray-400'
          "
        >
          <FeatherIcon
            v-if="isVotedByUser(option.title)"
            name="check"
            class="text-white"
            :stroke-width="2.5"
          />
        </div>
        <div class="flex items-baseline">
          <div class="text-base">{{ option.title }}</div>
          <div class="ml-1 text-xs text-gray-600" v-if="participated">
            ({{ option.percentage }}%)
          </div>
        </div>
      </button>
    </div>
  </div>
</template>
<script>
import { Dropdown, FeatherIcon, Tooltip } from 'frappe-ui'
import UserAvatar from './UserAvatar.vue'
import UserProfileLink from './UserProfileLink.vue'
import { copyToClipboard } from '@/utils'

export default {
  name: 'Poll',
  props: ['poll'],
  emits: ['vote'],
  components: { UserProfileLink, UserAvatar, Dropdown, FeatherIcon, Tooltip },
  resources: {
    poll() {
      return {
        type: 'document',
        doctype: 'GP Poll',
        name: this.poll.name,
        auto: false,
        realtime: true,
        whitelistedMethods: {
          submitVote: 'submit_vote',
        },
      }
    },
  },
  methods: {
    submitVote(option) {
      this.$resources.poll.get.fetch().then(() => {
        this.$resources.poll.submitVote.submit({ option: option.title })
      })
    },
    isVotedByUser(option) {
      return this._poll.votes.find(
        (vote) => vote.title === option && vote.user === this.$user().name
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
      return (
        this._poll.votes.some((vote) => vote.user === this.$user().name) ??
        false
      )
    },
    _poll() {
      return this.$resources.poll.doc || this.poll
    },
  },
}
</script>
