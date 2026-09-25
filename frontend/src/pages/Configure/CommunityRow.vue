<template>
  <!-- Phones draw a second line of details under the name, so the row grows to fit;
       desktop keeps its one-line 40px. -->
  <ListRow class="max-md:h-auto max-md:py-3 md:h-10">
    <ListCell class="gap-2 max-md:gap-3">
      <CommunityImageUploader v-if="canManage" :community="community" class="shrink-0" />
      <CommunityImage
        v-else
        :community="community"
        class="size-6 shrink-0 rounded-[5px] bg-surface-gray-1"
      />

      <div class="min-w-0">
        <div class="truncate text-base-medium text-ink-gray-7">
          {{ community.title }}
        </div>
        <!-- Phones fold the Spaces / Members columns into one line under the name; the
             two counts are still the way into those views, as plain text links. -->
        <div class="mt-0.5 truncate text-sm text-ink-gray-5 md:hidden">
          <button
            type="button"
            class="hover:text-ink-gray-7"
            @click="emit('view-spaces', community.name)"
          >
            {{ spacesLabel }}
          </button>
          <span aria-hidden="true"> · </span>
          <button
            type="button"
            class="hover:text-ink-gray-7"
            @click="emit('view-members', community.name)"
          >
            {{ membersLabel }}
          </button>
          <span aria-hidden="true"> · </span>
          <span>{{ visibilityLabel(community.is_private) }}</span>
        </div>
      </div>
    </ListCell>

    <ListCell class="max-md:hidden">
      <Button
        size="xs"
        variant="ghost"
        :label="spacesLabel"
        icon-right="lucide-arrow-up-right text-ink-gray-5"
        @click="emit('view-spaces', community.name)"
      />
    </ListCell>
    <ListCell class="max-md:hidden">
      <Button
        size="xs"
        variant="ghost"
        :label="membersLabel"
        icon-right="lucide-arrow-up-right text-ink-gray-5"
        @click="emit('view-members', community.name)"
      />
    </ListCell>
    <ListCell class="justify-end gap-1">
      <MembershipButton v-if="showMembershipButton" :community="community" size="sm" />
      <CommunityOptions
        v-if="canManage"
        :community="community"
        @view-spaces="emit('view-spaces', community.name)"
        @view-members="emit('view-members', community.name)"
        @merged="emit('merged', $event)"
      />
    </ListCell>
  </ListRow>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button } from 'frappe-ui'
import { ListCell, ListRow } from 'frappe-ui/list'
import CommunityImage from '@/components/CommunityImage.vue'
import { isCommunityJoined, type Community } from '@/data/communities'
import { useSessionUser } from '@/data/users'
import { canManageCommunity } from '@/utils/permissions'
import { visibilityLabel } from '@/utils/visibility'
import CommunityImageUploader from './CommunityImageUploader.vue'
import CommunityOptions from './CommunityOptions.vue'
import MembershipButton from './MembershipButton.vue'

const props = defineProps<{
  community: Community
  spacesCount: number
}>()

const emit = defineEmits<{
  (event: 'view-spaces', communityId: string): void
  (event: 'view-members', communityId: string): void
  (event: 'merged', communityId: string): void
}>()

const sessionUser = useSessionUser()

const canManage = computed(() => canManageCommunity(props.community, sessionUser))
// An archived community is read-only, and a private one you are not in never reaches
// this list, so the only Join offered is for a public community.
const showMembershipButton = computed(() => {
  if (sessionUser.isGuest || props.community.archived_at) return false
  return isCommunityJoined(props.community) || !props.community.is_private
})

const spacesLabel = computed(() => formatCount(props.spacesCount, 'space'))
const membersLabel = computed(() => formatCount(props.community.members?.length || 0, 'member'))

function formatCount(count: number, label: string) {
  return `${count} ${count === 1 ? label : `${label}s`}`
}
</script>
