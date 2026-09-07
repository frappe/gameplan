<template>
  <Dialog v-model:open="show" size="md" bare>
    <div class="flex flex-col" style="height: min(640px, calc(100vh - 8rem))">
      <div
        class="flex shrink-0 items-center justify-between border-b border-outline-gray-1 px-4 py-3"
      >
        <Dialog.Title as-child>
          <h2 class="text-lg font-medium text-ink-gray-9">Customize sidebar</h2>
        </Dialog.Title>
        <Dialog.Close as-child>
          <Button variant="ghost" label="Close" icon="lucide-x" />
        </Dialog.Close>
      </div>

      <ScrollArea class="min-h-0 flex-1" viewport-class="px-4 py-3">
        <div v-if="manageableCommunities.length > 0" class="space-y-4">
          <section class="flex items-center justify-between gap-3">
            <h3 class="text-base font-medium text-ink-gray-8">Badge style</h3>
            <Select :options="badgeStyleOptions" v-model="selectedBadgeStyle" />
          </section>

          <section class="space-y-1.5">
            <h3 class="text-base font-medium text-ink-gray-8">Shown in sidebar</h3>
            <div ref="shownSection" :class="getCommunityListClasses('shown')">
              <div>
                <div
                  v-for="community in selectedManageableCommunities"
                  :key="community.name"
                  data-sortable-section="shown"
                  :data-sortable-id="community.name"
                  class="group relative flex min-h-8 w-full touch-none cursor-grab select-none items-center gap-2 rounded-4 px-1.5 py-0.5 text-left text-ink-gray-8 hover:bg-surface-gray-1"
                  :class="getCommunityRowClasses(community.name)"
                  :style="getItemStyle(community.name, 'shown')"
                  @pointerdown="startPointerDrag($event, community.name, 'shown')"
                  @pointermove="updatePointerDrag"
                  @pointerup="finishPointerDrag"
                  @pointercancel="cancelPointerDrag"
                >
                  <span
                    class="lucide-grip-vertical size-4 shrink-0 text-ink-gray-4"
                    aria-hidden="true"
                  />
                  <CommunityImage
                    :community="community"
                    class="size-5 shrink-0 bg-surface-gray-1"
                  />
                  <span class="min-w-0 flex-1">
                    <span class="flex items-center gap-1.5 text-base">
                      <span class="truncate">{{ community.title }}</span>
                      <span
                        v-if="community.is_private"
                        class="lucide-lock size-3.5 shrink-0 text-ink-gray-5"
                      />
                    </span>
                  </span>
                  <Button
                    variant="ghost"
                    size="xs"
                    icon="lucide-arrow-down"
                    :label="`Hide ${community.title} from sidebar`"
                    tooltip="Hide from sidebar"
                    class="shrink-0 text-ink-gray-5 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100 focus-visible:opacity-100"
                    @pointerdown.stop
                    @mousedown.stop
                    @click.stop="moveCommunityToSection(community.name, 'hidden')"
                  />
                </div>
              </div>

              <div
                v-if="selectedManageableCommunities.length === 0"
                class="px-3 py-6 text-center text-p-sm text-ink-gray-5"
              >
                No communities shown
              </div>
            </div>
          </section>

          <section class="space-y-1.5">
            <h3 class="text-base font-medium text-ink-gray-8">Hidden from sidebar</h3>
            <div ref="hiddenSection" :class="getCommunityListClasses('hidden')">
              <div
                v-for="community in hiddenManageableCommunities"
                :key="community.name"
                data-sortable-section="hidden"
                :data-sortable-id="community.name"
                class="group relative flex min-h-8 w-full touch-none cursor-grab select-none items-center gap-2 rounded-5 px-1.5 py-0.5 text-left text-ink-gray-8 hover:bg-surface-gray-1"
                :class="getCommunityRowClasses(community.name)"
                :style="getItemStyle(community.name, 'hidden')"
                @pointerdown="startPointerDrag($event, community.name, 'hidden')"
                @pointermove="updatePointerDrag"
                @pointerup="finishPointerDrag"
                @pointercancel="cancelPointerDrag"
              >
                <span
                  class="lucide-grip-vertical size-4 shrink-0 text-ink-gray-4"
                  aria-hidden="true"
                />
                <CommunityImage :community="community" class="size-5 shrink-0 bg-surface-gray-1" />
                <span class="min-w-0 flex-1">
                  <span class="flex items-center gap-1.5 text-base">
                    <span class="truncate">{{ community.title }}</span>
                    <span
                      v-if="community.is_private"
                      class="lucide-lock size-3.5 shrink-0 text-ink-gray-5"
                    />
                  </span>
                </span>
                <Button
                  variant="ghost"
                  size="xs"
                  icon="lucide-arrow-up"
                  :label="`Show ${community.title} in sidebar`"
                  tooltip="Show in sidebar"
                  class="shrink-0 text-ink-gray-5 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100 focus-visible:opacity-100"
                  @pointerdown.stop
                  @mousedown.stop
                  @click.stop="moveCommunityToSection(community.name, 'shown')"
                />
              </div>

              <div
                v-if="hiddenManageableCommunities.length === 0"
                class="px-3 py-6 text-center text-p-sm text-ink-gray-5"
              >
                No hidden communities
              </div>
            </div>
          </section>
        </div>

        <div v-else class="px-3 py-6 text-center text-p-sm text-ink-gray-5">
          No communities found
        </div>
      </ScrollArea>

      <div class="flex shrink-0 justify-end border-t border-outline-gray-1 px-4 py-3">
        <Button
          variant="solid"
          :disabled="!hasUnsavedChanges"
          :loading="isSaving"
          @click="saveChanges"
        >
          Save
        </Button>
      </div>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, Dialog, ScrollArea, Select, toast, useCall } from 'frappe-ui'
