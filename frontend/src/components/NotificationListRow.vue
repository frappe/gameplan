<template>
  <ListRow
    :to="route ?? undefined"
    class="group h-[68px] sm:h-15"
    :class="!notification.read && 'w-[calc(100%-3rem)] sm:w-[calc(100%-2rem)]'"
    @click="open"
  >
    <ListCell>
      <UserAvatarWithHover size="2xl" :user="notification.from_user!" v-if="showAvatar" />
      <div
        class="grid size-10 place-items-center rounded-[8px] bg-surface-gray-2 group-hover:bg-surface-base"
        v-else
      >
        <ReactionFaceIcon class="size-5 text-ink-gray-6" v-if="notification.type === 'Reaction'" />
        <span
          :class="[notificationIcon(notification), 'size-5 text-ink-gray-6']"
          aria-hidden="true"
          v-else
        />
      </div>
    </ListCell>
    <ListCell>
      <div class="min-w-0 flex-1">
        <div class="flex min-w-0 items-center">
          <div class="overflow-hidden text-ellipsis whitespace-nowrap leading-none text-ink-gray-8">
            <span
              class="overflow-hidden text-ellipsis whitespace-nowrap"
              :class="
                notification.read ? 'text-lg sm:text-base' : 'text-lg-medium sm:text-base-medium'
              "
            >
              {{ notification.message }}
            </span>
          </div>
        </div>

        <div class="mt-1.5 flex min-w-0 items-center justify-between">
          <div
            class="inline-flex items-center overflow-hidden text-ellipsis whitespace-nowrap text-md text-ink-gray-5 sm:text-base"
          >
            <div class="flex min-w-0 items-center" v-if="title">
              <div class="truncate">{{ title }}</div>
            </div>
          </div>
        </div>
      </div>
    </ListCell>
    <ListCell class="justify-end">
      <div>
        <time
          class="block shrink-0 whitespace-nowrap text-right text-sm text-ink-gray-5"
          :datetime="notification.last_event_at"
        >
          {{ dayjsLocal(notification.last_event_at).format('h:mm a') }}
        </time>
        <div
          class="mt-1.5 hidden whitespace-nowrap text-right text-sm text-ink-gray-5 sm:block"
          v-if="location"
        >
          {{ location }}
        </div>
      </div>
    </ListCell>
    <div class="absolute -right-8 top-1/2 z-10 -translate-y-1/2" v-if="!notification.read">
      <Tooltip text="Mark as read">
        <Button
          variant="subtle"
          icon="lucide-check"
          @click.stop.prevent="emit('read', notification.name)"
        />
      </Tooltip>
    </div>
  </ListRow>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, dayjsLocal, Tooltip } from 'frappe-ui'
import { ListRow, ListCell } from 'frappe-ui/list'
import ReactionFaceIcon from '@/components/ReactionFaceIcon.vue'
import UserAvatarWithHover from '@/components/UserAvatarWithHover.vue'
import {
  notificationIcon,
  notificationLocation,
  notificationRoute,
  type NotificationRow,
} from '@/data/notifications'

const props = defineProps<{
  notification: NotificationRow
  title?: string | null
}>()
const emit = defineEmits<{ (e: 'read', name: string): void }>()

const route = computed(() => notificationRoute(props.notification))
const location = computed(() => notificationLocation(props.notification))
// A sender's face, unless it is a reaction (the emoji glyph) or a merged row that no
// longer belongs to one sender.
const showAvatar = computed(() =>
  Boolean(props.notification.from_user && props.notification.type !== 'Reaction'),
)

// Opening an unread row reads it; the row's own link does the navigation.
function open() {
  if (!props.notification.read && route.value) emit('read', props.notification.name)
}
</script>
