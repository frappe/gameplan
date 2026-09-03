<template>
  <div class="min-h-[3rem] overflow-hidden bg-surface-gray-2">
    <div ref="cover" class="group relative h-[178px] w-full" v-if="validatedImageUrl">
      <img
        class="h-[178px] w-full object-cover"
        :class="{ 'animate-pulse': loading }"
        :style="{ objectPosition }"
        :src="validatedImageUrl"
        @load="loading = false"
      />
      <div
        class="absolute inset-0 flex touch-none select-none items-center justify-center bg-black/20"
        :class="dragging ? 'cursor-grabbing' : 'cursor-grab'"
        v-if="reposition"
        @pointerdown="startDrag"
        @pointermove="drag"
        @pointerup="endDrag"
        @pointercancel="endDrag"
      >
        <div class="pointer-events-none text-center">
          <div class="rounded-5 py-1 text-xl text-ink-base">Drag image up or down</div>
          <div class="pointer-events-auto" data-cover-control @pointerdown.stop>
            <Button class="mt-2" @click="savePosition">Save position</Button>
            <Button class="ms-2 mt-2" @click="cancelReposition">Cancel</Button>
          </div>
        </div>
      </div>
      <div
        class="absolute bottom-0 left-1/2 mb-4 flex -translate-x-1/2 space-x-2 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100"
        v-if="!reposition"
      >
        <UnsplashImageBrowser
          v-if="editable"
          @select="
            (imageUrl) => {
              loading = true
              imageDimensions = null
              $emit('update:imageUrl', imageUrl)
              $emit('change', { imageUrl, imagePosition })
            }
          "
        >
          <template v-slot>
            <Button variant="outline"> Change Image </Button>
          </template>
        </UnsplashImageBrowser>
        <Button v-if="editable" variant="outline" @click="beginReposition"> Reposition </Button>
      </div>
    </div>
    <div
      v-else
      class="flex h-[178px] w-full items-center justify-center bg-surface-sidebar text-sm text-ink-gray-4"
    >
      <UnsplashImageBrowser
        v-if="editable"
        @select="
          (imageUrl) => {
            loading = true
            imageDimensions = null
            $emit('update:imageUrl', imageUrl)
            $emit('change', { imageUrl, imagePosition })
          }
        "
      >
        <template v-slot>
          <Button variant="outline"> Click to set cover image </Button>
        </template>
      </UnsplashImageBrowser>
    </div>
  </div>
</template>
<script>
import UnsplashImageBrowser from '@/components/UnsplashImageBrowser.vue'
import { getImgDimensions } from '@/utils'

export default {
  name: 'CoverImage',
  props: {
    imageUrl: {
      type: String,
      default: null,
    },
    imagePosition: {
      type: Number,
      default: 0,
    },
    editable: {
      type: Boolean,
      default: false,
    },
  },
  components: { UnsplashImageBrowser },
  emits: ['change', 'update:imageUrl', 'update:imagePosition'],
  data() {
    return {
      reposition: false,
      tempImagePosition: null,
      loading: true,
      dragging: false,
      dragStartY: null,
      dragStartPosition: null,
      imageDimensions: null,
    }
  },
  watch: {
    validatedImageUrl: {
      async handler(newVal, oldVal) {
        if (newVal !== oldVal) {
          // null when there is no cover, or when the image failed to load.
          this.imageDimensions = newVal ? await getImgDimensions(newVal) : null
        }
      },
      immediate: true,
    },
  },
  computed: {
    validatedImageUrl() {
      if (!this.imageUrl) return null
      if (this.imageUrl.startsWith('https://images.unsplash.com')) {
        let width = window.innerWidth || 768
        return this.imageUrl + `&w=${width}&fit=crop&crop=entropy,faces,focalpoint`
      }
      return this.imageUrl
    },
    objectPosition() {
      let position = this.reposition ? this.tempImagePosition : this.imagePosition
      return `center ${this.clampPosition(position)}%`
    },
  },
  methods: {
    beginReposition() {
      this.reposition = true
      this.tempImagePosition = this.clampPosition(this.imagePosition)
    },
    savePosition() {
      let imagePosition = this.clampPosition(this.tempImagePosition)
      this.$emit('update:imagePosition', imagePosition)
      this.$emit('change', { imageUrl: this.imageUrl, imagePosition })
      this.closeReposition()
    },
    cancelReposition() {
      this.closeReposition()
    },
    startDrag(event) {
      event.preventDefault()
      if (event.target?.closest?.('[data-cover-control]')) return

      let verticalOverflow = this.getVerticalOverflow()
      if (!verticalOverflow) return

      this.dragging = true
      this.dragStartY = event.clientY
      this.dragStartPosition = this.clampPosition(this.tempImagePosition)
      event.currentTarget.setPointerCapture(event.pointerId)
    },
    drag(event) {
      if (!this.dragging) return

      let verticalOverflow = this.getVerticalOverflow()
      if (!verticalOverflow) return

      let deltaY = this.dragStartY - event.clientY
      let deltaPosition = (deltaY * 100) / verticalOverflow
      this.tempImagePosition = this.clampPosition(this.dragStartPosition + deltaPosition)
    },
    endDrag(event) {
      if (!this.dragging) return

      this.dragging = false
      this.dragStartY = null
      this.dragStartPosition = null
      if (event.currentTarget.hasPointerCapture(event.pointerId)) {
        event.currentTarget.releasePointerCapture(event.pointerId)
      }
    },
    closeReposition() {
      this.dragging = false
      this.dragStartY = null
      this.dragStartPosition = null
      this.reposition = false
      this.tempImagePosition = null
    },
    getVerticalOverflow() {
      if (!this.$refs.cover || !this.imageDimensions) return 0

      let { width, height } = this.$refs.cover.getBoundingClientRect()
      let imageHeight = width / this.imageDimensions.ratio
      return Math.max(0, imageHeight - height)
    },
    clampPosition(position) {
      return Math.min(100, Math.max(0, Number(position) || 0))
    },
  },
}
</script>
