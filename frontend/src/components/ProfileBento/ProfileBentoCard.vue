<template>
  <article
    class="group relative block w-full min-w-0 overflow-hidden rounded-xl text-left outline-none transition focus:outline-none focus-visible:outline-none"
    :class="[flow ? '' : 'h-full', cardChromeClass, cardShellClass, dragClass]"
    :style="rootStyle"
    :data-profile-card-id="card.id"
    :data-size="card.size"
    :role="interactive ? 'button' : undefined"
    :tabindex="interactive ? 0 : undefined"
    @click="selectCard"
    @keydown.enter="selectCard"
    @keydown.space.prevent="selectCard"
    @pointerdown="startPointerDrag"
  >
    <div>
      <Button
        v-if="interactive"
        class="absolute right-3 top-3 z-10 opacity-0 transition-opacity group-hover:opacity-100"
        variant="outline"
        size="xs"
        icon="lucide-x"
        :label="`Remove ${cardTypeLabel} card`"
        @click.stop="$emit('remove')"
        @pointerdown.stop
      />
    </div>

    <div v-if="card.type === 'Blank'" class="h-full" />

    <div
      v-else-if="showHtmlLayout"
      class="relative overflow-hidden"
      :class="flow ? '' : 'h-full'"
      :style="htmlViewportStyle"
    >
      <div ref="htmlStack" class="p-3 sm:p-4">
        <div class="flex items-center gap-1.5 pb-2 text-xs font-medium text-ink-gray-5 sm:text-sm">
          {{ card.title }}
        </div>
        <!-- `readme` is a Text Editor field: frappe sanitizes it on save. Same
             prose pair the editor and every other read-only render use. -->
        <div class="prose prose-v3 max-w-none" v-html="card.text" />
      </div>
      <template v-if="canExpand">
        <div
          v-if="!expanded"
          class="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-surface-base via-surface-base/85 to-transparent"
          aria-hidden="true"
        />
        <button
          type="button"
          class="absolute bottom-2 right-2 z-20 rounded-md px-2 py-1 text-xs font-medium text-ink-gray-7 underline-offset-2 transition hover:bg-surface-gray-2 hover:underline sm:text-sm"
          @click.stop="$emit('toggleExpanded')"
          @pointerdown.stop
        >
          {{ expanded ? 'Show less' : 'Read more' }}
        </button>
      </template>
    </div>

    <div
      v-else-if="showTextLayout"
      class="flex flex-col justify-between p-3 sm:p-4"
      :class="flow ? 'min-h-[6.5rem]' : 'h-full'"
    >
      <div class="flex items-center gap-1.5 pb-2 text-xs font-medium text-ink-gray-5 sm:text-sm">
        {{ card.title }}
        <span v-if="card.url" class="lucide-arrow-up-right size-3.5" aria-hidden="true" />
      </div>
      <p :class="textClass">{{ textCardBody }}</p>
    </div>

    <div v-else class="h-full">
      <div ref="imageFrame" :class="imageFrameClass">
        <img
          v-if="imageUrl"
          :class="imageClass"
          :src="imageUrl"
          :alt="card.title"
          :style="imageStyle"
          @load="loadImageDimensions"
        />
        <FileUploader
          v-else-if="interactive"
          class="block h-full"
          :fileTypes="['image/png', 'image/jpeg']"
          :uploadArgs="{ optimize: true }"
          :validateFile="validateImageFile"
          @success="uploadImage"
        >
          <template #default="{ progress, uploading, error, openFileSelector }">
            <button
              type="button"
              class="flex h-full w-full flex-col items-center justify-center gap-2 p-3 text-center text-ink-gray-5 transition hover:bg-surface-gray-2 sm:p-4"
              :class="{ 'border border-outline-red-2 bg-surface-red-1': error }"
              @click.stop="openFileSelector"
              @pointerdown.stop
            >
              <div
                class="grid size-10 place-items-center rounded-lg border border-dashed bg-surface-base"
                :class="
                  error
                    ? 'border-outline-red-2 text-ink-red-3'
                    : 'border-outline-gray-3 text-ink-gray-6'
                "
              >
                <Spinner v-if="uploading" class="size-5" />
                <span
                  v-else
                  class="size-5"
                  :class="error ? 'lucide-image-off' : 'lucide-image-plus'"
                  aria-hidden="true"
                />
              </div>
              <div v-if="error" class="text-xs font-medium leading-snug text-ink-red-3 sm:text-sm">
                {{ error }}
              </div>
              <div v-else-if="showImageEmptyCopy" class="space-y-0.5">
                <div class="text-xs font-medium text-ink-gray-7 sm:text-sm">
                  {{ uploading ? `Uploading ${progress}%` : 'Add image' }}
                </div>
                <div class="text-xs leading-snug text-ink-gray-5 sm:text-sm">Click to upload</div>
              </div>
            </button>
          </template>
        </FileUploader>
        <div
          v-else
          class="flex h-full flex-col items-center justify-center gap-2 p-3 text-center text-ink-gray-5 sm:p-4"
        >
          <div
            class="grid size-10 place-items-center rounded-lg border border-dashed border-outline-gray-3 bg-surface-base text-ink-gray-6"
          >
            <span class="lucide-image-plus size-5" aria-hidden="true" />
          </div>
          <div v-if="showImageEmptyCopy" class="space-y-0.5">
            <div class="text-xs font-medium text-ink-gray-7 sm:text-sm">Add image</div>
          </div>
        </div>
        <div class="absolute inset-x-0 top-0 p-3 sm:p-4" :class="imageCaptionClass">
          <div
            class="flex items-center gap-1.5 text-xs font-medium sm:text-sm"
            :class="imageTitleClass"
          >
            {{ card.title }}
            <span v-if="card.url" class="lucide-arrow-up-right size-3.5" aria-hidden="true" />
          </div>
        </div>
        <div
          v-if="imageCardBody"
          class="absolute inset-x-0 bottom-0 p-3 sm:p-4"
          :class="imageBodyClass"
        >
          <p :class="imageBodyTextClass">{{ imageCardBody }}</p>
        </div>
        <div
          v-if="repositioning && imageUrl"
          class="absolute inset-0 z-10 flex touch-none select-none items-center justify-center bg-surface-gray-9/35"
          :class="draggingImage ? 'cursor-grabbing' : 'cursor-grab'"
          @click.stop
          @pointerdown.stop="startImageReposition"
          @pointermove.stop="moveImageReposition"
          @pointerup.stop="endImageReposition"
          @pointercancel.stop="endImageReposition"
        >
          <div class="pointer-events-none text-center">
            <div class="text-sm font-medium text-ink-base sm:text-base">Drag image up or down</div>
            <div
              class="pointer-events-auto mt-3 flex items-center justify-center gap-2"
              data-image-reposition-control
              @pointerdown.stop
            >
              <Button @click.stop="saveImagePosition">Save</Button>
              <Button @click.stop="cancelImageReposition">Cancel</Button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <a
      v-if="!interactive && card.url && card.type !== 'Blank'"
      class="absolute inset-0"
      :href="card.url"
      target="_blank"
      rel="noreferrer"
      :aria-label="card.title"
    />

    <div v-if="showSize">
      <Badge>{{ card.size }}</Badge>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useElementSize } from '@vueuse/core'
