<template>
  <SettingsHeader>
    <div class="flex flex-col gap-4">
      <h2 class="text-lg-semibold text-ink-gray-8">Custom Emojis</h2>
      <div class="flex items-center justify-between gap-3">
        <TextInput
          class="w-72"
          placeholder="Search by title or keyword"
          :model-value="search"
          @input="search = $event.target.value"
        >
          <template #prefix>
            <span class="lucide-search h-4 w-4 text-ink-gray-4" />
          </template>
        </TextInput>
        <Button icon-left="lucide-upload" @click="openUploadDialog">Upload</Button>
      </div>
    </div>

    <div
      v-if="filteredEmojis.length"
      class="mt-3 grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_6rem_2rem] items-center gap-3 border-b h-8 text-sm text-ink-gray-5"
    >
      <div>Emoji</div>
      <div>Keywords</div>
      <div>By</div>
      <div />
    </div>
  </SettingsHeader>

  <SettingsBody>
    <div
      v-if="customEmojis.loading && !customEmojis.data?.length"
      class="py-8 text-center text-p-sm text-ink-gray-5"
    >
      Loading…
    </div>
    <div v-else-if="!filteredEmojis.length" class="py-8 text-center text-p-sm text-ink-gray-5">
      {{
        search ? 'No emoji match your search.' : 'No custom emoji yet. Upload one to get started.'
      }}
    </div>
    <div v-else class="divide-y">
      <div
        v-for="emoji in filteredEmojis"
        :key="emoji.name"
        class="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_6rem_2rem] items-center gap-3 py-2"
      >
        <div class="flex min-w-0 items-center gap-2">
          <img
            :src="emoji.image"
            :alt="emoji.title"
            class="size-6 shrink-0 rounded-4 object-contain"
          />
          <span class="truncate text-base text-ink-gray-8">{{ emoji.title }}</span>
        </div>
        <div class="truncate text-base text-ink-gray-6">{{ emoji.keywords || '' }}</div>
        <div>
          <Tooltip :text="$user(emoji.owner).full_name">
            <UserAvatar :user="emoji.owner" size="sm" />
          </Tooltip>
        </div>
        <div class="flex justify-end">
          <Button
            variant="ghost"
            icon="lucide-trash-2"
            :label="`Delete ${emoji.title}`"
            :loading="deletingName === emoji.name"
            @click="deleteEmoji(emoji)"
          />
        </div>
      </div>
    </div>
  </SettingsBody>

  <Dialog title="Upload emoji" v-model:open="showUploadDialog">
    <div class="space-y-4">
      <div class="flex items-center gap-3">
        <div
          class="flex size-10 shrink-0 items-center justify-center rounded-4 border border-outline-gray-2 bg-surface-gray-1"
        >
          <img
            v-if="form.image"
            :src="form.image"
            alt="Preview"
            class="h-full w-full rounded-5 object-contain"
          />
          <span v-else class="lucide-image size-5 text-ink-gray-4" />
        </div>
        <ImageUploader kind="customEmoji" @success="(file) => (form.image = file.file_url)">
          <template #default="{ uploading, progress, openFileSelector }">
            <Button :loading="uploading" @click="openFileSelector">
              {{ uploading ? `${progress}%` : form.image ? 'Replace image' : 'Choose image' }}
            </Button>
          </template>
        </ImageUploader>
      </div>

      <FormControl type="text" label="Title" placeholder="party-parrot" v-model="form.title" />
      <FormControl
        type="text"
        label="Keywords (optional)"
        placeholder="celebrate, party, fun"
        v-model="form.keywords"
      />
      <ErrorMessage :message="error" />
    </div>
    <template #actions>
      <Button
        variant="solid"
        class="w-full"
        :loading="saving"
        :disabled="!canSave"
        @click="saveEmoji"
      >
        Upload
      </Button>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
// Declared so the parent's @close-dialog isn't treated as a failed attribute
// fallthrough (this component renders a fragment); it simply isn't emitted here.
defineEmits<{ (e: 'close-dialog'): void }>()
import { computed, ref } from 'vue'
import {
  Button,
  Dialog,
  ErrorMessage,
  FormControl,
  SettingsBody,
  SettingsHeader,
  TextInput,
  Tooltip,
  toast,
} from 'frappe-ui'
import { customEmojis, type CustomEmoji } from '@/data/customEmojis'
import ImageUploader from '@/components/ImageUploader.vue'
import UserAvatar from '@/components/UserAvatar.vue'

const search = ref('')
const showUploadDialog = ref(false)
const saving = ref(false)
const deletingName = ref<string | null>(null)
const error = ref('')
const form = ref({ title: '', image: '', keywords: '' })

const filteredEmojis = computed(() => {
  const list = customEmojis.data || []
  const query = search.value.toLowerCase().trim()
  if (!query) return list
  return list.filter((emoji) => {
    const haystack = `${emoji.title} ${emoji.keywords || ''}`.toLowerCase()
    return haystack.includes(query)
  })
})

const canSave = computed(() => Boolean(form.value.title.trim() && form.value.image))

function openUploadDialog() {
  form.value = { title: '', image: '', keywords: '' }
  error.value = ''
  showUploadDialog.value = true
}

async function saveEmoji() {
  if (!canSave.value || saving.value) return
  error.value = ''
  saving.value = true
  try {
    await customEmojis.insert.submit({
      title: form.value.title.trim(),
      image: form.value.image,
      keywords: form.value.keywords.trim(),
    })
    showUploadDialog.value = false
    toast.success('Emoji uploaded')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Could not upload emoji'
  } finally {
    saving.value = false
  }
}

async function deleteEmoji(emoji: CustomEmoji) {
  if (deletingName.value) return
  deletingName.value = emoji.name
  try {
    await customEmojis.delete.submit({ name: emoji.name })
    toast.success('Emoji deleted')
  } catch (e) {
    toast.error(e instanceof Error ? e.message : 'Could not delete emoji')
  } finally {
    deletingName.value = null
  }
}
</script>
