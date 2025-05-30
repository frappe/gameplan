import { ref, onMounted, onBeforeUnmount } from 'vue'

export function scrollTo(...options) {
  if (!options || options.length === 0) return
  const container = getScrollContainer()
  if (!container) return
  container.scrollTo(...options)
}

export function getScrollContainer() {
  // window.scrollContainer is reference to the scroll container in DesktopLayout.vue and MobileLayout.vue
  return window.scrollContainer as HTMLElement
}

export function useScrollPosition(options = { threshold: 200 }) {
  const isScrolled = ref(false)

  function updateScrollPosition() {
    const scrollContainer = getScrollContainer()
    isScrolled.value = scrollContainer.scrollTop > options.threshold
  }

  onMounted(() => {
    const scrollContainer = getScrollContainer()
    scrollContainer.addEventListener('scroll', updateScrollPosition)
  })

  onBeforeUnmount(() => {
    const scrollContainer = getScrollContainer()
    scrollContainer.removeEventListener('scroll', updateScrollPosition)
  })

  return {
    isScrolled,
    scrollToTop,
  }
}

export function scrollToTop() {
  const scrollContainer = getScrollContainer()
  scrollContainer.scrollTo({ top: 0, behavior: 'smooth' })
}
