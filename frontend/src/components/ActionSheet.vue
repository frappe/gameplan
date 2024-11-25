<template>
  <div
    class="fixed inset-0 bg-black-overlay-100 z-50 flex flex-col justify-end"
    @click.self="emit('update:modelValue', false)"
    v-if="modelValue"
  >
    <div
      v-if="modelValue"
      class="bg-surface-white max-h-screen overflow-auto shadow-lg w-full rounded-t-xl slide-in-from-bottom"
    >
      <div class="py-4 border-b text-center relative">
        <div class="text-lg font-bold">
          {{ title }}
        </div>
        <div class="absolute right-0 inset-y-0 flex items-center pr-4">
          <Button variant="ghost" @click="emit('update:modelValue', false)">
            <template #icon>
              <LucideX class="text-ink-gray-5" />
            </template>
          </Button>
        </div>
      </div>
      <div>
        <slot />
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
const props = defineProps<{
  modelValue: boolean
  title
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
}>()
</script>
<style scoped>
@keyframes slide-in-from-bottom {
  from {
    transform: translateY(100%);
  }
  to {
    transform: translateY(0);
  }
}

.slide-in-from-bottom {
  animation: slide-in-from-bottom 0.3s cubic-bezier(0.25, 0.1, 0.25, 1);
}
</style>
