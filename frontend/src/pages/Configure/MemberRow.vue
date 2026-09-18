<template>
  <!-- Phones draw a second line of details under the name, so the row grows to fit;
       desktop keeps its one-line 40px. -->
  <ListRow class="max-md:h-auto max-md:py-3 md:h-10">
    <!-- The link spans only the info cells (display: contents keeps them grid
         children); the options cell stays outside so its menu isn't a nested
         interactive element inside an anchor. -->
    <RouterLink :to="profileRoute" class="contents">
      <ListCell>
        <UserAvatar :user="member.user" size="sm" class="shrink-0" />
      </ListCell>

      <ListCell>
        <div class="min-w-0">
          <div class="truncate text-base-medium text-ink-gray-7">
            {{ user.full_name }}
          </div>
          <div class="mt-0.5 truncate text-sm text-ink-gray-5 md:hidden">
            {{ [roleLabel, user.email].filter(Boolean).join(' · ') }}
          </div>
        </div>
      </ListCell>

      <ListCell class="max-md:hidden">
        <div class="w-full truncate text-base text-ink-gray-5">{{ user.email }}</div>
      </ListCell>
      <ListCell class="text-base text-ink-gray-5 max-md:hidden">
        {{ roleLabel }}
      </ListCell>
    </RouterLink>

    <ListCell class="justify-end">
      <MemberOptions
        v-if="canManage"
        :community="community"
        :member="member"
        :can-manage="canManage"
      />
    </ListCell>
  </ListRow>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ListCell, ListRow } from 'frappe-ui/list'
import UserAvatar from '@/components/UserAvatar.vue'
import { useUser } from '@/data/users'
import type { Community, CommunityMember } from '@/data/communities'
import MemberOptions from './MemberOptions.vue'

const props = defineProps<{
  community: Community
  member: CommunityMember
  canManage: boolean
}>()

const user = computed(() => useUser(props.member.user))
const roleLabel = computed(() => (props.member.is_admin ? 'Community Admin' : 'Member'))
const profileRoute = computed(() => {
  return user.value.user_profile
    ? { name: 'PersonProfileProfile', params: { personId: user.value.user_profile } }
    : { name: 'People' }
})
</script>
