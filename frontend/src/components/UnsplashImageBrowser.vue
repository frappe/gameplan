<template>
  <Popover>
    <template #trigger="{ open }">
      <slot v-bind="{ open }"></slot>
    </template>
    <template #default>
      <div class="p-3">
        <div class="flex items-center space-x-2">
          <div class="flex-1">
            <TextInput
              type="text"
              placeholder="search by keyword"
              v-model="search"
              :debounce="300"
            />
          </div>
          <ImageUploader kind="cover" @success="(file) => $emit('select', file.file_url)">
            <template v-slot="{ file, progress, uploading, openFileSelector }">
              <div class="w-full text-center">
                <Button @click="openFileSelector" :loading="uploading">
                  {{ uploading ? `Uploading ${progress}%` : 'Upload Image' }}
                </Button>
              </div>
            </template>
          </ImageUploader>
        </div>
        <div class="relative mt-2 grid w-[25.5rem] gap-2 lg:grid-cols-2">
          <button
            v-for="image in $resources.images.data"
            :key="image.id"
            class="h-[50px] w-[200px] overflow-hidden rounded-4 hover:opacity-80"
            @click="$emit('select', image.urls.raw)"
          >
            <img
              :src="image.urls.raw + '&w=200&h=50&fit=crop&crop=entropy,faces,focalpoint'"
              :alt="image.alt_description || 'Unsplash photo'"
            />
          </button>
        </div>
        <div class="mt-2 text-center text-sm text-ink-gray-4">
          Image search powered by
          <a class="underline" target="_blank" href="https://unsplash.com"> Unsplash </a>
        </div>
      </div>
    </template>
  </Popover>
</template>

<script>
// import { Popover, PopoverButton, PopoverPanel } from '@headlessui/vue'
import { Popover } from 'frappe-ui'
import ImageUploader from '@/components/ImageUploader.vue'

export default {
  name: 'UnsplashImageBrowser',
  components: {
    Popover,
    ImageUploader,
  },
  emits: ['select'],
  resources: {
    images() {
      return {
        url: 'gameplan.api.get_unsplash_photos',
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
}
</script>
