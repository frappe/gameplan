<template>
  <Teleport to="body">
    <Transition name="action-sheet-overlay">
      <div
        class="fixed inset-0 bg-black-overlay-100 z-50 flex flex-col justify-end"
        @click.self="emit('update:modelValue', false)"
        v-show="modelValue"
      >
        <Transition name="action-sheet-panel">
          <div
            v-show="modelValue"
            class="bg-surface-white max-h-screen overflow-auto shadow-lg w-full rounded-t-xl"
          >
            <div class="py-4 border-b text-center relative">
              <div class="text-lg font-bold">
                {{ title }}
              </div>
              <div class="absolute right-0 inset-y-0 flex items-center pr-4">
                <Button variant="ghost" @click="emit('update:modelValue', false)">
                  <template #icon>
                    <span class="lucide-x text-ink-gray-5" />
                  </template>
                </Button>
              </div>
            </div>
            <div>
              <slot />
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>
<script setup lang="ts">
const props = defineProps<{
  modelValue: boolean
  title: string
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
}>()
</script>
<style scoped>
.action-sheet-overlay-enter-active {
  transition: opacity 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.action-sheet-overlay-leave-active {
  transition: opacity 0.2s cubic-bezier(0.4, 0, 1, 1);
}

.action-sheet-overlay-enter-from,
.action-sheet-overlay-leave-to {
  opacity: 0;
}

.action-sheet-panel-enter-active {
  transition:
    transform 0.35s cubic-bezier(0.22, 1, 0.36, 1),
    opacity 0.35s cubic-bezier(0.22, 1, 0.36, 1);
}

.action-sheet-panel-leave-active {
  transition:
    transform 0.28s cubic-bezier(0.4, 0, 1, 1),
    opacity 0.2s cubic-bezier(0.4, 0, 1, 1);
}

.action-sheet-panel-enter-from,
.action-sheet-panel-leave-to {
  transform: translateY(100%);
  opacity: 0;
}

.action-sheet-panel-enter-to,
.action-sheet-panel-leave-from {
  transform: translateY(0);
  opacity: 1;
}
</style>
