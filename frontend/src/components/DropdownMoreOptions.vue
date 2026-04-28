<template>
  <Dropdown v-bind="$attrs">
    <template #default="{ open }">
      <Button :label="label" :variant="open ? 'subtle' : 'ghost'">
        <template #icon>
          <span class="lucide-more-horizontal h-4 w-4 text-ink-gray-6" />
        </template>
      </Button>
    </template>
  </Dropdown>
</template>
<script setup lang="ts">
import { Button, Dropdown } from 'frappe-ui'
defineOptions({
  inheritAttrs: false,
})

defineProps<{
  label?: string
}>()
</script>
