import type { ComponentPublicInstance } from 'vue'

type Instance = ComponentPublicInstance & Record<string, unknown>

export default {
  methods: {
    $resetData(this: Instance, resetKeys?: string[]) {
      let data = (this.$options.data as (this: Instance) => Record<string, unknown>).call(this)
      if (!resetKeys) {
        resetKeys = Object.keys(data)
      }
      for (let key of resetKeys) {
        this[key] = data[key]
      }
    },
  },
}
