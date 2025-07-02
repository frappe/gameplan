<template>
  <PageHeader>
    <Breadcrumbs
      class="h-7"
      :items="[
        { label: 'Drafts', route: { name: 'Discussions' } },
        {
          label: draftDoc?.doc ? draftData.title : 'New Discussion',
          route: { name: 'NewDiscussion' },
        },
      ]"
    />
    <div class="hidden shrink-0 space-x-2 sm:block">
      <Button v-if="draftDoc?.doc" @click="deleteDraft" :disabled="sessionUser.name != author.name">
        Delete
      </Button>
      <Button v-else @click="discard"> Discard </Button>
      <Button @click="saveDraft" :loading="savingDraft" :disabled="!isDraftChanged || savingDraft">
        Save Draft
        <template #suffix>
          <KeyboardShortcut ctrl> S </KeyboardShortcut>
        </template>
      </Button>
      <Tooltip text="You cannot publish this draft" :disabled="sessionUser.name == author.name">
        <Button
          variant="solid"
          :loading="publishing"
          @click="publish"
          :disabled="sessionUser.name != author.name"
        >
          Publish
        </Button>
      </Tooltip>
    </div>
  </PageHeader>
</template>

<script setup lang="ts">
import { Breadcrumbs, Tooltip } from 'frappe-ui'
import PageHeader from '@/components/PageHeader.vue'
import { useNewDiscussionContext } from './useNewDiscussion'

const {
  draftDoc,
  draftData,
  sessionUser,
  author,
  deleteDraft,
  discard,
  saveDraft,
  savingDraft,
  isDraftChanged,
  publish,
  publishing,
} = useNewDiscussionContext()
</script>