import { communityState } from '@/data/communityState'
import { activeCommunities, availableCommunities, communities } from '@/data/communities'
import type { Community } from '@/data/communities'
import { setCommunityOrder } from '@/data/communityOrder'
import {
  currentSidebarBadgeStyle,
  setSidebarBadgeStyle,
  type SidebarBadgeStyle,
} from '@/data/sidebarPreferences'
import { sessionUser } from '@/data/session'
import { useSessionUser } from '@/data/users'
import {
  usePointerSortableSections,
  type PointerSortableCommit,
  type PointerSortableItem,
} from '@/composables/usePointerSortableSections'
import CommunityImage from '../CommunityImage.vue'

type SidebarSection = 'shown' | 'hidden'

interface SidebarPreferencesPayload {
  teams: string[]
  sidebar_badge_style: SidebarBadgeStyle
}

const badgeStyleOptions: Array<{ label: SidebarBadgeStyle; value: SidebarBadgeStyle }> = [
  { label: 'Unread count', value: 'Unread count' },
  { label: 'Dot', value: 'Dot' },
]

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
}>()

const route = useRoute()
const router = useRouter()
const selectedCommunityNames = ref<string[]>([])
const initialCommunityNames = ref<string[]>([])
const selectedBadgeStyle = ref<SidebarBadgeStyle>('Dot')
const initialBadgeStyle = ref<SidebarBadgeStyle>('Dot')
const isSaving = ref(false)
const user = useSessionUser()

const show = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const manageableCommunities = computed(() => {
  return availableCommunities.value.filter((community) => !community.archived_at)
})

const selectedManageableCommunities = computed(() => {
  let communitiesByName = new Map(
    manageableCommunities.value.map((community) => [community.name, community]),
  )

  return selectedCommunityNames.value
    .map((name) => communitiesByName.get(name))
    .filter((community): community is Community => community !== undefined)
})

const selectedSortableCommunities = computed<PointerSortableItem[]>(() => {
  return selectedManageableCommunities.value.map((community) => ({ id: community.name }))
})

const hiddenManageableCommunities = computed(() => {
  let selectedCommunitySet = new Set(selectedCommunityNames.value)
  return manageableCommunities.value.filter(
    (community) => !selectedCommunitySet.has(community.name),
  )
})

const hiddenSortableCommunities = computed<PointerSortableItem[]>(() => {
  return hiddenManageableCommunities.value.map((community) => ({ id: community.name }))
})

const updateJoinedTeams = useCall<string[], SidebarPreferencesPayload>({
  url: '/api/v2/method/GP Team/update_joined_teams',
  method: 'POST',
  immediate: false,
})

const hasUnsavedChanges = computed(() => {
  return (
    selectedBadgeStyle.value !== initialBadgeStyle.value ||
    !haveSameOrderedCommunityNames(selectedCommunityNames.value, initialCommunityNames.value)
  )
})

const {
  activeSection,
  startPointerDrag,
  updatePointerDrag,
  finishPointerDrag,
  cancelPointerDrag,
  isDraggingItem,
  getItemStyle,
} = usePointerSortableSections<SidebarSection>({
  sections: ['shown', 'hidden'],
  sectionRefNames: {
    shown: 'shownSection',
    hidden: 'hiddenSection',
  },
  sortableSection: 'shown',
  itemsBySection: {
    shown: selectedSortableCommunities,
    hidden: hiddenSortableCommunities,
  },
  onCommit: handleSidebarItemDrop,
})

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      initializeSelection()
    }
  },
)

