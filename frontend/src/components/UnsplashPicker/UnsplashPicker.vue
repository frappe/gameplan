<template>
  <Dialog v-model:open="open" :title="title" size="4xl">
    <div class="space-y-4" data-unsplash-picker>
      <TextInput
        ref="searchInput"
        v-model="query"
        type="text"
        :placeholder="placeholder"
        data-unsplash-search
        @keydown.enter.prevent="runSearch"
      >
        <template #prefix>
          <span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" />
        </template>
      </TextInput>

      <!-- Browsing and searching are the same request with a different argument,
           so the chips are a row of buttons rather than a second control: picking
           one clears the box, typing in the box clears the selection. -->
      <div class="flex flex-wrap gap-1.5" data-unsplash-topics>
        <Button
          v-for="topic in unsplashTopics"
          :key="topic.slug"
          size="sm"
          :variant="activeTopic === topic.slug ? 'solid' : 'subtle'"
          :label="topic.label"
          :data-unsplash-topic="topic.slug"
          @click="browseTopic(topic.slug)"
        />
      </div>

      <!-- Every state fills the same box, so searching, finding nothing and
           finding thirty photos all leave the dialog exactly as tall. A cap
           would not do it: a spinner under a max-height is only as tall as a
           spinner, and the dialog would still jump when the grid arrived. -->
      <div class="h-[55vh]" data-unsplash-pane>
        <!-- One state at a time, in the order they can happen: a site that never
             set a key, a request that failed, a first request in flight, nothing
             found, and then the results. -->
        <div
          v-if="notConfigured"
          class="rounded border border-outline-gray-2 bg-surface-gray-1 p-4"
          data-unsplash-not-configured
        >
          <p class="text-base font-medium text-ink-gray-8">Unsplash is not set up</p>
          <p class="mt-1 text-sm leading-5 text-ink-gray-6">{{ notConfiguredMessage }}</p>
        </div>

        <ErrorMessage v-else-if="errorMessage" :message="errorMessage" data-unsplash-error />

        <div
          v-else-if="loading && !photos.length"
          class="flex h-full flex-col items-center justify-center gap-2 text-ink-gray-5"
          data-unsplash-loading
        >
          <LoadingIndicator class="size-5" />
          <p class="text-sm">Searching Unsplash…</p>
        </div>

        <p
          v-else-if="!photos.length"
          class="flex h-full items-center justify-center px-6 text-center text-sm leading-5 text-ink-gray-5"
          data-unsplash-empty
        >
          {{ emptyMessage }}
        </p>

        <!-- `h-full` on the root, not a cap: the viewport reka gives
             `overflow-y: scroll` is itself `h-full`, which resolves to auto
             inside a box that only has a max-height, and then nothing scrolls. -->
        <ScrollArea v-else class="h-full" viewport-class="pr-3">
          <!-- Columns rather than a grid: photos keep their own proportions and
               stack with no dead space, which is the only way a wall of mixed
               portrait and landscape shots packs tightly.

               Switching topics keeps the photos that are already there, dimmed,
               rather than swapping them for a spinner. The pane cannot change
               height either way, so a flash to empty and back buys nothing. -->
          <ul
            class="columns-2 gap-1 transition-opacity sm:columns-3"
            :class="loading ? 'pointer-events-none opacity-40' : ''"
            data-unsplash-results
          >
            <li
              v-for="photo in photos"
              :key="photo.id"
              class="group relative mb-1 block break-inside-avoid overflow-hidden rounded"
            >
              <!-- The tile takes the photo's own proportions up front, so the
                   columns settle once instead of shuffling as each lazy image
                   lands. -->
              <img
                :src="photo.thumb_url"
                :alt="photo.alt || `Photo by ${photo.photographer_name}`"
                class="block w-full bg-surface-gray-2"
                :style="aspectRatio(photo)"
                loading="lazy"
              />
              <!-- The picker is the whole tile, laid over the image, because the
                   credit below has to be a link and a link cannot live inside a
                   button. Its label carries what the tile no longer says in text. -->
              <button
                type="button"
                class="absolute inset-0 transition focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-outline-gray-4 group-hover:bg-black/10"
                :data-unsplash-photo="photo.id"
                :aria-label="`Use this photo by ${photo.photographer_name}`"
                @click="choose(photo)"
              />
              <!-- Unsplash requires the photographer to be credited wherever the
                   photo is shown, with these UTM parameters on the link. The scrim
                   is what keeps it readable over a pale photo.

                   A literal white, not `text-ink-white`: that token is the ink for
                   an inverted surface and flips to black in dark mode, which is
                   exactly the wrong way round over a scrim that is always dark. -->
              <p
                class="pointer-events-none absolute inset-x-0 bottom-0 truncate bg-gradient-to-t from-black/70 to-transparent px-2 pb-1.5 pt-6 text-xs text-white"
              >
                <a
                  :href="photo.photographer_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="pointer-events-auto hover:underline"
                  @click.stop
                >
                  {{ photo.photographer_name }}
                </a>
              </p>
            </li>
          </ul>
        </ScrollArea>
      </div>

      <p class="text-xs text-ink-gray-5">
        Photos from
        <a
          :href="unsplashUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="underline hover:text-ink-gray-7"
        >
          Unsplash
        </a>
      </p>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
