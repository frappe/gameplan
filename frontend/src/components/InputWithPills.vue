<template>
  <div
    class="flex flex-wrap items-center w-full px-3 form-input cursor-text"
    :class="modelValue.length > 0 ? 'py-3' : 'py-2'"
    @click="focusInput"
  >
    <div class="flex flex-wrap items-center w-full gap-1">
      <div
        class="inline-flex items-center pl-2.5 pr-1 py-1 text-sm leading-none whitespace-nowrap rounded-full border"
        v-for="option in modelValue"
        :key="option.value"
        :class="
          focusedOption === option
            ? 'ring-2 ring-blue-600 bg-white'
            : 'bg-white'
        "
      >
        {{ option.displayValue || option.label }}

        <button
          class="p-1 ml-1 rounded-full hover:bg-gray-100"
          @click="removeOption(option)"
        >
          <FeatherIcon class="w-3" name="x" />
        </button>
      </div>
      <Combobox v-model="selectedValue">
        <div class="relative ml-1">
          <Popover :show="true">
            <template #target>
              <ComboboxInput
                class="w-full p-0 text-base bg-transparent border-none focus:ring-0"
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
                  class="w-full py-1 mt-1 overflow-auto text-base bg-white rounded-md shadow-lg max-h-60 ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm"
                >
                  <div
                    v-if="filteredOptions.length === 0"
                    class="relative px-4 py-2 text-gray-700 cursor-default select-none"
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
                      class="relative px-3 py-2 cursor-default select-none"
                      :class="{
                        'text-white bg-blue-500': active,
                        'text-gray-900': !active,
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
              .includes(this.query.toLowerCase().replace(/\s+/g, ''))
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
        this.modelValue.filter((option) => option !== _option)
      )
    },
    focusInput() {
      this.$refs.input.$el.focus()
    },
  },
}
</script>
