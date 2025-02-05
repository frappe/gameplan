<template>
  <Listbox as="div" v-model="selectedUser">
    <ListboxButton class="w-full h-full text-left" :class="$attrs.class">
      {{ selectedUser?.email || '' }}
      <span v-if="!selectedUser" class="text-sm text-ink-gray-4"> Assign this task </span>
    </ListboxButton>
    <div class="relative">
      <transition
        leave-active-class="transition duration-100 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <ListboxOptions
          class="absolute z-10 py-1 mt-1 bg-surface-white border rounded-md shadow-lg max-w-max"
        >
          <ListboxOption
            v-slot="{ active, selected }"
            v-for="user in users"
            :key="user.email"
            :value="user"
            as="template"
          >
            <li
              class="flex items-baseline py-2 pl-3 pr-6 cursor-default whitespace-nowrap"
              :class="{ 'bg-surface-gray-2': active }"
            >
              <span
                class="mr-2 text-base"
                :class="selected ? 'text-ink-gray-8 font-medium' : 'text-ink-gray-5'"
              >
                {{ user.full_name }}
              </span>
              <span class="text-sm" :class="selected ? 'text-ink-gray-5' : 'text-ink-gray-4'">
                {{ user.email }}
              </span>
            </li>
          </ListboxOption>
        </ListboxOptions>
      </transition>
    </div>
  </Listbox>
</template>
<script>
import { Listbox, ListboxButton, ListboxOptions, ListboxOption } from '@headlessui/vue'
export default {
  name: 'AssignUser',
  inheritAttrs: false,
  props: ['users', 'assignedUser'],
  emits: ['update:assignedUser'],
  components: {
    Listbox,
    ListboxButton,
    ListboxOptions,
    ListboxOption,
  },
  computed: {
    selectedUser: {
      get() {
        return this.assignedUser
      },
      set(val) {
        this.$emit('update:assignedUser', val)
      },
    },
  },
}
</script>