/**
 * Pick a photo from Unsplash.
 *
 * Every request goes through `gameplan/unsplash.py`, never straight to
 * api.unsplash.com: the access key is a site secret and must not reach the
 * browser. What comes back is already trimmed to `UnsplashPhoto`.
 *
 * The component only *chooses* — it emits the photo and lets the caller decide
 * where the URL is written, so nothing here knows about profiles.
 */
import { computed, ref, useTemplateRef, watch } from 'vue'
import { refDebounced } from '@vueuse/core'
import {
  Button,
  Dialog,
  ErrorMessage,
  LoadingIndicator,
  ScrollArea,
  TextInput,
  useCall,
} from 'frappe-ui'
import { unsplashTopics, type UnsplashPhoto, type UnsplashSearchResult } from './types'

const props = withDefaults(
  defineProps<{
    title?: string
    placeholder?: string
  }>(),
  {
    title: 'Choose a photo',
    placeholder: 'Search Unsplash',
  },
)

const emit = defineEmits<{
  select: [photo: UnsplashPhoto]
}>()

const open = defineModel<boolean>('open', { required: true })

const unsplashUrl = 'https://unsplash.com/?utm_source=gameplan&utm_medium=referral'

const defaultTopic = unsplashTopics[0].slug

const query = ref('')
/**
 * The chip that is lit, and the browse the picker falls back to.
 *
 * Exactly one of this and `query` is ever set: a query is a search across all of
 * Unsplash, a topic is a browse within one, and the server would have to pick
 * anyway. Emptying the search box returns here rather than to a blank pane,
 * which is why there is no "nothing yet" state left to render.
 */
const activeTopic = ref(defaultTopic)
// Typing is cheap; an Unsplash request is not. A demo key allows 50 an hour.
const debouncedQuery = refDebounced(query, 400)
const searchInput = useTemplateRef<{ el?: HTMLInputElement }>('searchInput')

const search = useCall<UnsplashSearchResult, { query: string; topic: string }>({
  url: '/api/v2/method/gameplan.unsplash.search_photos',
  immediate: false,
})

// Tracking is a side effect at Unsplash's end, not a read, so it must not be a
// GET — Frappe would roll the request back and the ping would never be sent.
const trackDownload = useCall<unknown, { download_location: string }>({
  url: '/api/v2/method/gameplan.unsplash.track_download',
  method: 'POST',
  immediate: false,
})

const result = computed(() => search.data as UnsplashSearchResult | null)
const photos = computed(() => result.value?.photos || [])
const loading = computed(() => search.loading)
const notConfigured = computed(() => result.value?.configured === false)
const notConfiguredMessage = computed(() => result.value?.message || '')
/** What the photos on screen belong to, which is not what is being typed. */
const searchedQuery = computed(() => result.value?.query || '')
const emptyMessage = computed(() => {
  if (searchedQuery.value) return `No photos found for “${searchedQuery.value}”. Try another word.`

  let topic = unsplashTopics.find((entry) => entry.slug === result.value?.topic)
  if (topic) return `No photos in ${topic.label} right now. Try another one.`
  return 'No photos found.'
})
const errorMessage = computed(() => {
  let error = search.error as Error | null
  if (!error) return ''
  // The server's messages name the config key or the failure mode, which is the
  // whole reason they are shown. `frappe.throw` prefixes the exception class.
  return error.message?.replace(/^\w*Error:\s*/, '') || 'Could not search Unsplash.'
})

// `flush: 'post'` so the dialog's content has rendered and the input exists; the
// extra frame lets the dialog finish its own focus handling before we take it.
watch(
  open,
  (isOpen) => {
    if (!isOpen) return

    // Reopened on the default browse rather than on the last search, so a picker
    // that was closed weeks ago does not reopen on a stale word.
    query.value = ''
    activeTopic.value = defaultTopic
    runSearch()
    requestAnimationFrame(() => searchInput.value?.el?.focus())
  },
  { flush: 'post' },
)

// Typing takes over from the chips, and clearing the box by hand hands it back.
watch(debouncedQuery, (value) => {
  let typed = value.trim()
  // A chip and the open handler both blank the box, and the debounce reports
  // that back a beat later. Without this the selection would snap to Featured
  // 400ms after every chip click, and each one would cost a second request.
  if (!typed && activeTopic.value) return

  activeTopic.value = typed ? '' : defaultTopic
  runSearch()
})

/**
 * The tile's shape, held before its image has loaded.
 *
 * Left off when Unsplash gave no dimensions, so the tile falls back to sizing
 * itself from the image as it always did rather than collapsing to nothing.
 */
function aspectRatio(photo: UnsplashPhoto) {
  if (!photo.width || !photo.height) return undefined
  return { aspectRatio: `${photo.width} / ${photo.height}` }
}

function browseTopic(slug: string) {
  query.value = ''
  activeTopic.value = slug
  runSearch()
}

function runSearch() {
  // `useCall` resolves rather than rejects on failure; the error state reads
  // `search.error` instead of a catch.
  search.submit({ query: query.value.trim(), topic: activeTopic.value })
}

function choose(photo: UnsplashPhoto) {
  emit('select', photo)
  open.value = false

  // Fired here, not when the photo was merely listed: Unsplash counts a
  // download when a photo is used. Failing to report it must not fail the pick.
  if (photo.download_location) {
    trackDownload.submit({ download_location: photo.download_location }).catch(() => {})
  }
}
</script>
