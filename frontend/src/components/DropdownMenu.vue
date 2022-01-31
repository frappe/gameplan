<!-- This example requires Tailwind CSS v2.0+ -->
<template>
  <Menu as="div" class="relative inline-block text-left">
    <div>
      <MenuButton :class="$attrs.class">
        <slot>
          <span class="sr-only">Open options</span>
          <FeatherIcon
            :name="icon || 'more-vertical'"
            class="w-5 h-5"
            aria-hidden="true"
          />
        </slot>
      </MenuButton>
    </div>

    <transition
      enter-active-class="transition duration-100 ease-out"
      enter-from-class="transform scale-95 opacity-0"
      enter-to-class="transform scale-100 opacity-100"
      leave-active-class="transition duration-75 ease-in"
      leave-from-class="transform scale-100 opacity-100"
      leave-to-class="transform scale-95 opacity-0"
    >
      <MenuItems
        class="absolute right-0 w-56 mt-2 origin-top-right bg-white divide-y divide-gray-100 rounded-md shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none"
      >
        <div class="py-1">
          <MenuItem
            as="li"
            class="list-none"
            v-for="item in menuItems"
            v-slot="{ active }"
            :disabled="item.disabled || !(item.action || item.route)"
          >
            <button
              type="button"
              v-if="item.action"
              @click.prevent="item.action ? item.action() : null"
              :class="[
                active ? 'bg-gray-100 text-gray-900' : 'text-gray-700',
                'w-full text-left block px-4 py-2 text-sm',
              ]"
            >
              {{ item.label }}
            </button>
            <Link
              v-else
              :link="{ name: item.label, route: item.route || '' }"
              :class="[
                active ? 'bg-gray-100 text-gray-900' : 'text-gray-700',
                'w-full block px-4 py-2 text-sm',
              ]"
            />
          </MenuItem>
        </div>
      </MenuItems>
    </transition>
  </Menu>
</template>

<script>
import { Menu, MenuButton, MenuItem, MenuItems } from '@headlessui/vue'
import Link from './Link.vue'

export default {
  name: 'DropdownMenu',
  inheritAttrs: false,
  props: ['items', 'icon'],
  components: {
    Menu,
    MenuButton,
    MenuItem,
    MenuItems,
    Link,
  },
  computed: {
    menuItems() {
      return this.items
        .map((item) => {
          return {
            label: item.label,
            route: item.route || null,
            action: item.action || null,
            disabled: item.disabled || false,
          }
        })
        .filter((item) => item.label)
    },
  },
}
</script>
