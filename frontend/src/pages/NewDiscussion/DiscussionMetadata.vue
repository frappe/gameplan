<template>
  <div class="mb-2 flex items-center space-x-3">
    <UserProfileLink :user="author.name">
      <UserAvatar size="lg" :user="author.name" />
    </UserProfileLink>
    <div class="flex w-full items-center">
      <span class="mr-2 text-base text-ink-gray-9">
        <UserProfileLink class="font-medium hover:text-ink-gray-8" :user="author.name">
          {{ author.full_name }}
        </UserProfileLink>
        in
      </span>
      <Combobox
        :options="formattedSpaceOptions"
        v-model="draftData.project"
        placeholder="Select Space"
        :class="[author.name !== sessionUser.name ? 'pointer-events-none' : '']"
        @focus="handleComboboxFocus"
        @blur="handleComboboxBlur"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { Combobox } from 'frappe-ui'
import UserProfileLink from '@/components/UserProfileLink.vue'
import { useNewDiscussionContext } from './useNewDiscussion'

const {
  author,
  sessionUser,
  draftData,
  formattedSpaceOptions,
  handleComboboxFocus,
  handleComboboxBlur,
} = useNewDiscussionContext()
</script>
