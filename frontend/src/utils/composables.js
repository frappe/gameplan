import { onMounted, onUnmounted, reactive, ref, watch } from 'vue'

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

export function useLocalStorage(key, initialValue) {
  let value = ref(null)
  let storedValue = localStorage.getItem(key)
  value.value = storedValue ? JSON.parse(storedValue) : initialValue

  watch(value, (newValue) => {
    localStorage.setItem(key, JSON.stringify(newValue))
  })
  return value
}
