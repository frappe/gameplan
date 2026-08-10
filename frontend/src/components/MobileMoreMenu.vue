<template>
  <div class="min-h-full bg-surface-gray-1 px-4 pt-8 pb-28">
    <div class="flex flex-col items-center text-center">
      <div
        v-if="sessionUser.name"
        class="flex size-[120px] items-center justify-center overflow-hidden rounded-full bg-surface-gray-3 text-5xl-semibold text-ink-gray-7 shadow-sm"
        :style="avatarStyle"
      >
        <img
          v-if="sessionUser.user_image"
          :src="sessionUser.user_image"
          :alt="`${sessionUser.full_name}'s profile photo`"
          class="size-full object-cover"
        />
        <span v-else>{{ userInitials }}</span>
      </div>
      <div class="mt-5 max-w-full truncate text-5xl-semibold text-ink-gray-9">
        {{ sessionUser.full_name }}
      </div>
      <p v-if="userBio" class="max-w-sm text-p-lg text-ink-gray-6">
        {{ userBio }}
      </p>
      <Button variant="ghost" size="lg" class="mt-2" @click="openProfile"> View profile </Button>
    </div>

    <div class="mt-8 space-y-6">
      <section v-for="group in itemGroups" :key="group.label">
        <div class="mb-2 pl-[18px] text-lg-medium text-ink-gray-5">
          {{ group.label }}
        </div>
        <nav class="overflow-hidden rounded-7 bg-surface-base">
          <button
            v-for="(item, index) in group.items"
            :key="item.label"
            type="button"
            class="flex min-h-14 w-full text-left transition active:bg-surface-gray-2"
            @click="onItemClick(item)"
          >
            <span class="flex w-14 shrink-0 items-center justify-center py-3">
              <span :class="[item.icon, 'size-5 text-ink-gray-8']" aria-hidden="true" />
            </span>
            <span class="relative flex min-w-0 flex-1 items-center gap-3 py-3 pr-4">
              <span
                v-if="index > 0"
                class="pointer-events-none absolute left-0 right-4 top-0 border-t"
                aria-hidden="true"
              />
              <span class="min-w-0 flex-1 truncate text-lg text-ink-gray-9">
                {{ item.label }}
              </span>
              <span v-if="item.value" class="shrink-0 text-md text-ink-gray-5">
                {{ item.value }}
              </span>
              <span class="size-4 shrink-0 text-ink-gray-4 lucide-chevron-right" />
            </span>
          </button>
        </nav>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, type RouteLocationRaw } from 'vue-router'
import { useSessionUser } from '@/data/users'
import { session } from '@/data/session'
import { useTheme, type Theme } from '@/utils/useTheme'

interface MoreItem {
  label: string
  icon: string
  route?: RouteLocationRaw
  onClick?: () => void
  value?: string
}

interface MoreItemGroup {
  label: string
  items: MoreItem[]
}

const router = useRouter()
const sessionUser = useSessionUser()
const { cycleTheme, currentTheme } = useTheme()

const THEME_META: Record<Theme, { label: string; icon: string }> = {
  light: { label: 'Light', icon: 'lucide-sun' },
  dark: { label: 'Dark', icon: 'lucide-moon' },
  system: { label: 'System Default', icon: 'lucide-monitor-smartphone' },
}

const userInitials = computed(() => {
  return (sessionUser.full_name || sessionUser.name)
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
})
const avatarStyle = computed(() => ({
  backgroundColor: sessionUser.image_background_color || undefined,
}))
const userBio = computed(() => sessionUser.bio?.trim())

const itemGroups = computed<MoreItemGroup[]>(() => {
  const workspaceItems: MoreItem[] = [
    { label: 'Drafts', icon: 'lucide-pencil-line', route: { name: 'Drafts' } },
    { label: 'Bookmarks', icon: 'lucide-bookmark', route: { name: 'Bookmarks' } },
    { label: 'Pages', icon: 'lucide-files', route: { name: 'MyPages' } },
    { label: 'Tasks', icon: 'lucide-list-todo', route: { name: 'MyTasks' } },
    { label: 'People', icon: 'lucide-users-2', route: { name: 'People' } },
  ]

  return [
    {
      label: '',
      items: workspaceItems,
    },
    {
      label: 'Settings',
      items: [
        { label: 'Profile', icon: 'lucide-user', onClick: openProfile },
        {
          label: 'Theme',
          icon: THEME_META[currentTheme.value].icon,
          onClick: cycleTheme,
          value: THEME_META[currentTheme.value].label,
        },
        { label: 'Log out', icon: 'lucide-log-out', onClick: () => session.logout.submit() },
      ],
    },
  ]
})

function onItemClick(item: MoreItem) {
  if (item.onClick) {
    item.onClick()
    return
  }

  if (item.route) {
    router.push(item.route)
  }
}

function openProfile() {
  if (!sessionUser.user_profile) return
  router.push({ name: 'PersonProfileProfile', params: { personId: sessionUser.user_profile } })
}
</script>
