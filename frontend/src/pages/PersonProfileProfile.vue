<template>
  <div class="pb-16">
    <!-- Mirrors the rendered layout: one column below `sm`, four above. -->
    <div v-if="!bentoCardsLoaded" class="grid grid-cols-1 gap-3 sm:grid-cols-4">
      <Skeleton class="aspect-[4/1] rounded-xl sm:col-span-4" />
      <Skeleton class="aspect-square rounded-xl sm:col-span-1" />
      <Skeleton class="aspect-square rounded-xl sm:col-span-1" />
      <Skeleton class="aspect-[2/1] rounded-xl sm:col-span-2" />
    </div>
    <!-- Both branches wait for the cards, so the empty state never flashes. It
         replaces the grid rather than sitting under it: a lone name card above
         "your profile is empty" reads as a contradiction. -->
    <EmptyStateBox v-else-if="isProfileEmpty" class="px-6" data-profile-empty-state>
      <span class="lucide-user-round mb-3 size-7 text-ink-gray-4" aria-hidden="true" />
      <template v-if="isOwnProfile">
        <div class="text-base text-ink-gray-7">Your profile is empty</div>
        <!-- A saved layout is the one cause of a blank page the settings dialog
             cannot fix, so say so and offer the way back. -->
        <p
          v-if="hasSavedLayout"
          class="mt-2 max-w-md text-center text-p-sm text-ink-gray-5"
          data-profile-saved-layout-hint
        >
          Add your photo and bio in profile settings. Your page keeps the layout you saved, so
          restore the default or use Customize to choose what it shows.
        </p>
        <p v-else class="mt-2 max-w-md text-center text-p-sm text-ink-gray-5">
          Add your photo and bio in profile settings. Use Customize to choose what your page shows.
        </p>
        <!-- The two places a profile gets filled in: its values, then its layout. -->
        <div class="mt-4 flex flex-wrap justify-center gap-2">
          <Button
            variant="solid"
            icon-left="lucide-user-round"
            @click="showSettingsDialog('Profile')"
          >
            Edit profile
          </Button>
          <Button icon-left="lucide-layout-grid" @click="customizeLayout">Customize</Button>
          <Button
            v-if="hasSavedLayout"
            icon-left="lucide-rotate-ccw"
            data-profile-restore-default-layout
            @click="$emit('restoreDefaultLayout')"
          >
            Restore default layout
          </Button>
        </div>
      </template>
      <p v-else class="max-w-md text-center text-p-sm text-ink-gray-5">
        This person has not filled in their profile yet.
      </p>
    </EmptyStateBox>

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
import { Button, Skeleton } from 'frappe-ui'
import EmptyStateBox from '@/components/EmptyStateBox.vue'
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
//
// The bento props are optional because the parent only binds them while the
// Profile tab is the route being rendered. Treat their absence as "not loaded
// yet" and show the skeleton — never dereference them.
const props = withDefaults(
  defineProps<{
    profile: { doc?: GPUserProfile | null }
    bentoCards?: ProfileBentoCard[]
    bentoCardsLoaded?: boolean
    /** False once this profile has a saved layout rather than the computed default. */
    bentoIsDefault?: boolean
    isOwnProfile?: boolean
    /** Set only when the viewer owns this profile; enables the card edit buttons. */
    fieldEditor?: ProfileFieldEditor
  }>(),
  { bentoCards: () => [], bentoIsDefault: true },
)

defineEmits<{
  restoreDefaultLayout: []
}>()

const router = useRouter()
const showAboutDialog = ref(false)

const aboutText = computed(() => {
  return props.bentoCards.find((card) => card.field === 'readme')?.text
})

/**
 * "Nothing worth reading on this page", which swaps the grid for the empty state.
 * A bound field with no value produces no card, and `full_name` is always set, so
 * a profile nobody has filled in still renders its name card — that near-empty
 * page is the one real users land on, not a zero-card page. Treating the lone
 * name card as empty covers both, since an empty list satisfies the same rule.
 * Nothing is lost by dropping it: the name is already in the page header.
 */
const isProfileEmpty = computed(() => {
  return (props.bentoCards ?? []).every((card) => card.field === 'full_name')
})

/** Only a saved layout can be restored; the default is already what it would restore to. */
const hasSavedLayout = computed(() => props.bentoIsDefault === false)

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

function customizeLayout() {
  router.push({ name: 'ProfileCustomize' })
}

async function saveAbout(value: string) {
  if (!props.fieldEditor) throw new Error('Not editable')
  await props.fieldEditor.save({ field: 'readme', value })
}
</script>