function initializeSelection() {
  selectedCommunityNames.value = activeCommunities.value.map((community) => community.name)
  initialCommunityNames.value = [...selectedCommunityNames.value]
  selectedBadgeStyle.value = currentSidebarBadgeStyle.value
  initialBadgeStyle.value = selectedBadgeStyle.value
}

function getCommunityRowClasses(communityName: string) {
  if (!isDraggingItem(communityName)) return 'transition-colors'

  return 'z-10 cursor-grabbing bg-surface-base shadow-sm ring-1 ring-outline-gray-2'
}

function getCommunityListClasses(section: SidebarSection) {
  return [
    'min-h-16 rounded-6 border border-outline-gray-2 px-1.5 py-2 transition-colors',
    activeSection.value === section ? 'border-outline-gray-4' : '',
  ]
}

function handleSidebarItemDrop({
  itemId,
  sourceSection,
  targetSection,
  targetIndex,
}: PointerSortableCommit<SidebarSection>) {
  if (targetSection === 'hidden') {
    if (sourceSection === 'shown') {
      moveCommunityToSection(itemId, 'hidden')
    }
    return
  }

  placeCommunityInShown(itemId, targetIndex)
}

function moveCommunityToSection(communityName: string, section: SidebarSection) {
  if (section === 'shown') {
    if (!selectedCommunityNames.value.includes(communityName)) {
      selectedCommunityNames.value = [...selectedCommunityNames.value, communityName]
    }
    return
  }

  if (!selectedCommunityNames.value.includes(communityName)) return
  if (selectedCommunityNames.value.length === 1) {
    toast.error('Select at least one community')
    return
  }

  selectedCommunityNames.value = selectedCommunityNames.value.filter(
    (name) => name !== communityName,
  )
}

function placeCommunityInShown(communityName: string, targetIndex: number) {
  let communityNames = selectedCommunityNames.value.filter((name) => name !== communityName)
  let index = clamp(targetIndex, 0, communityNames.length)

  communityNames.splice(index, 0, communityName)
  selectedCommunityNames.value = communityNames
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max)
}

async function saveChanges() {
  if (isSaving.value) return
  if (!hasUnsavedChanges.value) return

  if (selectedCommunityNames.value.length === 0) {
    toast.error('Select at least one community')
    return
  }

  let previousCommunityId = communityState.id
  isSaving.value = true

  try {
    await updateJoinedTeams.submit({
      teams: selectedCommunityNames.value,
      sidebar_badge_style: selectedBadgeStyle.value,
    })
    setCommunityOrder(selectedCommunityNames.value)
    setSidebarBadgeStyle(selectedBadgeStyle.value)
    user.sidebar_badge_style = selectedBadgeStyle.value
    updateLocalCommunityMembership()

    if (previousCommunityId && !selectedCommunityNames.value.includes(previousCommunityId)) {
      let nextCommunity = activeCommunities.value[0]
      communityState.change(nextCommunity?.name ?? null)

      if (route.matched.some((record) => record.meta?.communityScope)) {
        router.push(
          nextCommunity
            ? { name: 'Discussions', params: { communityId: nextCommunity.name } }
            : { name: 'NoCommunities' },
        )
      }
    }

    initialCommunityNames.value = [...selectedCommunityNames.value]
    initialBadgeStyle.value = selectedBadgeStyle.value
    show.value = false
    toast.success('Sidebar updated')
  } catch {
    toast.error('Failed to update sidebar')
  } finally {
    isSaving.value = false
  }
}

function haveSameOrderedCommunityNames(left: string[], right: string[]) {
  if (left.length !== right.length) return false
  return left.every((name, index) => name === right[index])
}

function updateLocalCommunityMembership() {
  let user = sessionUser.value
  if (!user) return

  let selectedCommunitySet = new Set(selectedCommunityNames.value)
  for (let community of manageableCommunities.value) {
    let members = community.members || []
    let isSelected = selectedCommunitySet.has(community.name)
    let hasMember = members.some((member) => member.user === user)

    if (isSelected && !hasMember) {
      communities.updateRow({
        name: community.name,
        members: [...members, { user }],
      })
    }

    if (!isSelected && hasMember) {
      communities.updateRow({
        name: community.name,
        members: members.filter((member) => member.user !== user),
      })
    }
  }
}
</script>
