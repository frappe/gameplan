<template>
  <div
    class="fixed inset-0 bg-black-overlay-100 z-50 flex flex-col justify-end"
    @click.self="emit('update:modelValue', false)"
    v-if="modelValue"
  >
    <div v-if="modelValue" class="bg-white shadow-lg w-full rounded-t-xl slide-in-from-bottom">
      <div class="py-4 text-lg font-bold border-b text-center">{{ title }}</div>
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
  'update:modelValue': (value: boolean) => void
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
