<template>
  <div class="flex flex-col gap-6 md:flex-row md:gap-8">
    <nav
      aria-label="Moderation sections"
      class="-mx-4 flex gap-1 overflow-x-auto border-b border-outline-gray-2 px-4 pb-3 md:mx-0 md:w-48 md:shrink-0 md:flex-col md:border-b-0 md:border-r md:px-0 md:pr-4"
    >
      <button
        v-for="option in options"
        :key="option.value"
        type="button"
        class="whitespace-nowrap rounded-5 px-3 py-2 text-left text-base-medium transition-colors"
        :class="
          model === option.value
            ? 'bg-surface-gray-2 text-ink-gray-9'
            : 'text-ink-gray-6 hover:bg-surface-gray-2 hover:text-ink-gray-9'
        "
        :aria-current="model === option.value ? 'page' : undefined"
        @click="model = option.value"
      >
        {{ option.label }}
      </button>
    </nav>
    <section class="min-w-0 flex-1">
      <div
        class="flex flex-wrap items-center justify-between gap-3 border-b border-outline-gray-2 pb-4"
      >
        <h2 class="text-xl-semibold text-ink-gray-9">
          {{ options.find((option) => option.value === model)?.label }}
        </h2>
        <slot name="actions" />
      </div>
      <slot />
    </section>
  </div>
</template>
<script setup lang="ts">
defineProps<{ options: { label: string; value: string }[] }>()
const model = defineModel<string>({ required: true })
</script>
