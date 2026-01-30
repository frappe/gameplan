<template>
  <Teleport to="body">
    <AnimatePresence :initial="false" :onExitComplete="handleExitComplete">
      <div v-if="show" key="bottom-sheet" class="fixed inset-0 z-50">
        <Motion
          class="absolute inset-0 bg-black-overlay-200 dark:bg-black-overlay-700"
          aria-hidden="true"
          :initial="{ opacity: 0 }"
          :animate="{ opacity: 1 }"
          :exit="{ opacity: 0 }"
          @click="show = false"
        />
        <div class="absolute inset-x-0 bottom-0 flex justify-center">
          <Motion
            class="w-full max-w-2xl transform-gpu rounded-t-2xl bg-surface-white shadow-lg [corner-shape:squircle]"
            :initial="{ y: '50%', opacity: 0.5 }"
            :animate="{ y: dragY, opacity: 1 }"
            :exit="{ y: '100%', opacity: 0 }"
            :transition="{ type: 'spring', stiffness: 300, damping: 30 }"
          >
            <div ref="sheetRef">
              <div ref="handleRef" class="flex touch-none justify-center pb-2 pt-3">
                <div class="h-1.5 w-10 rounded-full bg-surface-gray-3" />
              </div>
              <div class="h-[70vh] overflow-y-auto">
                <slot />
              </div>
            </div>
          </Motion>
        </div>
      </div>
    </AnimatePresence>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { AnimatePresence, Motion } from 'motion-v'
import { usePointerSwipe, useScrollLock } from '@vueuse/core'

interface Props {
  modelValue: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'close-complete'): void
}>()

const show = computed({
  get() {
    return props.modelValue
  },
  set(value: boolean) {
    emit('update:modelValue', value)
  },
})

const sheetRef = ref<HTMLElement | null>(null)
const handleRef = ref<HTMLElement | null>(null)
const dragY = ref(0)
const scrollLock = useScrollLock(document.body)

watch(
  () => show.value,
  (value) => {
    scrollLock.value = value
    if (!value) {
      dragY.value = 0
    }
  },
)

const { distanceY, isSwiping } = usePointerSwipe(handleRef, {
  pointerTypes: ['touch'],
  onSwipe() {
    dragY.value = Math.max(0, Math.abs(distanceY.value))
  },
  onSwipeEnd() {
    const shouldClose = distanceY.value > 120
    if (shouldClose) {
      show.value = false
    }
    dragY.value = 0
  },
})

const handleExitComplete = () => {
  emit('close-complete')
}
</script>