import type { ProfileBentoCard } from './types'
import { profileBentoFlowCollapsedHeight } from './profileBentoLayout'
import { Badge, Button, FileUploader, Spinner } from 'frappe-ui'
import { getImgDimensions } from '@/utils'

const props = defineProps<{
  card: ProfileBentoCard
  selected?: boolean
  interactive?: boolean
  draggable?: boolean
  dragging?: boolean
  repositioning?: boolean
  showSize?: boolean
  /** Single-column flow layout (mobile): the card sizes itself instead of being positioned. */
  flow?: boolean
  expanded?: boolean
  canExpand?: boolean
}>()

const emit = defineEmits<{
  cancelImageReposition: []
  pointerDown: [event: PointerEvent]
  remove: []
  saveImagePosition: [position: number]
  select: []
  toggleExpanded: []
  uploadImage: [fileUrl: string]
  'update:contentHeight': [height: number]
}>()

interface UploadedFile {
  file_url: string
}

const imageGradientClassBySize: Record<ProfileBentoCard['size'], string> = {
  '1x1': 'h-16',
  '1x2': 'h-20',
  '2x1': 'h-20',
  '2x2': 'h-28',
  '4x1': 'h-20',
  '4x2': 'h-32',
}

const imageFrame = ref<HTMLElement | null>(null)
const htmlStack = ref<HTMLElement | null>(null)
const tempImagePosition = ref(50)
const draggingImage = ref(false)
const dragStartY = ref(0)
const dragStartPosition = ref(50)
const imageDimensions = ref<{ width: number; height: number; ratio: number } | null>(null)

