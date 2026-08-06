<template>
  <Popover :side="side" :align="align">
    <template #trigger="triggerProps">
      <slot name="trigger" v-bind="triggerProps">
        <button type="button">
          <span class="text-base">{{ modelValue || '' }}</span>
        </button>
      </slot>
    </template>
    <!-- shell (bg, radius, shadow, ring) is provided by Popover's PopoverPanel -->
    <template #default="{ close }">
      <EmojiPickerPanel class="h-96 w-96" @select="selectEmoji($event, close)">
        <template #actions>
          <Button @click="setRandom">Random</Button>
        </template>
      </EmojiPickerPanel>
    </template>
  </Popover>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { Button, Popover } from 'frappe-ui'
import EmojiPickerPanel from '@/components/EmojiPickerPanel.vue'
import { randomEmoji } from '@/utils/emoji'

const props = withDefaults(
  defineProps<{
    modelValue?: string
    setDefault?: boolean
    side?: 'top' | 'right' | 'bottom' | 'left'
    align?: 'start' | 'center' | 'end'
  }>(),
  {
    modelValue: '',
    side: 'top',
    align: 'center',
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
  select: [value: string]
}>()

onMounted(() => {
  if (props.setDefault && !props.modelValue) setRandom()
})

function selectEmoji(value: string, close?: () => void) {
  emit('update:modelValue', value)
  emit('select', value)
  close?.()
}

function setRandom() {
  selectEmoji(randomEmoji())
}

defineExpose({ setRandom })
</script>
