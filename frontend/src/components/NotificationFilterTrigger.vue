<template>
  <Button :variant="active ? 'subtle' : 'outline'" :label="label" :icon-left="icon">
    <template #suffix>
      <span
        class="lucide-chevron-down size-4 transition-transform"
        :class="{ 'rotate-180': open }"
        aria-hidden="true"
      />
    </template>
  </Button>
</template>

<script setup lang="ts">
import { Button } from 'frappe-ui'

defineProps<{
  label: string
  open?: boolean
  active?: boolean
  icon?: string
}>()
</script>
