<template>
  <div class="min-h-[3rem]">
    <UnsplashImageBrowser
      @select="
        (imageUrl) => {
          loading = true
          $emit('change', imageUrl)
        }
      "
    >
      <img
        v-if="coverImageUrl"
        class="object-cover w-full h-60"
        :class="{ 'opacity-50': loading }"
        :src="coverImageUrl"
        :alt="`${team.title} cover image`"
        @load="loading = false"
      />
      <div
        v-else
        class="w-full h-[3rem] flex items-center justify-center text-sm text-gray-500 bg-gray-50 hover:bg-gray-100"
      >
        Click to set cover image
      </div>
    </UnsplashImageBrowser>
  </div>
</template>
<script>
import UnsplashImageBrowser from '@/components/UnsplashImageBrowser.vue'
export default {
  name: 'TeamPageHomeCover',
  props: ['team'],
  components: { UnsplashImageBrowser },
  emits: ['change'],
  data() {
    return {
      loading: true,
    }
  },
  computed: {
    coverImageUrl() {
      let image_url = this.team.cover_image
      if (!image_url) return null
      if (image_url.startsWith('https://images.unsplash.com')) {
        return image_url + 'w=768&fit=crop&crop=entropy,faces,focalpoint'
      }
      return image_url
    },
  },
}
</script>
