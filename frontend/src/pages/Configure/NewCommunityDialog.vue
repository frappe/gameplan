<template>
  <Dialog title="New Community" v-model:open="show">
    <div class="space-y-4">
      <p class="text-p-base text-ink-gray-6">
        Communities group spaces, members, and visibility settings for a team or group.
      </p>
      <TextInput
        v-model="title"
        label="Name"
        placeholder="Community name"
        autofocus
        @keydown.enter.prevent="submit"
      />
      <FormControl
        v-model="visibility"
        type="select"
        label="Visibility"
        :options="visibilityOptions"
      />
      <ErrorMessage :message="communities.insert.error" />
    </div>

    <template #actions>
      <div class="flex justify-end gap-2">
        <Button @click="show = false">Cancel</Button>
        <Button
          variant="solid"
          :disabled="!canSubmit"
          :loading="communities.insert.loading"
          @click="submit"
        >
          Create
        </Button>
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Button, Dialog, ErrorMessage, FormControl, TextInput } from 'frappe-ui'
import { communities } from '@/data/communities'
import type { GPTeam } from '@/types/doctypes'
import { isGameplanAdmin } from '@/data/users'
import { creatableVisibilityOptions, VISIBILITY_GENERAL, type Visibility } from '@/utils/visibility'

const show = defineModel<boolean>()
const emit = defineEmits<{
  (event: 'created', communityId: string): void
}>()
const title = ref('')
const visibility = ref<Visibility>(VISIBILITY_GENERAL)
const visibilityOptions = computed(() => creatableVisibilityOptions(isGameplanAdmin()))

const canSubmit = computed(() => Boolean(title.value.trim()) && !communities.insert.loading)

watch(show, (value) => {
  if (!value) return
  title.value = ''
  visibility.value = VISIBILITY_GENERAL
})

async function submit() {
  const nextTitle = title.value.trim()
  if (!nextTitle || communities.insert.loading) return

  const community = (await communities.insert.submit({
    title: nextTitle,
    visibility: visibility.value,
  })) as unknown as GPTeam | undefined

  await communities.reload()
  show.value = false

  if (community?.name) {
    emit('created', community.name)
  }
}
</script>
