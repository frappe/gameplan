<template>
  <Popover v-slot="{ open }" class="relative">
    <PopoverButton>
      <slot :open="open">
        <span class="text-base"> {{ modelValue || '' }} </span>
      </slot>
    </PopoverButton>
    <transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="translate-y-1 opacity-0"
      enter-to-class="translate-y-0 opacity-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="translate-y-0 opacity-100"
      leave-to-class="translate-y-1 opacity-0"
    >
      <PopoverPanel
        class="absolute z-10 px-4 mt-3 transform -translate-x-1/2 bg-white max-w-max left-1/2 sm:px-0"
      >
        <div
          class="relative overflow-y-auto rounded-lg shadow-lg max-h-96 ring-1 ring-black ring-opacity-5"
        >
          <div class="flex gap-2 px-3 pt-3 pb-1">
            <div class="flex-1">
              <Input
                type="text"
                placeholder="Search by keyword"
                :value="search"
                @input="setSearch"
              />
            </div>
            <Button @click="setRandom">Random</Button>
          </div>
          <div class="w-96"></div>
          <div class="px-3" v-for="(emojis, group) in emojiGroups" :key="group">
            <div class="sticky top-0 pt-3 pb-2 text-sm text-gray-700 bg-white">
              {{ group }}
            </div>
            <div class="grid grid-cols-12 place-items-center w-96">
              <button
                class="w-8 h-8 p-1 text-2xl rounded-md focus:outline-none focus:ring focus:ring-blue-200 hover:bg-gray-100"
                v-for="emoji in emojis"
                :key="emoji.description"
                @click="$emit('update:modelValue', emoji.emoji)"
                :title="emoji.description"
              >
                {{ emoji.emoji }}
              </button>
            </div>
          </div>
        </div>
      </PopoverPanel>
    </transition>
  </Popover>
</template>
<script>
import { Popover, PopoverButton, PopoverPanel } from '@headlessui/vue'
import { debounce } from 'frappe-ui'
import { gemoji } from 'gemoji'

export default {
  name: 'IconPicker',
  props: ['modelValue', 'setDefault'],
  emits: ['update:modelValue'],
  expose: ['setRandom'],
  data() {
    return { search: '' }
  },
  components: {
    Popover,
    PopoverButton,
    PopoverPanel,
  },
  mounted() {
    if (this.setDefault && !this.modelValue) {
      this.setRandom()
    }
  },
  computed: {
    emojiGroups() {
      let groups = {}
      for (let emoji of gemoji) {
        if (this.search) {
          let keywords = [emoji.description, ...emoji.names, ...emoji.tags]
            .join(' ')
            .toLowerCase()
          if (!keywords.includes(this.search.toLowerCase())) {
            continue
          }
        }

        let group = groups[emoji.category]
        if (!group) {
          groups[emoji.category] = []
          group = groups[emoji.category]
        }
        group.push(emoji)
      }
      if (!Object.keys(groups).length) {
        groups['No results'] = []
      }
      return groups
    },
  },
  methods: {
    setSearch: debounce(function (search) {
      this.search = search
    }, 300),
    setRandom() {
      let total = gemoji.length
      let index = randomInt(0, total - 1)
      this.$emit('update:modelValue', gemoji[index].emoji)
    },
  },
}

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1) + min)
}
</script>
