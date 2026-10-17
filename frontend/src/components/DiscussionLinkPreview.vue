<template>
  <PopoverRoot :open="Boolean(anchorEl && preview)">
    <PopoverAnchor v-if="anchorEl" :reference="anchorEl" />
    <PopoverPortal>
      <PopoverContent
        v-if="anchorEl && preview"
        class="z-[100]"
        side="top"
        align="start"
        :side-offset="4"
        :collision-padding="10"
        @open-auto-focus.prevent
        @pointerenter="cancelClose"
        @pointerleave="scheduleClose"
      >
        <div
          class="w-96 rounded-6 bg-surface-elevation-2 p-4 shadow-2xl ring-1 ring-black ring-opacity-5"
        >
          <div class="truncate text-sm text-ink-gray-5">
            {{ spacePath(preview.project) }} on
            {{ dayjsLocal(preview.creation).format('MMM D, YYYY') }}
          </div>
          <div class="mt-3 line-clamp-2 text-base-semibold text-ink-gray-9">
            {{ preview.title }}
          </div>
          <p v-if="preview.snippet" class="mt-3 line-clamp-2 text-p-sm text-ink-gray-6">
            {{ preview.snippet }}
          </p>
        </div>
        <PopoverArrow class="fill-surface-elevation-2" />
      </PopoverContent>
    </PopoverPortal>
  </PopoverRoot>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { PopoverAnchor, PopoverArrow, PopoverContent, PopoverPortal, PopoverRoot } from 'reka-ui'
import { call, dayjsLocal } from 'frappe-ui'
import { getCommunity } from '@/data/communities'
import { getSpace } from '@/data/spaces'

interface Preview {
  title: string
  project: string
  creation: string
  snippet: string
}

const DISCUSSION_PATH = /^\/(?:.+\/)?discussion\/(\d+)(?:\/|$)/
const HOVER_DELAY = 300
const LEAVE_DELAY = 300

const props = defineProps<{ container: HTMLElement | null }>()
const route = useRoute()
const router = useRouter()

const anchorEl = ref<HTMLElement | null>(null)
const preview = ref<Preview | null>(null)
const cache = new Map<string, Promise<Preview | null>>()
let openTimer: ReturnType<typeof setTimeout> | undefined
let closeTimer: ReturnType<typeof setTimeout> | undefined

function discussionLink(target: EventTarget | null) {
  const link = (target as HTMLElement | null)?.closest?.('a[href]') as HTMLAnchorElement | null
  if (!link) return null
  const url = new URL(link.href, window.location.origin)
  const base = router.options.history.base
  if (url.host !== window.location.host || !url.pathname.startsWith(`${base}/`)) return null
  const path = url.pathname.slice(base.length)
  const name = path.match(DISCUSSION_PATH)?.[1]
  return name ? { link, name, path: path + url.search + url.hash } : null
}

function loadPreview(name: string) {
  if (!cache.has(name)) {
    cache.set(
      name,
      call('frappe.client.get_value', {
        doctype: 'GP Discussion',
        filters: { name },
        fieldname: ['title', 'project', 'creation', 'content'],
      })
        .then((doc: (Omit<Preview, 'snippet'> & { content?: string }) | null) =>
          doc?.title
            ? {
                ...doc,
                snippet:
                  new DOMParser()
                    .parseFromString(doc.content || '', 'text/html')
                    .body.textContent?.trim() || '',
              }
            : null,
        )
        .catch(() => null),
    )
  }
  return cache.get(name)!
}

function spacePath(project: string) {
  const space = getSpace(project)
  const community = space?.team ? getCommunity(space.team) : null
  return [community?.title, space?.title].filter(Boolean).join(' / ')
}

function onPointerOver(event: PointerEvent) {
  const hovered = discussionLink(event.target)
  if (!hovered) return
  if (hovered.link === anchorEl.value) return cancelClose()

  clearTimeout(openTimer)
  openTimer = setTimeout(async () => {
    const result = await loadPreview(hovered.name)
    if (!result || !hovered.link.matches(':hover')) return
    cancelClose()
    preview.value = result
    anchorEl.value = hovered.link
  }, HOVER_DELAY)
}

function onPointerOut(event: PointerEvent) {
  const left = discussionLink(event.target)
  if (!left || left.link.contains(event.relatedTarget as Node | null)) return
  clearTimeout(openTimer)
  if (left.link === anchorEl.value) scheduleClose()
}

function scheduleClose() {
  clearTimeout(closeTimer)
  closeTimer = setTimeout(() => {
    anchorEl.value = null
    preview.value = null
  }, LEAVE_DELAY)
}

function cancelClose() {
  clearTimeout(closeTimer)
}

async function onClick(event: MouseEvent) {
  if (event.defaultPrevented || event.button !== 0) return
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
  const clicked = discussionLink(event.target)
  if (!clicked || clicked.link.closest('[contenteditable="true"]')) return

  event.preventDefault()
  clearTimeout(openTimer)
  anchorEl.value = null
  preview.value = null

  const comment = clicked.link.closest('[data-id]')?.getAttribute('data-id')
  await router.replace({ query: { ...route.query, comment: comment || 'first_post' } })
  router.push(clicked.path)
}

function listen(container: HTMLElement | null | undefined, add: boolean) {
  const method = add ? 'addEventListener' : 'removeEventListener'
  container?.[method]('pointerover', onPointerOver as EventListener)
  container?.[method]('pointerout', onPointerOut as EventListener)
  container?.[method]('click', onClick as EventListener)
}

watch(
  () => props.container,
  (container, previous) => {
    listen(previous, false)
    listen(container, true)
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  clearTimeout(openTimer)
  clearTimeout(closeTimer)
  listen(props.container, false)
})
</script>
