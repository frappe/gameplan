<template>
  <PopoverRoot v-model:open="isOpen">
    <!-- Bottom left, clear of the desktop rail. -->
    <PopoverTrigger as-child>
      <button
        type="button"
        class="fixed bottom-3 left-16 z-[200] flex items-center gap-2 rounded-full border border-outline-gray-2 bg-surface-elevation-2 py-1 pl-1 pr-2.5 shadow-lg transition-opacity hover:opacity-100"
        :class="isOpen ? 'opacity-100' : 'opacity-60'"
        title="Dev only — switch user"
      >
        <UserAvatar :user="sessionUser.name" size="sm" />
        <span class="max-w-32 truncate text-p-sm text-ink-gray-7">
          {{ sessionUser.full_name }}
        </span>
        <span class="lucide-chevrons-up-down size-3.5 shrink-0 text-ink-gray-5" />
      </button>
    </PopoverTrigger>

    <PopoverPortal>
      <PopoverContent
        side="top"
        align="start"
        :side-offset="8"
        :collision-padding="12"
        class="z-[200] outline-none"
        @open-auto-focus.prevent
      >
        <div
          class="flex max-h-[70vh] w-80 max-w-[calc(100vw-1.5rem)] flex-col overflow-hidden rounded-6 bg-surface-elevation-2 shadow-2xl ring-1 ring-outline-gray-2"
          style="transform-origin: var(--reka-popover-content-transform-origin)"
        >
          <div class="flex items-center justify-between gap-2 px-3 pt-3">
            <span class="text-p-sm font-medium text-ink-gray-8">Switch user</span>
            <span class="text-p-xs uppercase tracking-wide text-ink-gray-4">dev only</span>
          </div>

          <DevUserList @close="isOpen = false" />
        </div>
      </PopoverContent>
    </PopoverPortal>
  </PopoverRoot>
</template>

<script setup lang="ts">
/**
 * A floating "become somebody else" control, mounted only by a dev build on a
 * desktop viewport. On mobile the same list opens from the You page instead.
 */
import { ref } from 'vue'
import { PopoverContent, PopoverPortal, PopoverRoot, PopoverTrigger } from 'reka-ui'
import UserAvatar from '@/components/UserAvatar.vue'
import DevUserList from '@/components/DevUserList.vue'
import { useSessionUser } from '@/data/users'

defineOptions({ name: 'DevUserSwitcher' })

const sessionUser = useSessionUser()

const isOpen = ref(false)
</script>
