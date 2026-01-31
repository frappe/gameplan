<template>
  <Popover placement="right-start" trigger="hover" :hoverDelay="0.1" :leaveDelay="0.1">
    <template #target="{ togglePopover }">
      <button
        :class="[
          active ? 'bg-surface-gray-3' : 'text-ink-gray-6',
          'group flex h-7 w-full items-center justify-between rounded px-2 text-base hover:bg-surface-gray-2',
        ]"
        @click.prevent="togglePopover()"
      >
        <div class="flex gap-2">
          <LucideLayoutGrid class="h-4 w-4" />
          <span class="whitespace-nowrap"> Apps </span>
        </div>
        <LucideChevronRight class="h-4 w-4 text-ink-gray-5" />
      </button>
    </template>
    <template #body>
      <div
        class="mx-2 flex w-fit min-w-32 max-w-48 flex-col rounded-lg border border-outline-gray-2 bg-surface-white p-1.5 text-sm text-ink-gray-8 shadow-xl"
      >
        <a
          v-for="app in apps.data"
          :key="app.name"
          :href="app.route"
          class="flex items-center gap-2 rounded p-1.5 hover:bg-surface-gray-2"
        >
          <img class="h-6 w-6" :src="app.logo" />
          <span class="w-full max-w-[4.5rem] truncate">
            {{ app.title }}
          </span>
        </a>
      </div>
    </template>
  </Popover>
</template>
<script setup>
import { Popover, createResource } from 'frappe-ui'

const props = defineProps({
  active: {
    type: Boolean,
    default: false,
  },
})

const apps = createResource({
  url: 'frappe.apps.get_apps',
  cache: 'apps',
  auto: true,
  transform: (data) => {
    let _apps = [
      {
        name: 'frappe',
        logo: '/assets/frappe/images/framework.png',
        title: 'Desk',
        route: '/app',
      },
    ]
    data.forEach((app) => {
      if (app.name === 'gameplan') return
      _apps.push({
        name: app.name,
        logo: app.logo,
        title: app.title,
        route: app.route,
      })
    })

    return _apps
  },
})
</script>
