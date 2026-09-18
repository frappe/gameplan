<template>
  <!-- Not a box: the recap is the first section of the inbox, at the list's own width, so
       its rows sit column for column with the day groups below and nothing frames it. -->
  <section aria-label="While you were away">
    <!-- Same height and inset as a day label in the list, so the two read as one family of
         headers; the controls are the list's own mark-as-read buttons. -->
    <div class="flex min-h-10 items-center gap-2 px-4 sm:px-3">
      <button
        type="button"
        class="flex min-w-0 flex-1 items-center gap-2 text-left"
        :aria-expanded="expanded"
        @click="expanded = !expanded"
      >
        <span
          :class="[
            expanded ? 'lucide-chevron-down' : 'lucide-chevron-right',
            'size-4 shrink-0 text-ink-gray-5',
          ]"
          aria-hidden="true"
        />
        <!-- On a phone the summary drops to its own line and wraps instead of being cut
             off after three words; on desktop it stays on the title line. -->
        <span class="min-w-0 py-1.5 sm:py-0">
          <span class="block text-base-medium text-ink-gray-8 sm:inline">While you were away</span>
          <span v-if="!expanded" class="block text-sm text-ink-gray-5 sm:inline sm:text-base">
            <span class="hidden sm:inline">— </span>{{ headline }}
          </span>
        </span>
      </button>
      <!-- The window and the two controls belong to the folded state: open, the rows have
           their own ticks and the header is just a label like the day labels below. -->
      <span
        v-if="!expanded"
        class="hidden shrink-0 whitespace-nowrap text-sm text-ink-gray-5 sm:inline"
      >
        {{ timeWindow }}
      </span>
      <div v-if="!expanded" class="flex shrink-0 items-center gap-1">
        <Tooltip text="Mark all as read">
          <Button
            variant="subtle"
            icon="lucide-check"
            label="Mark all as read"
            :loading="markAwayCardRead.loading"
            @click="markRead"
          />
        </Tooltip>
        <Tooltip text="Dismiss">
          <Button
            variant="subtle"
            icon="lucide-x"
            label="Dismiss"
            :loading="dismissAwayCard.loading"
            @click="dismiss"
          />
        </Tooltip>
      </div>
    </div>

    <!-- The very List the inbox uses, group headers and all, so every measurement matches. -->
    <List v-if="expanded" class="max-sm:list-gap-3 sm:list-gap-4 max-sm:list-row-px-4">
      <ListGroup
        v-for="group in groups"
        :key="group.label"
        :label="group.label"
        class="max-sm:[&>[data-slot=list-group-header]]:px-4 sm:[&>[data-slot=list-group-header]]:px-3"
      >
        <NotificationListRow
          v-for="item in group.items"
          :key="item.name"
          :notification="item"
          :title="item.title"
          @read="emit('read', $event)"
        />
      </ListGroup>
    </List>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useLocalStorage } from '@vueuse/core'
import { Button, dayjsLocal, Tooltip } from 'frappe-ui'
import { List, ListGroup } from 'frappe-ui/list'
import NotificationListRow from '@/components/NotificationListRow.vue'
import { dismissAwayCard, markAwayCardRead, type AwayItem, type AwaySummary } from '@/data/away'

const props = defineProps<{ summary: AwaySummary }>()
const emit = defineEmits<{ (e: 'changed'): void; (e: 'read', name: string): void }>()

// A mention is a person waiting on you, so the card opens itself when there is one.
// The user's own fold/unfold is remembered per period, so it stays put across reloads.
const collapsed = useLocalStorage<boolean | null>(
  `gameplan:awayCardCollapsed:${props.summary.period}`,
  null,
)
const expanded = computed({
  get: () => (collapsed.value === null ? props.summary.mentions.total > 0 : !collapsed.value),
  set: (value: boolean) => (collapsed.value = !value),
})

// Every item is an unread row (the summary only holds unread ones), so the shared row
// draws it the unread way and offers its mark-as-read button.
function unread(items: AwayItem[]) {
  return items.map((item) => ({ ...item, read: 0 as const }))
}

// Everything that arrived, in three groups; nothing is held back behind a "show all".
const groups = computed(() => {
  const { mentions, comments, other } = props.summary
  return [
    { label: 'Mentions', items: unread(mentions.items) },
    { label: 'New comments', items: unread(comments) },
    { label: 'Other', items: unread(other) },
  ].filter((group) => group.items.length)
})

const timeWindow = computed(() => {
  const from = dayjsLocal(props.summary.starts_at)
  const to = dayjsLocal(props.summary.ends_at)
  const sameDay = from.isSame(to, 'day')
  return `${from.format('ddd h:mm a')} – ${to.format(sameDay ? 'h:mm a' : 'ddd h:mm a')}`
})

const headline = computed(() => {
  const parts: string[] = []
  const { mentions, comments, other } = props.summary
  if (mentions.total) parts.push(plural(mentions.total, 'mention'))
  if (comments.length) {
    const count = comments.reduce((sum, item) => sum + (item.event_count || 1), 0)
    parts.push(`${plural(count, 'comment')} in ${plural(comments.length, 'discussion')}`)
  }
  if (other.length) parts.push(`${other.length} more`)
  return parts.join(', ') || plural(props.summary.unread, 'notification')
})

function plural(count: number, one: string) {
  return `${count} ${count === 1 ? one : `${one}s`}`
}

async function markRead() {
  await markAwayCardRead.submit({ period: props.summary.period })
  emit('changed')
}

async function dismiss() {
  await dismissAwayCard.submit({ period: props.summary.period })
  emit('changed')
}
</script>
