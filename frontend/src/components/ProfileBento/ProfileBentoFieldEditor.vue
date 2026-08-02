<template>
  <form
    ref="form"
    class="relative z-10 flex min-w-0 flex-col gap-1.5"
    data-profile-field-editor
    :data-field="field"
    @submit.prevent="save"
    @focusout="handleFocusOut"
    @keydown.esc.stop.prevent="cancel"
    @keydown.enter.meta.prevent="save"
    @keydown.enter.ctrl.prevent="save"
    @click.stop
    @pointerdown.stop
  >
    <template v-if="field === 'full_name'">
      <TextInput
        v-model="firstName"
        placeholder="First name"
        aria-label="First name"
        :disabled="saving"
        @keydown.enter.prevent="save"
      />
      <TextInput
        v-model="lastName"
        placeholder="Last name"
        aria-label="Last name"
        :disabled="saving"
        @keydown.enter.prevent="save"
      />
    </template>
    <!-- Default `subtle` variant on purpose: frappe-ui's `ghost` sets no
         background, so the browser's own white field colour shows through in
         dark mode. -->
    <Textarea
      v-else
      v-model="bio"
      :rows="3"
      :maxlength="profileBioLimit"
      placeholder="Write a short bio"
      aria-label="Bio"
      :disabled="saving"
    />
    <ErrorMessage :message="errorMessage" />
  </form>
</template>

<script setup lang="ts">
import { onMounted, ref, useTemplateRef } from 'vue'
import { ErrorMessage, Textarea, TextInput } from 'frappe-ui'
import { profileBioLimit, type ProfileFieldEditor } from './types'

const props = defineProps<{
  field: 'bio' | 'full_name'
  /** Current value of a `bio` card. Ignored for `full_name`. */
  value?: string
  editor: ProfileFieldEditor
}>()

const emit = defineEmits<{
  close: []
}>()

const form = useTemplateRef<HTMLFormElement>('form')
const bio = ref(props.value || '')
const firstName = ref(props.editor.firstName)
const lastName = ref(props.editor.lastName)
const saving = ref(false)
const errorMessage = ref('')
// A save triggered by blur must not run again while the form is unmounting.
const closing = ref(false)

onMounted(() => {
  form.value?.querySelector<HTMLElement>('textarea, input')?.focus()
})

function isDirty() {
  if (props.field === 'full_name') {
    return (
      firstName.value.trim() !== props.editor.firstName ||
      lastName.value.trim() !== props.editor.lastName
    )
  }
  return bio.value !== (props.value || '')
}

async function save() {
  if (saving.value || closing.value) return
  if (!isDirty()) {
    cancel()
    return
  }

  saving.value = true
  errorMessage.value = ''
  try {
    if (props.field === 'full_name') {
      await props.editor.save({
        field: 'full_name',
        firstName: firstName.value,
        lastName: lastName.value,
      })
    } else {
      await props.editor.save({ field: 'bio', value: bio.value })
    }
    close()
  } catch (error) {
    // Stay open with the draft intact: the card behind still shows the stored
    // value, so nothing unpersisted is ever presented as saved.
    errorMessage.value = getMessage(error)
  } finally {
    saving.value = false
  }
}

function cancel() {
  close()
}

function close() {
  closing.value = true
  emit('close')
}

/** Blur saves, but only once focus has left the editor entirely. */
function handleFocusOut(event: FocusEvent) {
  let nextTarget = event.relatedTarget
  if (nextTarget instanceof Node && form.value?.contains(nextTarget)) return
  save()
}

function getMessage(error: unknown) {
  if (error instanceof Error) return error.message
  return String(error || 'Could not save')
}
</script>
