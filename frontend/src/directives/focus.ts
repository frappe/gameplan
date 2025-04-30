import type { ObjectDirective } from 'vue'

interface FocusDirective extends ObjectDirective<HTMLElement> {
  mounted(el: HTMLElement): void
}

const focusDirective: FocusDirective = {
  mounted(el) {
    el.focus()
  },
}

export default focusDirective
