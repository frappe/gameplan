<template>
  <Dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    :options="{
      title: 'Configure Home Page',
      actions: [
        {
          label: 'Save',
          variant: 'solid',
          onClick: saveSelection,
        },
      ],
    }"
  >
    <template #body-content>
      <div class="space-y-2">
        <p class="text-ink-gray-7 text-base">Select the default page when you click on Home.</p>

        <RadioGroupRoot class="space-y-1" v-model="selectedHomePage">
          <RadioGroupItem
            v-for="option in homePageOptions"
            :key="option.name"
            :value="option.name"
            class="flex items-start w-full group data-[state=checked]:bg-surface-gray-2 p-2 rounded-md cursor-pointer hover:bg-surface-gray-1"
          >
            <div
              class="size-4 border border-outline-gray-2 group-data-[state=checked]:bg-surface-gray-7 rounded-full grid place-content-center"
            >
              <RadioGroupIndicator>
                <CircleCheck class="text-ink-white size-4.5" />
              </RadioGroupIndicator>
            </div>
            <div class="ml-2 text-left">
              <div class="text-base text-ink-gray-9 font-">{{ option.name }}</div>
              <div class="text-ink-gray-6 mt-1 text-sm">{{ option.description }}</div>
            </div>
          </RadioGroupItem>
        </RadioGroupRoot>
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Dialog, Select } from 'frappe-ui'
import { RadioGroupRoot, RadioGroupItem, RadioGroupIndicator } from 'reka-ui'
import { useLocalStorage } from '@vueuse/core'
import { useRouter } from 'vue-router'
import CircleCheck from 'frappe-ui/src/icons/CircleCheck.vue'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
}>()

const preferredHomePage = useLocalStorage('preferredHomePage', 'Discussions')
const selectedHomePage = ref(preferredHomePage.value)

const homePageOptions = [
  { name: 'Discussions', routeName: 'Discussions', description: 'View all discussions.' },
  { name: 'Spaces', routeName: 'Spaces', description: 'Browse your spaces.' },
]

const router = useRouter()

watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue) {
      selectedHomePage.value = preferredHomePage.value
    }
  },
)

function saveSelection() {
  preferredHomePage.value = selectedHomePage.value
  router.push({ name: selectedHomePage.value })
  emit('update:modelValue', false)
}
</script>
