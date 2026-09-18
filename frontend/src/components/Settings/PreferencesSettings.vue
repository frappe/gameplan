<template>
  <!-- On phones the dialog's own bar names the tab (Settings/SettingsDialog.vue). -->
  <SettingsHeader class="max-sm:hidden">
    <h2 class="text-lg-semibold text-ink-gray-8">Preferences</h2>
  </SettingsHeader>

  <SettingsBody>
    <div class="space-y-11 pt-6">
      <section>
        <div class="divide-y divide-outline-gray-1">
          <SettingsRow
            title="Appearance"
            description="Choose a light, dark, or system-matched interface"
          >
            <Select :options="themeOptions" v-model="selectedTheme">
              <template #item-prefix="{ item }">
                <div
                  class="size-3 rounded-full border border-outline-gray-2 flex overflow-hidden"
                  v-if="item.value === 'system'"
                >
                  <div class="w-1/2 bg-white"></div>
                  <div class="w-1/2 bg-gray-950"></div>
                </div>
                <div
                  v-else
                  class="size-3 rounded-full border"
                  :class="item.value == 'light' ? 'bg-white border-outline-gray-2' : 'bg-gray-950'"
                ></div>
              </template>
            </Select>
          </SettingsRow>

          <SettingsRow
            title="Cursor"
            description="Show the pointer on everything clickable, or only on external links"
          >
            <Select :options="cursorStyleOptions" v-model="selectedCursorStyle" />
          </SettingsRow>
        </div>
      </section>

      <section>
        <h2 class="text-lg-semibold text-ink-gray-8">Sidebar</h2>

        <div class="mt-2 divide-y divide-outline-gray-1">
          <SettingsRow title="Unread badge" description="Show unread activity as a dot or a count">
            <Select
              :options="badgeStyleOptions"
              v-model="selectedBadgeStyle"
              :disabled="savingBadgeStyle"
            />
          </SettingsRow>

          <SettingsRow
            title="Communities"
            description="Show, hide, and reorder communities in the left rail"
          >
            <Button @click="showCustomizeSidebar = true">Customize</Button>
          </SettingsRow>

          <SettingsRow
            title="Space sorting"
            description="Choose how spaces are ordered in the current community sidebar"
          >
            <Select :options="spaceSortOptions" v-model="selectedSpaceSort" />
          </SettingsRow>

          <SettingsRow
            title="Inactive spaces"
            description="Hide spaces with no activity for the last 2 months"
          >
            <Switch v-model="hideInactiveSpaces" />
          </SettingsRow>
        </div>
      </section>

      <section>
        <h2 class="text-lg-semibold text-ink-gray-8">Reactions</h2>

        <div class="mt-2 divide-y divide-outline-gray-1">
          <SettingsRow
            title="Quick reactions"
            description="Choose the emoji shown in the reaction picker. Drag to reorder"
          >
            <Button
              variant="subtle"
              icon-left="lucide-rotate-ccw"
              @click="resetQuickReactionEmojis"
            >
              Reset
            </Button>
          </SettingsRow>
        </div>

        <QuickReactionsEditor class="mt-2" />
      </section>
    </div>
  </SettingsBody>

  <CustomizeSidebarDialog v-model="showCustomizeSidebar" />
</template>

<script setup lang="ts">
// Declared so the parent's @close-dialog isn't treated as a failed attribute
// fallthrough (this component renders a fragment); it simply isn't emitted here.
defineEmits<{ (e: 'close-dialog'): void }>()
import { computed, ref } from 'vue'
import {
  Button,
  SettingsBody,
  SettingsHeader,
  SettingsRow,
  Select,
  Switch,
  toast,
  useDoctype,
} from 'frappe-ui'
import CustomizeSidebarDialog from '@/components/AppRail/CustomizeSidebarDialog.vue'
import { resetQuickReactionEmojis } from '@/data/reactionPreferences'
import {
  currentHideInactiveSpaces,
  currentSidebarBadgeStyle,
  currentSpaceSidebarSort,
  setHideInactiveSpaces,
  setSidebarBadgeStyle,
  setSpaceSidebarSort,
  type SidebarBadgeStyle,
  type SpaceSidebarSort,
} from '@/data/sidebarPreferences'
import { useSessionUser } from '@/data/users'
import { useTheme, type Theme } from '@/utils/useTheme'
import { useCursorStyle, type CursorStyle } from '@/utils/useCursorStyle'
import type { GPUserProfile } from '@/types/doctypes'
import QuickReactionsEditor from './QuickReactionsEditor.vue'

const sessionUser = useSessionUser()
const { currentTheme, setTheme } = useTheme()
const { currentCursorStyle, setCursorStyle } = useCursorStyle()
const userProfiles = useDoctype<GPUserProfile>('GP User Profile')

const showCustomizeSidebar = ref(false)
const savingBadgeStyle = ref(false)

const themeOptions: Array<{ label: string; value: Theme }> = [
  { label: 'Light', value: 'light' },
  { label: 'Dark', value: 'dark' },
  { label: 'System Default', value: 'system' },
]

const cursorStyleOptions: Array<{ label: string; value: CursorStyle }> = [
  { label: 'Pointer', value: 'pointer' },
  { label: 'Normal', value: 'normal' },
]

const badgeStyleOptions: Array<{ label: SidebarBadgeStyle; value: SidebarBadgeStyle }> = [
  { label: 'Dot', value: 'Dot' },
  { label: 'Unread count', value: 'Unread count' },
]

const spaceSortOptions: Array<{ label: SpaceSidebarSort; value: SpaceSidebarSort }> = [
  { label: 'Recent activity', value: 'Recent activity' },
  { label: 'Alphabetical', value: 'Alphabetical' },
]

const selectedTheme = computed({
  get: () => currentTheme.value,
  set: (theme: Theme) => setTheme(theme),
})

const selectedCursorStyle = computed({
  get: () => currentCursorStyle.value,
  set: (style: CursorStyle) => setCursorStyle(style),
})

const selectedSpaceSort = computed({
  get: () => currentSpaceSidebarSort.value,
  set: (sort: SpaceSidebarSort) => setSpaceSidebarSort(sort),
})

const hideInactiveSpaces = computed({
  get: () => currentHideInactiveSpaces.value,
  set: (value: boolean) => setHideInactiveSpaces(value),
})

const selectedBadgeStyle = computed({
  get: () => currentSidebarBadgeStyle.value,
  set: saveBadgeStyle,
})

async function saveBadgeStyle(style: SidebarBadgeStyle) {
  if (style === currentSidebarBadgeStyle.value || savingBadgeStyle.value) return

  let profileName = sessionUser.user_profile
  if (!profileName) {
    toast.error('Could not find your profile')
    return
  }

  savingBadgeStyle.value = true
  try {
    await userProfiles.setValue.submit({
      name: profileName,
      sidebar_badge_style: style,
    })
    setSidebarBadgeStyle(style)
    sessionUser.sidebar_badge_style = style
    toast.success('Sidebar preference saved')
  } catch {
    toast.error('Could not save sidebar preference')
  } finally {
    savingBadgeStyle.value = false
  }
}
</script>
