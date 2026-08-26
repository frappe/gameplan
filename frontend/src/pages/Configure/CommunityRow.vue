<template>
  <ListRow class="h-10">
    <ListCell class="gap-2">
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
        <div class="mt-1 flex flex-wrap gap-x-2 gap-y-1 text-base text-ink-gray-5 md:hidden">
          <Button
            size="xs"
            variant="ghost"
            :label="spacesLabel"
            icon-right="lucide-arrow-up-right text-ink-gray-5"
            @click="emit('view-spaces', community.name)"
          />
          <Button
            size="xs"
            variant="ghost"
            :label="membersLabel"
            icon-right="lucide-arrow-up-right text-ink-gray-5"
            @click="emit('view-members', community.name)"
          />
          <span class="inline-flex items-center gap-1">
            <span :class="[visibilityIcon(community.is_private), 'size-3.5']" />
            {{ visibilityLabel(community.is_private) }}
          </span>
          <MembershipButton v-if="showMembershipButton" :community="community" size="xs" />
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
    <ListCell class="justify-end gap-1 max-md:hidden">
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
import { visibilityIcon, visibilityLabel } from '@/utils/visibility'
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
