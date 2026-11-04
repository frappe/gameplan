<template>
  <div class="mt-5 space-y-5 text-ink-gray-9">
    <p class="text-base text-ink-gray-6">
      Rules apply to this Community. Code is preserved. Block takes priority over approval and
      flagging.
    </p>
    <Select v-model="action" label="Action" :options="actions" class="max-w-xs" />
    <div class="flex flex-wrap gap-2">
      <FileUploader
        :file-types="['.csv']"
        :private="true"
        :validate-file="validateFile"
        @success="previewFile"
        @failure="showError"
      >
        <template #default="{ openFileSelector, uploading, progress }">
          <Button :loading="uploading" @click="openFileSelector">{{
            uploading ? `Uploading ${progress}%` : 'Add from CSV'
          }}</Button>
        </template>
      </FileUploader>
      <Button :href="downloadUrl(false)">Download list</Button>
      <Button :href="downloadUrl(true)">Sample CSV</Button>
    </div>
    <div class="flex flex-wrap items-end gap-2">
      <TextInput
        v-model="word"
        label="Word or phrase"
        placeholder="Word or phrase"
        class="min-w-0 flex-1"
      />
      <div class="flex h-7 items-center gap-2">
        <Checkbox v-model="caseSensitive" label="Case sensitive" />
        <Button :disabled="!word.trim()" :loading="saving" @click="addWord">Add rule</Button>
      </div>
    </div>
    <ErrorMessage v-if="error" :message="error" />
    <div
      v-for="rule in items"
      :key="rule.name"
      class="flex items-center justify-between gap-3 border-b border-outline-gray-2 py-4"
    >
      <span class="text-base"
        >{{ rule.word }}
        <span v-if="rule.case_sensitive" class="text-ink-gray-5">(case sensitive)</span></span
      >
      <Button @click="deleteRule(rule)">Delete</Button>
    </div>
    <p v-if="!items.length" class="text-base text-ink-gray-5">No rules for this action.</p>
    <div class="flex gap-2">
      <Button v-if="start" @click="start -= 40">Previous</Button
      ><Button v-if="hasMore" @click="start += 40">Next</Button>
    </div>
    <Textarea v-model="testText" label="Test words or a post" placeholder="Test words or a post" />
    <Button @click="testRules">Test rules</Button>
    <p v-for="(words, key) in results" :key="key" class="text-base">
      {{ key }}: {{ words.length ? words.join(', ') : 'No matches' }}
    </p>
    <Dialog v-model:open="previewOpen" title="Preview CSV import">
      <p class="text-base">
        {{ preview?.added }} new rules · {{ preview?.duplicates }} duplicates skipped. Existing
        rules stay unchanged.
      </p>
      <ul class="mt-3 text-base">
        <li v-for="entry in preview?.words" :key="entry">{{ entry }}</li>
      </ul>
      <p v-if="(preview?.added || 0) > 40" class="mt-2 text-base text-ink-gray-5">
        Showing the first 40 new rules.
      </p>
      <ErrorMessage v-if="error" :message="error" />
      <template #actions
        ><Button variant="solid" :loading="saving" @click="applyImport"
          >Import {{ preview?.added }} rules</Button
        ></template
      >
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import {
  Button,
  Dialog,
  ErrorMessage,
  FileUploader,
  TextInput,
  Checkbox,
  Select,
  Textarea,
  call,
  dialog,
  toast,
} from 'frappe-ui'
import { extractServerMessage } from '@/utils'
const props = defineProps<{ communityId: string }>()
const actions = ['Block', 'Censor', 'Require approval', 'Flag']
const action = ref('Block'),
  word = ref(''),
  caseSensitive = ref(false),
  start = ref(0),
  hasMore = ref(false)
type Rule = { name: string; word: string; case_sensitive: number }
type Preview = { expected: string; added: number; duplicates: number; words: string[] }
const items = ref<Rule[]>([]),
  preview = ref<Preview | null>(null),
  previewOpen = ref(false),
  file = ref(''),
  error = ref(''),
  saving = ref(false)
const testText = ref(''),
  results = ref<Record<string, string[]>>({})
function showError(e: unknown) {
  error.value = extractServerMessage(e) || 'Could not update watched words'
}
let loadRequest = 0
async function load() {
  const request = ++loadRequest
  items.value = []
  error.value = ''
  try {
    const result = await call<{ items: Rule[]; has_more: boolean }>(
      'gameplan.watched_words.rules',
      { community: props.communityId, action: action.value, start: start.value },
    )
    if (request !== loadRequest) return
    items.value = result.items
    hasMore.value = result.has_more
  } catch (e) {
    if (request === loadRequest) showError(e)
  }
}
function validateFile(file: File) {
  if (file.size > 1024 * 1024) return 'CSV uploads must be at most 1 MB'
}
async function previewFile(uploaded: { name: string }) {
  file.value = uploaded.name
  error.value = ''
  try {
    preview.value = await call('gameplan.watched_words.upload', {
      community: props.communityId,
      action: action.value,
      file: file.value,
    })
    previewOpen.value = true
  } catch (e) {
    showError(e)
  }
}
async function applyImport() {
  saving.value = true
  try {
    await call('gameplan.watched_words.upload', {
      community: props.communityId,
      action: action.value,
      file: file.value,
      expected: preview.value?.expected,
    })
    previewOpen.value = false
    toast.success('Watched words imported')
    await load()
  } catch (e) {
    showError(e)
  } finally {
    saving.value = false
  }
}
async function addWord() {
  saving.value = true
  try {
    await call('gameplan.watched_words.add', {
      community: props.communityId,
      action: action.value,
      word: word.value,
      case_sensitive: caseSensitive.value,
    })
    word.value = ''
    await load()
  } catch (e) {
    showError(e)
  } finally {
    saving.value = false
  }
}
function deleteRule(rule: Rule) {
  dialog.danger({
    title: 'Delete watched word',
    message: `Remove “${rule.word}” from ${action.value}?`,
    confirmLabel: 'Delete rule',
    onConfirm: async () => {
      try {
        await call('gameplan.watched_words.remove', {
          community: props.communityId,
          name: rule.name,
        })
        await load()
      } catch (e) {
        showError(e)
      }
    },
  })
}
function downloadUrl(sample: boolean) {
  return (
    '/api/method/gameplan.watched_words.download?' +
    new URLSearchParams({
      community: props.communityId,
      action: action.value,
      sample: sample ? '1' : '0',
    })
  )
}
async function testRules() {
  try {
    results.value = await call('gameplan.watched_words.test', {
      community: props.communityId,
      content: testText.value,
    })
  } catch (e) {
    showError(e)
  }
}
watch(
  [() => props.communityId, action],
  () => {
    start.value = 0
    previewOpen.value = false
    results.value = {}
    load()
  },
  { immediate: true },
)
watch(start, load)
</script>
