<template>
  <div class="flex items-center gap-2">
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
          :active="selectedOptions.length > 0 || filters.communities.length > 0"
          @clear="setSpaces([])"
        />
      </template>
      <template #group-label="{ group }">
        <Checkbox
          size="sm"
          :model-value="isCommunitySelected(group.key)"
          @update:model-value="(checked: boolean) => setCommunitySpaces(group.key, checked)"
        >
          <template #label>
            <span class="text-base-medium text-ink-gray-8">{{ group.group }}</span>
          </template>
        </Checkbox>
      </template>
      <template #item-prefix="{ item }">
        <SpaceIcon :icon="item.icon" class="size-4 text-ink-gray-6" />
      </template>
    </MultiSelect>

    <DateRangePicker :model-value="dateRange" @update:model-value="setDateRange" align="end">
      <template #trigger="{ open, toggle }">
        <FilterTrigger
          :label="dateLabel"
          :open="open"
          :active="filters.date.kind !== 'all'"
          icon="lucide-calendar"
          @click="toggle()"
          @clear="setNotificationDate({ kind: 'all' })"
        />
      </template>
    </DateRangePicker>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Checkbox, DateRangePicker, MultiSelect, dayjs } from 'frappe-ui'
import FilterTrigger from '@/components/NotificationFilterTrigger.vue'
import SpaceIcon from '@/components/SpaceIcon.vue'
import { UNCATEGORIZED, useGroupedSpaces } from '@/data/groupedSpaces'
import {
  notificationDateBounds,
  notificationFilters,
  setNotificationCommunities,
  setNotificationDate,
  setNotificationSpaces,
} from '@/data/notificationFilters'

const filters = notificationFilters

const groupedSpaces = useGroupedSpaces()
const spaceOptions = computed(() =>
  groupedSpaces.value.map((group) => ({
    key: String(group.name),
    group: group.title,
    options: group.spaces.map((space) => ({
      label: space.title,
      value: String(space.name),
      icon: space.icon,
    })),
  })),
)

function communitySpaceIds(community: string | number | undefined) {
  const group = groupedSpaces.value.find((group) => String(group.name) === String(community))
  return group ? group.spaces.map((space) => String(space.name)) : []
}

function isCommunitySelected(community: string | number | undefined) {
  const ids = communitySpaceIds(community)
  return ids.length > 0 && ids.every((id) => filters.value.spaces.includes(id))
}

function setCommunitySpaces(community: string | number | undefined, checked: boolean) {
  const ids = communitySpaceIds(community)
  const others = filters.value.spaces.filter((space) => !ids.includes(space))
  setSpaces(checked ? [...others, ...ids] : others)
}

function setSpaces(values: Array<string | number>) {
  const spaces = values.map(String)
  setNotificationSpaces(spaces)
  setNotificationCommunities(
    groupedSpaces.value
      .filter(
        (group) =>
          group.name !== UNCATEGORIZED &&
          group.spaces.every((space) => spaces.includes(String(space.name))),
      )
      .map((group) => String(group.name)),
  )
}

function triggerLabel(selected: Array<{ label: string }>, none: string, plural: string): string {
  if (selected.length === 0) return none
  if (selected.length === 1) return selected[0].label
  return `${selected.length} ${plural}`
}

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
