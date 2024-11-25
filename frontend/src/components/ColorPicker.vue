<template>
  <Popover transition="default">
    <template #target="{ togglePopover, isOpen }">
      <button @click="togglePopover()">
        <slot v-bind="{ isOpen }">
          <span class="text-base"> {{ modelValue || '' }} </span>
        </slot>
      </button>
    </template>
    <template #body>
      <div class="left-1/2 mt-3 max-w-max -translate-x-1/2 transform bg-surface-white px-4 sm:px-0">
        <div
          class="relative max-h-96 overflow-y-auto rounded-lg p-2 shadow-lg ring-1 ring-black ring-opacity-5"
        >
          <div class="grid grid-cols-10 place-items-center gap-1">
            <button
              class="h-4 w-4 rounded-full"
              :style="{ backgroundColor: color }"
              v-for="color in colors"
              :key="color"
              @click="$emit('update:modelValue', color)"
              :title="color"
            >
              &nbsp;
            </button>
          </div>
        </div>
      </div>
    </template>
  </Popover>
</template>
<script>
import { Popover } from 'frappe-ui'
import { theme } from '@/utils/theme'
import { getRandomNumber } from '@/utils'

export default {
  name: 'ColorPicker',
  props: ['modelValue'],
  emits: ['update:modelValue'],
  components: {
    Popover,
  },
  computed: {
    colors() {
      let colors = getAllColors()
      return [
        ...colors.gray,
        ...colors.red,
        ...colors.orange,
        ...colors.yellow,
        ...colors.green,
        ...colors.blue,
        ...colors.purple,
        ...colors.pink,
      ]
    },
  },
}

export function getColors(name) {
  return Object.keys(theme.colors[name]).map((key) => theme.colors[name][key])
}

function getAllColors() {
  return {
    gray: getColors('gray'),
    red: getColors('red'),
    orange: getColors('orange'),
    yellow: getColors('yellow'),
    green: getColors('green'),
    blue: getColors('blue'),
    purple: getColors('purple'),
    pink: getColors('pink'),
  }
}

export function getRandomColor() {
  const colorNames = ['gray', 'red', 'orange', 'yellow', 'green', 'blue', 'purple', 'pink']
  const colorName = colorNames[getRandomNumber(0, colorNames.length - 1)]
  return getAllColors()[colorName][2]
}
</script>
