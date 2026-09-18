<template>
  <!-- Three triggers that read as one row: each shows what is picked, none scrolls
       sideways. On a phone the parent lets them wrap. -->
  <div class="flex items-center gap-2">
    <MultiSelect
      :options="communityOptions"
      :model-value="filters.communities"
      @update:model-value="setCommunities"
      placeholder="All communities"
    >
      <!-- The anchor toggles the popover itself; the trigger only has to look right. -->
      <template #trigger="{ open, selectedOptions }">
        <FilterTrigger
          :label="triggerLabel(selectedOptions, 'All communities', 'communities')"
          :open="open"
          :active="selectedOptions.length > 0"
        />
      </template>
    </MultiSelect>

    <MultiSelect
      :options="spaceOptions"
      :model-value="filters.spaces"
      @update:model-value="setSpaces"
      placeholder="All spaces"
    >
      <template #trigger="{ open, selectedOptions }">
        <FilterTrigger
          :label="triggerLabel(selectedOptions, 'All spaces', 'spaces')"
          :open="open"
          :active="selectedOptions.length > 0"
        />
      </template>
    </MultiSelect>

    <!-- The stock picker does the whole job: one click opens the calendar, two clicks on
         the same day pick that day, two different days pick a range, and it closes and
         applies as soon as the range is complete. Its own "Today" button covers the
         one-click case. Only the trigger is ours, so a single day reads as one date. -->
    <DateRangePicker :model-value="dateRange" @update:model-value="setDateRange" align="end">
      <!-- Unlike MultiSelect, the picker's trigger slot is a plain anchor: a custom trigger
           opens the calendar by calling the `toggle` it is handed. -->
      <template #trigger="{ open, toggle }">
        <FilterTrigger
          :label="dateLabel"
          :open="open"
          :active="filters.date.kind !== 'all'"
          icon="lucide-calendar"
          @click="toggle()"
        />
      </template>
    </DateRangePicker>

    <!-- Boxed like the filters but muted, so it reads as an action on them, not one of them. -->
    <Button
      v-if="hasActiveNotificationFilters"
      variant="outline"
      label="Clear"
      icon-left="lucide-x"
      class="shrink-0 text-ink-gray-5"
      @click="clearNotificationFilters()"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, DateRangePicker, MultiSelect, dayjs } from 'frappe-ui'
import FilterTrigger from '@/components/NotificationFilterTrigger.vue'
import { activeCommunities } from '@/data/communities'
import { useGroupedSpaces } from '@/data/groupedSpaces'
import {
  clearNotificationFilters,
  hasActiveNotificationFilters,
  notificationDateBounds,
  notificationFilters,
  setNotificationCommunities,
  setNotificationDate,
  setNotificationSpaces,
} from '@/data/notificationFilters'

const filters = notificationFilters

const communityOptions = computed(() =>
  activeCommunities.value.map((community) => ({
    label: community.title,
    value: String(community.name),
  })),
)

// Spaces from every picked community, grouped under their community's name; every
// community when none is picked.
const groupedSpaces = useGroupedSpaces()
const spaceOptions = computed(() => {
  const picked = new Set(filters.value.communities)
  return groupedSpaces.value
    .filter((group) => picked.size === 0 || picked.has(String(group.name)))
    .map((group) => ({
      group: group.title,
      options: group.spaces.map((space) => ({
        label: space.title,
        value: String(space.name),
        icon: space.icon,
      })),
    }))
})

function setCommunities(values: Array<string | number>) {
  const communities = values.map(String)
  setNotificationCommunities(communities)
  // A space filter is scoped to the picked communities, so drop spaces that just left scope.
  if (communities.length) {
    const inScope = new Set(
      groupedSpaces.value
        .filter((group) => communities.includes(String(group.name)))
        .flatMap((group) => group.spaces.map((space) => String(space.name))),
    )
    const spaces = filters.value.spaces.filter((space) => inScope.has(space))
    if (spaces.length !== filters.value.spaces.length) setNotificationSpaces(spaces)
  }
}

function setSpaces(values: Array<string | number>) {
  setNotificationSpaces(values.map(String))
}

function triggerLabel(selected: Array<{ label: string }>, none: string, plural: string): string {
  if (selected.length === 0) return none
  if (selected.length === 1) return selected[0].label
  return `${selected.length} ${plural}`
}

// The picker speaks `[from, to]` (or `[]`); the store keeps a single day as a range whose
// ends match, so the two map onto each other directly.
const dateRange = computed<string[]>(() => {
  const bounds = notificationDateBounds.value
  return bounds ? [bounds[0], bounds[1]] : []
})

function setDateRange(range: string[]) {
  const [from, to] = range
  setNotificationDate(from ? { kind: 'range', from, to: to || from } : { kind: 'all' })
}

const dateLabel = computed(() => {
  const bounds = notificationDateBounds.value
  if (!bounds) return 'All dates'
  // Plain `dayjs`: these are calendar dates, not server timestamps to shift into local time.
  const [from, to] = bounds.map((day) => dayjs(day))
  const thisYear = dayjs().year()
  const withYear = (day: typeof from) =>
    day.format(day.year() === thisYear ? 'D MMM' : 'D MMM YYYY')
  if (bounds[0] === bounds[1]) {
    return from.isSame(dayjs(), 'day') ? 'Today' : withYear(from)
  }
  if (from.isSame(to, 'month')) return `${from.format('D')} – ${withYear(to)}`
  return `${withYear(from)} – ${withYear(to)}`
})
</script>
