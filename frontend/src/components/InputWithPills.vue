<template>
  <div
    class="form-input flex w-full cursor-text flex-wrap items-center px-3"
    :class="modelValue.length > 0 ? 'py-3' : 'py-2'"
    @click="focusInput"
  >
    <div class="flex w-full flex-wrap items-center gap-1">
      <div
        class="inline-flex items-center whitespace-nowrap rounded-full border py-1 pl-2.5 pr-1 text-sm leading-none"
        v-for="option in modelValue"
        :key="option.value"
        :class="
          focusedOption === option ? 'bg-surface-white ring-2 ring-blue-600' : 'bg-surface-white'
        "
      >
        {{ option.displayValue || option.label }}

        <button class="ml-1 rounded-full p-1 hover:bg-surface-gray-2" @click="removeOption(option)">
          <LucideX class="h-3 w-3" />
        </button>
      </div>
      <Combobox v-model="selectedValue">
        <div class="relative ml-1">
          <Popover :show="true">
            <template #target>
              <ComboboxInput
                class="w-full border-none bg-transparent p-0 text-base focus:ring-0"
                ref="input"
                :placeholder="placeholder"
                :value="query"
                @input="query = $event.target.value"
                @keydown="handleKeyDown"
                autocomplete="none"
              />
            </template>
            <template #body>
              <TransitionRoot
                leave="transition ease-in duration-100"
                leaveFrom="opacity-100"
                leaveTo="opacity-0"
                @after-leave="query = ''"
              >
                <ComboboxOptions
                  class="mt-1 max-h-60 w-full overflow-auto rounded-md bg-surface-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm"
                >
                  <div
                    v-if="filteredOptions.length === 0"
                    class="relative cursor-default select-none px-4 py-2 text-ink-gray-6"
                  >
                    No user found.
                  </div>
                  <ComboboxOption
                    v-for="option in filteredOptions"
                    as="template"
                    :key="option.value"
                    :value="option"
                    v-slot="{ selected, active }"
                  >
                    <li
                      class="relative cursor-default select-none px-3 py-2"
                      :class="{
                        'bg-blue-500 text-ink-white': active,
                        'text-ink-gray-8': !active,
                      }"
                    >
                      <span
                        class="block truncate"
                        :class="{
                          'font-medium': selected,
                          'font-normal': !selected,
                        }"
                      >
                        {{ option.label }}
                      </span>
                    </li>
                  </ComboboxOption>
                </ComboboxOptions>
              </TransitionRoot>
            </template>
          </Popover>
        </div>
      </Combobox>
    </div>
  </div>
</template>
<script>
import {
  Combobox,
  ComboboxInput,
  ComboboxOptions,
  ComboboxOption,
  TransitionRoot,
} from '@headlessui/vue'
import Popover from 'frappe-ui/src/components/Popover.vue'

export default {
  name: 'InputWithPills',
  components: {
    Combobox,
    ComboboxInput,
    ComboboxOptions,
    ComboboxOption,
    TransitionRoot,
    Popover,
  },
  props: ['options', 'placeholder', 'modelValue'],
  emits: ['update:modelValue'],
  data() {
    return {
      query: '',
      selectedValue: null,
      focusedOption: null,
    }
  },
  watch: {
    selectedValue: {
      immediate: true,
      handler(val) {
        if (val === null) return
        if (val.onSelect) {
          val.onSelect()
          return
        }
        if (!this.modelValue.includes(val)) {
          let newValue = [...this.modelValue, val]
          this.$emit('update:modelValue', newValue)
          this.$nextTick(() => {
            this.query = ''
          })
        }
      },
    },
  },
  computed: {
    filteredOptions() {
      if (typeof this.options === 'function') {
        return this.options({ query: this.query })
      }
      return this.query === ''
        ? this.options
        : this.options.filter((option) =>
            option.label
              .toLowerCase()
              .replace(/\s+/g, '')
              .includes(this.query.toLowerCase().replace(/\s+/g, '')),
          )
    },
  },
  methods: {
    handleKeyDown(e) {
      if (e.key === 'Backspace') {
        if (this.focusedOption) {
          this.removeOption(this.focusedOption)
          this.focusedOption = null
          return
        }
        if (e.target.value === '') {
          this.focusedOption = this.modelValue[this.modelValue.length - 1]
          return
        }
      }
      this.focusedOption = null
    },
    removeOption(_option) {
      this.$emit(
        'update:modelValue',
        this.modelValue.filter((option) => option !== _option),
      )
    },
    focusInput() {
      this.$refs.input.$el.focus()
    },
  },
}
</script>