const cardChromeClass = computed(() => {
  if (props.card.type === 'Blank') {
    if (!props.interactive) return 'border-0 ring-0 shadow-none'
    return props.selected
      ? 'border border-outline-gray-4 ring-2 ring-outline-gray-2'
      : 'border border-transparent hover:bg-surface-gray-2'
  }
  if (showImageLayout.value) {
    if (!imageUrl.value && !props.selected) return 'border border-outline-gray-2'
    return props.selected
      ? 'border border-outline-gray-4 ring-2 ring-outline-gray-2'
      : 'border border-transparent hover:border-outline-gray-3'
  }
  return props.selected
    ? 'border border-outline-gray-4 ring-2 ring-outline-gray-2'
    : 'border border-outline-gray-2 hover:border-outline-gray-3'
})

const cardShellClass = computed(() => {
  if (props.card.type === 'Blank') return ''
  if (showImageLayout.value) return ''
  return 'bg-surface-base'
})

const dragClass = computed(() => {
  if (!props.draggable) return ''
  if (props.dragging) return 'cursor-grabbing opacity-20 scale-[0.98]'
  return 'cursor-grab select-none touch-none active:cursor-grabbing'
})

const textClass = computed(() => {
  return 'text-base font-medium leading-snug text-ink-gray-9 sm:text-xl'
})

const cardTypeLabel = computed(() => {
  return props.card.type === 'Blank' ? 'blank' : 'profile'
})

const showHtmlLayout = computed(() => {
  return props.card.type !== 'Blank' && props.card.format === 'html'
})

const showImageLayout = computed(() => {
  if (showHtmlLayout.value) return false
  return props.card.type === 'Image' || Boolean(imageUrl.value)
})

const showTextLayout = computed(() => {
  return !showImageLayout.value && !showHtmlLayout.value
})

const rootStyle = computed(() => {
  if (!props.flow || !showImageLayout.value) return undefined
  return { aspectRatio: String(flowAspectRatio.value) }
})

/**
 * In the single-column flow layout a card spans the full width, so a tall
 * declared size (1x2) would render as a ~2x-viewport-wide slab. Keep the
 * declared ratio but never let it go past 4:3 portrait.
 */
const flowAspectRatio = computed(() => {
  let [columns, rows] = props.card.size.split('x').map(Number)
  return Math.max(columns / rows, 3 / 4)
})

const htmlViewportStyle = computed(() => {
  if (!props.flow || props.expanded) return undefined
  return { maxHeight: `${profileBentoFlowCollapsedHeight}px` }
})

const imageFrameClass = computed(() => {
  if (imageRendering.value === 'Natural') {
    return 'relative grid h-full place-items-center bg-surface-gray-2'
  }

  return 'relative h-full'
})

const imageClass = computed(() => {
  return {
    Cover: 'h-full w-full object-cover',
    Fit: 'h-full w-full object-contain',
    Natural: 'max-h-full max-w-full object-contain',
  }[imageRendering.value]
})

const imageStyle = computed(() => {
  return {
    objectPosition: `center ${currentImagePosition.value}%`,
  }
})

const currentImagePosition = computed(() => {
  if (props.repositioning) return clampPosition(tempImagePosition.value)
  return clampPosition(props.card.imagePosition ?? 50)
})

const imageCaptionClass = computed(() => {
  if (!imageUrl.value) return ''
  if (imageRendering.value !== 'Cover') return ''
  return `bg-gradient-to-b from-surface-gray-7/50 to-transparent dark:from-surface-white/70 ${
    imageGradientClassBySize[props.card.size]
  }`
})

const imageTitleClass = computed(() => {
  if (!imageUrl.value) return 'text-ink-gray-6'
  if (imageRendering.value !== 'Cover') return 'text-ink-gray-6'
  return 'text-ink-gray-1'
})

