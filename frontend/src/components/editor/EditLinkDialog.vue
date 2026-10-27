<template>
  <Dialog v-model:open="open" title="Edit link">
    <div class="space-y-3">
      <FormControl
        v-model="url"
        type="text"
        label="URL"
        placeholder="https://example.com"
        @keydown.enter.prevent="save"
      />
      <FormControl v-model="label" type="text" label="Text" @keydown.enter.prevent="save" />
      <ErrorMessage :message="error" />
    </div>
    <template #actions>
      <div class="flex items-center gap-2">
        <Button variant="subtle" theme="red" @click="emit('remove')">Remove link</Button>
        <Button class="ml-auto" variant="outline" @click="open = false">Cancel</Button>
        <Button variant="solid" @click="save">Save</Button>
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Button, Dialog, ErrorMessage, FormControl } from 'frappe-ui'

const props = defineProps<{ href: string; text: string }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{
  (e: 'save', link: { href: string; text: string }): void
  (e: 'remove'): void
}>()

const url = ref('')
const label = ref('')
const error = ref('')

watch(open, (isOpen) => {
  if (!isOpen) return
  url.value = props.href
  label.value = props.text
  error.value = ''
})

function normalize(value: string) {
  const trimmed = value.trim()
  if (!trimmed || trimmed.startsWith('/') || /^[a-z][a-z0-9+.-]*:/i.test(trimmed)) return trimmed
  return `https://${trimmed}`
}

function isValid(href: string) {
  if (/\s/.test(href)) return false
  if (href.startsWith('/')) return true
  let url: URL
  try {
    url = new URL(href)
  } catch {
    return false
  }
  if (url.protocol === 'http:' || url.protocol === 'https:') {
    return url.hostname === 'localhost' || url.hostname.includes('.')
  }
  return url.protocol === 'mailto:' || url.protocol === 'tel:'
}

function save() {
  const href = normalize(url.value)
  if (!href || !isValid(href)) {
    error.value = 'Enter a valid URL'
    return
  }
  emit('save', { href, text: label.value.trim() || href })
}
</script>
