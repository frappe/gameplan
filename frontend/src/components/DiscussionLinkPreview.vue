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
          class="rounded-6 bg-surface-elevation-2 p-3 shadow-2xl ring-1 ring-black ring-opacity-5"
          :style="{ maxWidth: `${maxWidth}px` }"
        >
          <div class="truncate text-base-medium text-ink-gray-8">{{ preview.title }}</div>
          <div class="mt-0.5 truncate text-p-xs text-ink-gray-6">
            {{ getSpace(preview.project)?.title }} · {{ fullName(preview.owner) }} ·
            {{ dayjsLocal(preview.creation).fromNow() }}
          </div>
          <p v-if="preview.snippet" class="mt-2 line-clamp-3 text-p-sm text-ink-gray-6">
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
import { useUser } from '@/data/users'
import { getSpace } from '@/data/spaces'

interface Preview {
  title: string
  project: string
  owner: string
  creation: string
  snippet: string
}

const DISCUSSION_PATH = /^\/g\/(?:.+\/)?discussion\/(\d+)(?:\/|$)/
const HOVER_DELAY = 300
const LEAVE_DELAY = 300

const props = defineProps<{ container: HTMLElement | null }>()
const route = useRoute()
const router = useRouter()

const anchorEl = ref<HTMLElement | null>(null)
const preview = ref<Preview | null>(null)
const maxWidth = ref(0)
const cache = new Map<string, Promise<Preview | null>>()
let openTimer: ReturnType<typeof setTimeout> | undefined
let closeTimer: ReturnType<typeof setTimeout> | undefined

function discussionLink(target: EventTarget | null) {
  const link = (target as HTMLElement | null)?.closest?.('a[href]') as HTMLAnchorElement | null
  if (!link) return null
  const url = new URL(link.href, window.location.origin)
  if (url.host !== window.location.host) return null
  const name = url.pathname.match(DISCUSSION_PATH)?.[1]
  return name ? { link, name } : null
}

function loadPreview(name: string) {
  if (!cache.has(name)) {
    cache.set(
      name,
      call('frappe.client.get_value', {
        doctype: 'GP Discussion',
        filters: { name },
        fieldname: ['title', 'project', 'owner', 'creation', 'content'],
      })
        .then((doc: (Omit<Preview, 'snippet'> & { content?: string }) | null) =>
          doc?.title
            ? {
                ...doc,
                snippet:
                  new DOMParser().parseFromString(doc.content || '', 'text/html').body.textContent?.trim() ||
                  '',
              }
            : null,
        )
        .catch(() => null),
    )
  }
  return cache.get(name)!
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
    maxWidth.value = availableWidth(hovered.link)
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

function availableWidth(link: HTMLElement) {
  const container = props.container
  if (!container) return 0
  const contentRight =
    container.getBoundingClientRect().right - parseFloat(getComputedStyle(container).paddingRight)
  return Math.max(contentRight - link.getBoundingClientRect().left, 0)
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
  const url = new URL(clicked.link.href, window.location.origin)
  router.push(url.pathname.slice(router.options.history.base.length) + url.search + url.hash)
}

function fullName(user: string) {
  return useUser(user).full_name?.trim() || user
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
