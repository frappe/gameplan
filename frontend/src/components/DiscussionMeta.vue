<template>
  <div class="leading-5">
    <span class="text-base text-ink-gray-7">
      <UserProfileLink class="hover:text-ink-blue-4" :user="discussion.owner">
        {{ $user(discussion.owner).full_name }}
      </UserProfileLink>
      in
      <DiscussionBreadcrumbs :discussion="discussion" />
    </span>
    <span> &middot; </span>
    <span class="text-base text-ink-gray-5">
      {{
        discussion.participants_count == 1
          ? `1 participant`
          : `${discussion.participants_count} participants`
      }}
    </span>
  </div>
</template>
<script>
import DiscussionBreadcrumbs from './DiscussionBreadcrumbs.vue'
import UserProfileLink from './UserProfileLink.vue'

export default {
  name: 'DiscussionMeta',
  props: ['discussion'],
  components: { UserProfileLink, DiscussionBreadcrumbs },
}
</script>
