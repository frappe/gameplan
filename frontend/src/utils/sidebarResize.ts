import { ref } from 'vue'

export function useSidebarResize() {
  let storedWidth = localStorage.getItem('sidebarWidth')
  const sidebarWidth = ref(storedWidth ? parseInt(storedWidth) : 256)
  const sidebarResizing = ref(false)

  function startResize() {
    document.addEventListener('mousemove', resize)
    document.addEventListener('mouseup', () => {
      document.body.classList.remove('select-none')
      document.body.classList.remove('cursor-col-resize')
      localStorage.setItem('sidebarWidth', sidebarWidth.value.toString())
      sidebarResizing.value = false
      document.removeEventListener('mousemove', resize)
    })
  }

  function resize(e: MouseEvent) {
    sidebarResizing.value = true
    document.body.classList.add('select-none')
    document.body.classList.add('cursor-col-resize')
    sidebarWidth.value = e.clientX

    // snap to 256
    let range = [256 - 10, 256 + 10]
    if (sidebarWidth.value > range[0] && sidebarWidth.value < range[1]) {
      sidebarWidth.value = 256
    }

    if (sidebarWidth.value < 12 * 16) {
      sidebarWidth.value = 12 * 16
    }
    if (sidebarWidth.value > 24 * 16) {
      sidebarWidth.value = 24 * 16
    }
  }

  return {
    sidebarWidth,
    sidebarResizing,
    startResize,
    resize,
  }
}
