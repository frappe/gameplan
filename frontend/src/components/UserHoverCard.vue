<template>
  <slot v-if="userData.name == '_everyone_'" />
  <HoverCardRoot v-model:open="userCardOpen" v-else>
    <HoverCardTrigger asChild>
      <slot />
    </HoverCardTrigger>
    <HoverCardPortal>
      <HoverCardContent side="top" class="z-50 w-66">
        <HoverCardArrow class="fill-surface-white" />
        <div class="bg-surface-white p-3 rounded-lg shadow-2xl">
          <div class="flex items-center gap-2.5">
            <div>
              <div class="font-medium text-base text-ink-gray-8">
                {{ userData.full_name }}
              </div>
            </div>
          </div>
          <div class="mt-0.5 text-p-sm text-ink-gray-6">{{ userData.bio }}</div>
          <div class="text-p-xs text-ink-gray-6 mt-2">
            {{ userData.discussions_count_3m }}
            {{ pluralize(userData.discussions_count_3m, 'post', 'posts') }},
            {{ userData.comments_count_3m }}
            {{ pluralize(userData.comments_count_3m, 'reply', 'replies') }} in the last 3 months
          </div>
        </div>
      </HoverCardContent>
    </HoverCardPortal>
  </HoverCardRoot>
</template>

<script setup lang="ts">
import { useUser } from '@/data/users'
import {
  HoverCardRoot,
  HoverCardPortal,
  HoverCardTrigger,
  HoverCardContent,
  HoverCardArrow,
} from 'reka-ui'
import { ref } from 'vue'

defineOptions({
  inheritAttrs: false,
})

const props = defineProps({
  user: {
    type: String,
    required: true,
  },
})

const userData = useUser(props.user)

function pluralize(count: number, singular: string, plural: string) {
  return count === 1 ? singular : plural
}

const userCardOpen = ref(false)
</script>