const imageBodyClass = computed(() => {
  if (imageRendering.value !== 'Cover') return 'bg-surface-base/90'
  return 'bg-gradient-to-t from-surface-gray-7/75 to-transparent dark:from-surface-white/75'
})

const imageBodyTextClass = computed(() => {
  if (imageRendering.value !== 'Cover') return 'text-sm font-medium leading-snug text-ink-gray-9'
  return 'text-sm font-medium leading-snug text-ink-white'
})

const showImageEmptyCopy = computed(() => {
  return props.card.size !== '1x1'
})

const imageRendering = computed(() => {
  return props.card.imageRendering || 'Cover'
})

const imageUrl = computed(() => {
  return props.card.image
})

const textCardBody = computed(() => {
  return props.card.text
})

const imageCardBody = computed(() => {
  return props.card.text?.trim()
})

function selectCard() {
  if (!props.interactive) return
  emit('select')
}

function uploadImage(file: UploadedFile) {
  emit('uploadImage', file.file_url)
}

function validateImageFile(file: File) {
  const extension = file.name.split('.').pop()?.toLowerCase()
  if (!extension || !['png', 'jpg', 'jpeg'].includes(extension)) {
    return 'Only PNG and JPG images are allowed'
  }
}

function startPointerDrag(event: PointerEvent) {
  if (!props.draggable || event.button !== 0) return
  emit('pointerDown', event)
}

// `htmlStack` is never height-constrained (its wrapper does the clipping), so
// this stays the card's natural content height whether it is collapsed or
// expanded — the grid needs a value that does not change as it grows the tile.
const { height: htmlStackHeight } = useElementSize(htmlStack)
watch(htmlStackHeight, (height) => {
  if (!showHtmlLayout.value || !height) return
  emit('update:contentHeight', height)
})

watch(
  () => [props.repositioning, props.card.imagePosition] as const,
  ([repositioning]) => {
    if (repositioning) {
      tempImagePosition.value = clampPosition(props.card.imagePosition ?? 50)
    }
  },
)

watch(
  imageUrl,
  async (url) => {
    imageDimensions.value = url ? await getImgDimensions(url) : null
  },
  { immediate: true },
)

async function loadImageDimensions() {
  if (!imageUrl.value) return
  imageDimensions.value = await getImgDimensions(imageUrl.value)
}

function startImageReposition(event: PointerEvent) {
  if (event.button !== 0 || isImageRepositionControl(event.target)) return

  let verticalOverflow = getVerticalOverflow()
  if (!verticalOverflow) return

  draggingImage.value = true
  dragStartY.value = event.clientY
  dragStartPosition.value = clampPosition(tempImagePosition.value)
  event.currentTarget.setPointerCapture(event.pointerId)
}

function isImageRepositionControl(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false
  return Boolean(target.closest('[data-image-reposition-control]'))
}

function moveImageReposition(event: PointerEvent) {
  if (!draggingImage.value) return

  let verticalOverflow = getVerticalOverflow()
  if (!verticalOverflow) return

  let deltaY = dragStartY.value - event.clientY
  let deltaPosition = (deltaY * 100) / verticalOverflow
  tempImagePosition.value = clampPosition(dragStartPosition.value + deltaPosition)
}

function endImageReposition(event: PointerEvent) {
  if (!draggingImage.value) return

  draggingImage.value = false
  if (event.currentTarget.hasPointerCapture(event.pointerId)) {
    event.currentTarget.releasePointerCapture(event.pointerId)
  }
}

function saveImagePosition() {
  emit('saveImagePosition', clampPosition(tempImagePosition.value))
}

function cancelImageReposition() {
  emit('cancelImageReposition')
}

function getVerticalOverflow() {
  if (!imageFrame.value) return 0

  let { width, height } = imageFrame.value.getBoundingClientRect()
  let imageRatio = getImageRatio()
  if (!imageRatio) return 0

  let imageHeight = width / imageRatio
  return Math.max(0, imageHeight - height)
}

function getImageRatio() {
  if (imageDimensions.value?.ratio) return imageDimensions.value.ratio

  let image = imageFrame.value?.querySelector('img')
  if (!image?.naturalWidth || !image.naturalHeight) return 0
  return image.naturalWidth / image.naturalHeight
}

function clampPosition(position: number) {
  return Math.min(100, Math.max(0, Number(position) || 0))
}
</script>
