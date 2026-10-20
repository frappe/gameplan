<template>
  <NodeViewWrapper class="not-prose my-3" contenteditable="false">
    <div
      v-if="node.attrs.poll"
      class="min-w-[50%] max-w-fit rounded-6 border border-outline-gray-2 px-4 py-3"
    >
      <Poll
        v-if="poll"
        embedded
        :poll="poll"
        :space="thread?.space()"
        :read-only-mode="thread?.readOnlyMode()"
      />
      <div v-else class="text-base text-ink-gray-5">Poll unavailable</div>
    </div>
    <div v-else-if="draft" class="space-y-4 rounded-6 border border-outline-gray-2 px-4 py-3">
      <FormControl
        ref="questionInput"
        type="text"
        label="Question"
        :model-value="draft.title"
        @update:model-value="update({ title: $event })"
      />
      <div class="space-y-2">
        <div class="text-sm leading-4 text-ink-gray-6">Options</div>
        <TextInput
          v-for="(option, i) in draft.options"
          :key="i"
          :placeholder="`Option ${i + 1}`"
          :model-value="option.title"
          @update:model-value="updateOption(i, $event)"
        />
      </div>
      <div class="flex items-center gap-2">
        <FormControl
          type="checkbox"
          label="Anonymous"
          :model-value="draft.anonymous"
          :disabled="draft.multiple_answers"
          @update:model-value="update({ anonymous: Boolean($event) })"
        />
        <FormControl
          type="checkbox"
          label="Multiple answers"
          :model-value="draft.multiple_answers"
          :disabled="draft.anonymous"
          @update:model-value="update({ multiple_answers: Boolean($event) })"
        />
        <Button class="ml-auto" @click="deleteNode()">Remove poll</Button>
      </div>
    </div>
  </NodeViewWrapper>
</template>
<script setup lang="ts">
import { computed, inject, nextTick, onMounted, useTemplateRef } from 'vue'
import { NodeViewWrapper, nodeViewProps } from '@tiptap/vue-3'
import { Button, FormControl, TextInput } from 'frappe-ui'
import Poll from '../Poll.vue'
import { threadPollsKey, type PollDraft } from './poll-draft'

type InputRef = { focus: () => void } | null

const props = defineProps(nodeViewProps)

const thread = inject(threadPollsKey, null)
const questionInput = useTemplateRef<InputRef>('questionInput')

const draft = computed<PollDraft | null>(() => props.node.attrs.draft)
const poll = computed(() =>
  thread?.polls.data?.find((p) => String(p.name) === String(props.node.attrs.poll)),
)

onMounted(() => {
  if (draft.value && !draft.value.title) nextTick(() => questionInput.value?.focus())
  if (props.node.attrs.poll && thread && !poll.value && !thread.polls.loading) {
    thread.polls.reload()
  }
})

function update(patch: Partial<PollDraft>) {
  if (!draft.value) return
  props.updateAttributes({ draft: { ...draft.value, ...patch } })
}

function updateOption(index: number, title: string) {
  if (!draft.value) return
  const options = draft.value.options.map((option, i) => (i === index ? { title } : option))
  if (options[options.length - 1].title) options.push({ title: '' })
  update({ options })
}
</script>
