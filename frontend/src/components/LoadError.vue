<template>
  <EmptyStateBox icon="lucide-cloud-alert" :description="message" role="alert">
    <Button
      class="mt-4"
      variant="subtle"
      icon-left="lucide-rotate-ccw"
      label="Retry"
      @click="emit('retry')"
    />
  </EmptyStateBox>
</template>

<script setup lang="ts">
// Stands in for content whose first load failed. Pass `message` through `errorText`.
import { Button } from 'frappe-ui'
import EmptyStateBox from './EmptyStateBox.vue'

defineProps<{
  message: string
}>()

const emit = defineEmits<{ retry: [] }>()
</script>
