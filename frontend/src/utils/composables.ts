import { computed, onMounted, onUnmounted, reactive } from 'vue'

export function useScreenSize() {
  const size = reactive({
    width: window.innerWidth,
    height: window.innerHeight,
  })

  const onResize = () => {
    size.width = window.innerWidth
    size.height = window.innerHeight
  }

  onMounted(() => {
    window.addEventListener('resize', onResize)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', onResize)
  })

  return size
}

export function isMobile() {
  let size = useScreenSize()
  return computed(() => size.width < 640)
}
