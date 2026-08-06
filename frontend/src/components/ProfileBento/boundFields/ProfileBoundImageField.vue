<template>
  <ProfileImageField
    :label="spec.title"
    :subject="spec.title"
    :has-image="Boolean(image)"
    @upload="stageImage"
    @remove="stageImage('')"
  >
    <!-- Only the cover: an avatar is a picture of a person, and a stock photo is
         never the right one. -->
    <template v-if="isCover" #actions>
      <Button icon-left="lucide-image" data-profile-unsplash-open @click="showPicker = true">
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
import { UnsplashPicker, type UnsplashPhoto } from '@/components/UnsplashPicker'
import type { ProfileBoundFieldSpec, ProfileFieldDraft } from '../types'

const props = defineProps<{
  spec: ProfileBoundFieldSpec
  draft: ProfileFieldDraft
}>()

const showPicker = ref(false)
const isCover = computed(() => props.spec.field === 'cover_image')
// The staged image if one was picked, otherwise whatever the profile holds. The
// file is already uploaded by this point; only the profile field is staged.
const image = computed(() => {
  return isCover.value ? props.draft.values.cover_image : props.draft.values.image
})

function stageImage(url: string) {
  if (props.spec.field !== 'cover_image' && props.spec.field !== 'image') return
  props.draft.stage({ field: props.spec.field, value: url })
}

/**
 * An Unsplash photo is hotlinked, not copied into a Frappe File: `cover_image`
 * is an `Attach Image`, which is a plain text column with no local-path rule,
 * and Unsplash's guidelines ask that their URLs be used directly. It goes
 * through the same path as an upload, so nothing downstream has to tell them
 * apart.
 */
function applyUnsplashPhoto(photo: UnsplashPhoto) {
  stageImage(photo.url)
}
</script>
