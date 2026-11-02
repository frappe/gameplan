<template>
  <Dialog v-model:open="open" :title="title" size="6xl" bare :dismissible="!busy">
    <div class="flex h-[48rem] max-h-[calc(100dvh-4rem)] flex-col text-ink-gray-9">
      <header
        class="flex shrink-0 items-center justify-between gap-4 border-b border-outline-gray-2 px-5 py-4"
      >
        <DialogTitle as="h2" class="text-xl-semibold">{{ title }}</DialogTitle>
        <Button variant="ghost" aria-label="Close review" :disabled="busy" @click="open = false"
          ><span class="lucide-x size-4 text-ink-gray-9"
        /></Button>
      </header>
      <div class="flex min-h-0 flex-1 flex-col md:flex-row">
        <aside
          v-if="$slots.sidebar"
          class="max-h-[35vh] shrink-0 overflow-y-auto border-b border-outline-gray-2 bg-surface-gray-1 p-5 md:order-last md:max-h-none md:w-80 md:border-b-0 md:border-l"
        >
          <slot name="sidebar" />
        </aside>
        <main
          class="min-h-0 min-w-0 flex-1 overflow-y-auto p-5 sm:p-6"
          data-testid="review-content"
        >
          <slot />
        </main>
      </div>
      <footer
        v-if="$slots.actions"
        class="flex shrink-0 flex-wrap items-center justify-end gap-2 border-t border-outline-gray-2 bg-surface-gray-1 px-5 py-4"
      >
        <slot name="actions" />
      </footer>
    </div>
  </Dialog>
</template>
<script setup lang="ts">
import { Button, Dialog } from 'frappe-ui'
import { DialogTitle } from 'reka-ui'
defineProps<{ title: string; busy?: boolean }>()
const open = defineModel<boolean>('open', { default: false })
</script>
