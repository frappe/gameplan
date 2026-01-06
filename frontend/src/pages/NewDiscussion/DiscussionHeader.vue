<template>
  <PageHeader>
    <Breadcrumbs
      class="h-7"
      :items="[
        { label: 'Drafts', route: { name: 'Drafts' } },
        {
          label: draftDoc?.doc ? draftData.title : 'New Discussion',
          route: { name: 'NewDiscussion' },
        },
      ]"
    />
    <div class="hidden shrink-0 space-x-2 sm:flex">
      <DropdownMoreOptions
        :options="[
          {
            label: 'Delete',
            condition: () => draftDoc?.doc && sessionUser.name == author.name,
            onClick: deleteDraft,
          },
          { label: 'Discard', condition: () => !draftDoc?.doc, onClick: discard },
          {
            label: 'Save Draft',
            condition: () => isDraftChanged && !saveStatus.isSaving,
            onClick: immediateSave,
          },
        ]"
        placement="right"
      />
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
import DropdownMoreOptions from '@/components/DropdownMoreOptions.vue'

const {
  draftDoc,
  draftData,
  sessionUser,
  author,
  deleteDraft,
  discard,
  saveStatus,
  isDraftChanged,
  publish,
  publishing,
  immediateSave,
} = useNewDiscussionContext()
</script>
