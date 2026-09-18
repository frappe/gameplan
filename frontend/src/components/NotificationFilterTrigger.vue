<template>
  <!-- One trigger shape for every filter on the notifications page. The root is the
       Button itself so a popover anchor rendered `as-child` binds to a real element. -->
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
  /** True when something is picked, so the trigger reads as "filtered". */
  active?: boolean
  icon?: string
}>()
</script>
