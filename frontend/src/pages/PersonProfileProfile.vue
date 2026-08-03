<template>
  <div class="pb-16">
    <!-- Mirrors the rendered layout: one column below `sm`, four above. -->
    <div v-if="!bentoCardsLoaded" class="grid grid-cols-1 gap-3 sm:grid-cols-4">
      <Skeleton class="aspect-[4/1] rounded-xl sm:col-span-4" />
      <Skeleton class="aspect-square rounded-xl sm:col-span-1" />
      <Skeleton class="aspect-square rounded-xl sm:col-span-1" />
      <Skeleton class="aspect-[2/1] rounded-xl sm:col-span-2" />
    </div>
    <ProfileBentoGrid
      v-else
      :cards="bentoCards"
      :editable-cards="Boolean(fieldEditor)"
      @edit="editCard"
    />

    <ProfileAboutDialog v-model:open="showAboutDialog" :text="aboutText" :save="saveAbout" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Skeleton } from 'frappe-ui'
import ProfileAboutDialog from '@/components/ProfileBento/ProfileAboutDialog.vue'
import ProfileBentoGrid from '@/components/ProfileBento/ProfileBentoGrid.vue'
import type { ProfileBentoCard, ProfileFieldEditor } from '@/components/ProfileBento/types'
import { showSettingsDialog } from '@/components/Settings'
import type { GPUserProfile } from '@/types/doctypes'

defineOptions({
  name: 'PersonProfileProfile',
})

// `profile` is passed by PersonProfile's router-view. Declaring it keeps it out
// of `$attrs`, where an object prop would land on the root element as an attribute.
const props = defineProps<{
  profile: { doc?: GPUserProfile | null }
  bentoCards: ProfileBentoCard[]
  bentoCardsLoaded: boolean
  isOwnProfile: boolean
  /** Set only when the viewer owns this profile; enables the card edit buttons. */
  fieldEditor?: ProfileFieldEditor
}>()

const router = useRouter()
const showAboutDialog = ref(false)

const aboutText = computed(() => {
  return props.bentoCards.find((card) => card.field === 'readme')?.text
})

/**
 * The profile page shows a bound field, it never edits one. Each card's edit
 * button hands off to wherever that field is actually owned: About to its own
 * dialog (a rich text field needs the room), the cover to the customize page
 * (where sizing, rendering and reposition live together), everything else to
 * Settings → Profile.
 */
function editCard(card: ProfileBentoCard) {
  if (card.field === 'readme') {
    showAboutDialog.value = true
    return
  }
  if (card.field === 'cover_image') {
    router.push({ name: 'ProfileCustomize', query: { field: 'cover_image' } })
    return
  }
  showSettingsDialog('Profile')
}

async function saveAbout(value: string) {
  if (!props.fieldEditor) throw new Error('Not editable')
  await props.fieldEditor.save({ field: 'readme', value })
}
</script>
