<template>
  <Popover v-slot="{ open }">
    <PopoverButton class="flex w-full">
      <slot v-bind="{ open }"></slot>
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
        class="absolute max-w-sm px-4 mt-3 transform -translate-x-1/2 bg-white rounded-lg left-1/2 sm:px-0 lg:max-w-3xl"
      >
        <div
          class="p-3 overflow-hidden rounded-lg shadow-lg ring-1 ring-black ring-opacity-5"
        >
          <div class="flex items-center space-x-2">
            <div class="flex-1">
              <Input
                type="text"
                placeholder="search by keyword"
                :value="search"
                @input="(val) => (search = val)"
                :debounce="300"
              />
            </div>
            <FileUploader @success="(file) => $emit('select', file.file_url)">
              <template
                v-slot="{ file, progress, uploading, openFileSelector }"
              >
                <div class="w-full text-center">
                  <Button @click="openFileSelector" :loading="uploading">
                    {{ uploading ? `Uploading ${progress}%` : 'Upload Image' }}
                  </Button>
                </div>
              </template>
            </FileUploader>
          </div>
          <div
            class="relative grid gap-2 mt-2 bg-white lg:grid-cols-2 w-[25.5rem]"
          >
            <button
              v-for="image in $resources.images.data"
              :key="image.id"
              class="overflow-hidden rounded hover:opacity-80 w-[200px] h-[50px]"
              @click="$emit('select', image.urls.raw)"
            >
              <img
                :src="
                  image.urls.raw +
                  '&w=200&h=50&fit=crop&crop=entropy,faces,focalpoint'
                "
              />
            </button>
          </div>
          <div class="mt-2 text-sm text-center text-gray-500">
            Image search powered by
            <a class="underline" target="_blank" href="https://unsplash.com">
              Unsplash
            </a>
          </div>
        </div>
      </PopoverPanel>
    </transition>
  </Popover>
</template>

<script>
import { Popover, PopoverButton, PopoverPanel } from '@headlessui/vue'
import { FileUploader } from 'frappe-ui'

export default {
  name: 'UnsplashImageBrowser',
  components: {
    Popover,
    PopoverButton,
    PopoverPanel,
    FileUploader,
  },
  emits: ['select'],
  resources: {
    images() {
      return {
        method: 'gameplan.api.get_unsplash_photos',
        params: { keyword: this.search },
        auto: true,
        debounce: 500,
      }
    },
  },
  data() {
    return {
      search: '',
    }
  },
  methods: {
    log: console.log,
  },
}
</script>
