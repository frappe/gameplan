<template>
  <ProfileImageField
    :label="spec.title"
    :subject="spec.title"
    :has-image="Boolean(card.image)"
    :busy="saving"
    @upload="saveImage"
    @remove="saveImage('')"
  >
    <!-- Only the cover: an avatar is a picture of a person, and a stock photo is
         never the right one. -->
    <template v-if="isCover" #actions>
      <Button
        icon-left="lucide-image"
        data-profile-unsplash-open
        :disabled="saving"
        @click="showPicker = true"
      >
        Unsplash
      </Button>
    </template>
  </ProfileImageField>

  <UnsplashPicker
    v-model:open="showPicker"
    title="Choose a cover image"
    placeholder="Search Unsplash for a place, a mood, a texture"
    @select="applyUnsplashPhoto"
  />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Button } from 'frappe-ui'
import ProfileImageField from '../ProfileImageField.vue'
import { useBoundFieldSave } from './useBoundFieldSave'
import { UnsplashPicker, type UnsplashPhoto } from '@/components/UnsplashPicker'
import type { ProfileBentoCard, ProfileBoundFieldSpec, ProfileFieldEditor } from '../types'

const props = defineProps<{
  spec: ProfileBoundFieldSpec
  card: ProfileBentoCard
  fieldEditor: ProfileFieldEditor
}>()

const { saving, commit } = useBoundFieldSave(() => props.fieldEditor)

const showPicker = ref(false)
const isCover = computed(() => props.spec.field === 'cover_image')

function saveImage(url: string) {
  if (props.spec.field !== 'cover_image' && props.spec.field !== 'image') return
  commit({ field: props.spec.field, value: url })
}

/**
 * An Unsplash photo is hotlinked, not copied into a Frappe File: `cover_image`
 * is an `Attach Image`, which is a plain text column with no local-path rule,
 * and Unsplash's guidelines ask that their URLs be used directly. It goes
 * through the same write path as an upload, so nothing downstream has to tell
 * them apart.
 */
function applyUnsplashPhoto(photo: UnsplashPhoto) {
  saveImage(photo.url)
}
</script>
