<template>
  <div class="relative inline-flex">
    <Button
      :variant="active ? 'subtle' : 'outline'"
      :label="label"
      :icon-left="icon"
      :class="{ '[&:has(+button:hover)]:bg-surface-gray-3': active }"
    >
      <template #suffix>
        <span v-if="active" class="size-4" aria-hidden="true" />
        <span
          v-else
          class="lucide-chevron-down size-4 transition-transform"
          :class="{ 'rotate-180': open }"
          aria-hidden="true"
        />
      </template>
    </Button>
    <button
      v-if="active"
      type="button"
      :aria-label="`Clear ${label}`"
      class="absolute right-2 top-1/2 grid size-4 -translate-y-1/2 place-content-center rounded-sm text-ink-gray-8"
      @click.stop="emit('clear')"
    >
      <span class="lucide-x size-4" aria-hidden="true" />
    </button>
  </div>
</template>

<script setup lang="ts">
import { Button } from 'frappe-ui'

defineProps<{
  label: string
  open?: boolean
  active?: boolean
  icon?: string
}>()

const emit = defineEmits<{ (e: 'clear'): void }>()
</script>
