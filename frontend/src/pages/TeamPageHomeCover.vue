<template>
  <div class="min-h-[3rem] bg-gray-100">
    <div class="relative w-full h-60 group" v-if="coverImageUrl">
      <img
        class="object-cover w-full h-60"
        :class="{ 'animate-pulse': loading }"
        :style="{ objectPosition: `center ${imagePosition}` }"
        :src="coverImageUrl"
        :alt="`${team.doc.title} cover image`"
        @load="loading = false"
      />
      <div
        class="absolute inset-0 flex items-center justify-center select-none cursor-grab"
        v-if="reposition"
        @mousedown="initialY = $event.clientY"
      >
        <div class="text-center">
          <div class="px-3 py-1 text-base bg-white rounded-md">
            Drag up/down to reposition image
          </div>
          <Button
            class="mt-2"
            @click="
              () => {
                $emit('change', {
                  cover_image_position: team.doc.cover_image_position,
                })
                reposition = false
              }
            "
          >
            Save position
          </Button>
          <Button class="mt-2 ml-2" @click="reposition = false">Cancel</Button>
        </div>
      </div>
      <div
        class="absolute bottom-0 flex mb-4 space-x-2 transition-opacity -translate-x-1/2 opacity-0 left-1/2 group-hover:opacity-100 focus-within:opacity-100"
        v-if="!reposition"
      >
        <UnsplashImageBrowser
          @select="
            (imageUrl) => {
              loading = true
              imageDimensions = null
              $emit('change', {
                cover_image: imageUrl,
              })
            }
          "
        >
          <Button>Change Image</Button>
        </UnsplashImageBrowser>
        <Button @click="reposition = true">Reposition</Button>
      </div>
    </div>
    <div
      v-else
      class="w-full h-[3rem] flex items-center justify-center text-sm text-gray-500 bg-gray-50 hover:bg-gray-100"
    >
      Click to set cover image
    </div>
  </div>
</template>
<script>
import UnsplashImageBrowser from '@/components/UnsplashImageBrowser.vue'
import { getImgDimensions } from '@/utils'
export default {
  name: 'TeamPageHomeCover',
  props: ['team'],
  components: { UnsplashImageBrowser },
  emits: ['change'],
  data() {
    return {
      reposition: false,
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

        let finalPosition = this.team.doc.cover_image_position + this.changeY
        if (finalPosition > 100) {
          this.changeY = 100 - this.team.doc.cover_image_position
        }
        if (finalPosition < 0) {
          this.changeY = -this.team.doc.cover_image_position
        }
      }
    }
    this.onMouseUp = () => {
      if (!this.reposition) return
      this.initialY = null
      this.team.doc.cover_image_position += this.changeY
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
    coverImageUrl: {
      async handler(newVal, oldVal) {
        if (newVal !== oldVal) {
          this.imageDimensions = await getImgDimensions(newVal)
        }
      },
      immediate: true,
    },
  },
  computed: {
    coverImageUrl() {
      let image_url = this.team.doc.cover_image
      if (!image_url) return null
      if (image_url.startsWith('https://images.unsplash.com')) {
        let width = window.innerWidth || 768
        return image_url + `&w=${width}&fit=crop&crop=entropy,faces,focalpoint`
      }
      return image_url
    },
    imagePosition() {
      return `${this.team.doc.cover_image_position + this.changeY}%`
    },
  },
}
</script>
