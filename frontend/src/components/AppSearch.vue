<template>
  <Combobox v-model="selectedValue" nullable>
    <Popover class="w-full">
      <template #target="{ open: openPopover }">
        <div class="relative w-full">
          <div
            class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none"
          >
            <FeatherIcon name="search" class="w-4 h-4 text-gray-500" />
          </div>
          <ComboboxInput
            id="search"
            name="search"
            class="block w-full py-1 pl-10 pr-3 text-sm placeholder-gray-500 bg-gray-100 border border-transparent rounded-md focus:outline-none focus:ring-0 focus:border-gray-100 focus:shadow focus:text-gray-900 focus:placeholder-gray-400 focus:bg-white"
            placeholder="Search"
            type="search"
            autocomplete="off"
            @input="
              (e) => {
                $resources.search.submit(e.target.value)
                openPopover()
              }
            "
          />
        </div>
      </template>
      <template #body>
        <ComboboxOptions
          class="p-1.5 bg-white rounded-md shadow-md rounded-t-none max-h-[14rem] overflow-y-auto"
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
                'px-2.5 py-1.5 rounded-md text-base',
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
                class="mt-1 text-sm prose-sm prose text-gray-600"
                v-html="option.content"
              />
            </li>
          </ComboboxOption>
          <div
            class="text-base text-gray-600 px-2.5 py-1.5"
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
      method:
        'gameplan.gameplan.doctype.team_project_discussion.team_project_discussion.search',
      makeParams(query) {
        return { query }
      },
      debounce: 500,
    },
  },
}
</script>
