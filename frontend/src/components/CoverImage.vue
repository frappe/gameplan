<template>
  <div class="min-h-[3rem] overflow-hidden bg-surface-gray-2">
    <div class="group relative h-[130px] w-full" v-if="validatedImageUrl">
      <img
        class="h-[130px] w-full object-cover"
        :class="{ 'animate-pulse': loading }"
        :style="{ objectPosition }"
        :src="validatedImageUrl"
        @load="loading = false"
      />
      <div
        class="absolute inset-0 flex cursor-grab select-none items-center justify-center"
        v-if="reposition"
        @mousedown="initialY = $event.clientY"
      >
        <div class="text-center">
          <div class="rounded-md py-1 text-lg text-ink-white">Drag up/down to reposition image</div>
          <Button
            class="mt-2"
            @click="
              () => {
                $emit('update:imagePosition', tempImagePosition)
                $emit('change', { imageUrl, imagePosition: tempImagePosition })
                reposition = false
                tempImagePosition = null
              }
            "
          >
            Save position
          </Button>
          <Button class="ml-2 mt-2" @click="reposition = false">Cancel</Button>
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
          <template v-slot="{ togglePopover }">
            <Button variant="outline" @click="togglePopover()"> Change Image </Button>
          </template>
        </UnsplashImageBrowser>
        <Button
          v-if="editable"
          variant="outline"
          @click="
            () => {
              reposition = true
              tempImagePosition = imagePosition
            }
          "
        >
          Reposition
        </Button>
      </div>
    </div>
    <div
      v-else
      class="flex h-[130px] w-full items-center justify-center bg-surface-menu-bar text-sm text-ink-gray-4"
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
        <template v-slot="{ togglePopover }">
          <Button variant="outline" @click="togglePopover()"> Click to set cover image </Button>
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
      initialY: null,
      changeY: null,
      imageDimensions: null,
    }
  },
  mounted() {
    this.onMouseMove = (e) => {
      if (!this.reposition) return
      if (this.initialY && this.imageDimensions) {
        let ratio = this.imageDimensions.ratio
        let clientWidth = e.target.clientWidth
        let clientHeight = clientWidth / ratio
        let diff = this.initialY - e.clientY
        this.changeY = (diff * 100) / clientHeight

        let finalPosition = this.tempImagePosition + this.changeY
        if (finalPosition > 100) {
          this.changeY = 100 - this.tempImagePosition
        }
        if (finalPosition < 0) {
          this.changeY = -this.tempImagePosition
        }
      }
    }
    this.onMouseUp = () => {
      if (!this.reposition) return
      this.initialY = null
      this.tempImagePosition += this.changeY
      this.changeY = 0
    }
    window.addEventListener('mousemove', this.onMouseMove)
    window.addEventListener('mouseup', this.onMouseUp)
  },
  destroyed() {
    window.removeEventListener('mousemove', this.onMouseMove)
    window.removeEventListener('mouseup', this.onMouseUp)
  },
  watch: {
    validatedImageUrl: {
      async handler(newVal, oldVal) {
        if (newVal !== oldVal) {
          this.imageDimensions = await getImgDimensions(newVal)
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
      return `center ${position + this.changeY}%`
    },
  },
}
</script>
