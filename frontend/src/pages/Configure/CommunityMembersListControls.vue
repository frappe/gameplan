<template>
  <div>
    <div class="flex flex-wrap items-center justify-between gap-3">
      <TextInput class="max-md:w-full" v-model="search" placeholder="Search members">
        <template #prefix>
          <span class="lucide-search h-4 w-4 text-ink-gray-4" />
        </template>
      </TextInput>
      <slot name="action" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { TextInput } from 'frappe-ui'

const search = defineModel<string>('search', { default: '' })
</script>
