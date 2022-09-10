<template>
  <Combobox v-model="selectedValue" nullable>
    <Popover class="w-full">
      <template #target="{ open: openPopover }">
        <div class="relative w-full">
          <div
            class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3"
          >
            <FeatherIcon name="search" class="h-4 w-4 text-gray-500" />
          </div>
          <ComboboxInput
            id="search"
            name="search"
            class="block w-full rounded-md border border-transparent bg-gray-100 py-1 pl-10 pr-3 text-sm placeholder-gray-500 focus:border-gray-100 focus:bg-white focus:text-gray-900 focus:placeholder-gray-400 focus:shadow focus:outline-none focus:ring-0"
            placeholder="Search"
            type="search"
            autocomplete="off"
            @input="
              (e) => {
                $resources.search.submit(e.target.value)
                openPopover()
              }
            "
            v-focus
          />
        </div>
      </template>
      <template #body>
        <ComboboxOptions
          class="overflow-y-auto rounded-md rounded-t-none bg-white p-1.5 shadow-md"
        >
          <ComboboxOption
            as="template"
            v-for="option in $resources.search.data"
            :key="option.name"
            :value="option"
            v-slot="{ active }"
          >
            <li
              :class="[
                'rounded-md px-2.5 py-1.5 text-base',
                { 'bg-gray-100': active },
              ]"
            >
              <div class="flex items-center justify-between">
                <div class="text-base font-medium" v-html="option.title" />
                <span class="text-xs text-gray-600">{{
                  $dayjs(option.modified).fromNow()
                }}</span>
              </div>
              <div
                class="prose-sm prose mt-1 text-sm text-gray-600"
                v-html="option.content"
              />
            </li>
          </ComboboxOption>
          <div
            class="px-2.5 py-1.5 text-base text-gray-600"
            v-if="
              !$resources.search.loading &&
              ($resources.search.data || []).length == 0
            "
          >
            No results found
          </div>
        </ComboboxOptions>
      </template>
    </Popover>
  </Combobox>
</template>
<script>
import {
  Combobox,
  ComboboxInput,
  ComboboxOptions,
  ComboboxOption,
  ComboboxButton,
} from '@headlessui/vue'
import { Popover } from 'frappe-ui'

export default {
  name: 'AppSearch',
  directives: {
    focus: {
      mounted(el) {
        el.focus()
      },
    },
  },
  components: {
    Combobox,
    ComboboxInput,
    ComboboxOptions,
    ComboboxOption,
    ComboboxButton,
    Popover,
  },
  data() {
    return {
      selectedValue: null,
    }
  },
  watch: {
    selectedValue(value) {
      if (value) {
        this.$router.push({
          name: 'ProjectDetailDiscussion',
          params: {
            teamId: value.team,
            projectId: value.project,
            postId: value.name,
          },
        })
        this.$resources.search.reset()
      }
    },
  },
  resources: {
    search: {
      method: 'gameplan.gameplan.doctype.team_discussion.api.search',
      makeParams(query) {
        return { query }
      },
      debounce: 500,
    },
  },
}
</script>
