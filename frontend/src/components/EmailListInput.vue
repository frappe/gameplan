<template>
  <FormControl
    v-model="model"
    type="textarea"
    :label="label"
    placeholder="jane@example.com, sam@example.com"
    :rows="3"
    description="Separate multiple email addresses with commas or new lines"
    :error="error"
    :disabled="disabled"
    @blur="touched = true"
  />
</template>

<script lang="ts">
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

/** The addresses in `text`, split on commas and new lines, and the ones that are not emails. */
export function parseEmailList(text: string): { emails: string[]; invalid: string[] } {
  const emails = text
    .split(/[\n,]/)
    .map((email) => email.trim())
    .filter(Boolean)
  return { emails, invalid: emails.filter((email) => !EMAIL_PATTERN.test(email)) }
}
</script>

<script setup lang="ts">
// The invite-by-email box in onboarding and the Invite people dialog. The error waits
// for blur, or for `validate()` on submit, so a half-typed address is not flagged.
import { computed, ref } from 'vue'
import { FormControl } from 'frappe-ui'

defineProps<{
  label?: string
  disabled?: boolean
}>()

const model = defineModel<string>({ required: true })
const touched = ref(false)

const invalid = computed(() => parseEmailList(model.value).invalid)
const error = computed(() => {
  if (!touched.value || !invalid.value.length) return undefined
  const [first, ...rest] = invalid.value
  if (!rest.length) return `${first} is not a valid email address`
  return `${invalid.value.join(', ')} are not valid email addresses`
})

defineExpose({
  /** Shows any invalid address and returns whether the list can be sent. */
  validate(): boolean {
    touched.value = true
    return !invalid.value.length
  },
})
</script>
