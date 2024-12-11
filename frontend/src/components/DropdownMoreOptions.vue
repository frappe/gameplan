<template>
  <Dropdown v-bind="$attrs">
    <template #default="{ open }">
      <Button :variant="open ? 'subtle' : 'ghost'">
        <template #icon>
          <LucideMoreHorizontal class="h-4 w-4 text-ink-gray-6" />
        </template>
      </Button>
    </template>
  </Dropdown>
</template>
<script setup lang="ts">
import { Button, Dropdown } from 'frappe-ui'
import LucideMoreHorizontal from '~icons/lucide/more-horizontal'
</script>
