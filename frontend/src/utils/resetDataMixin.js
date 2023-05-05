export default {
  methods: {
    $resetData(resetKeys) {
      let data = this.$options.data.call(this)
      if (!resetKeys) {
        resetKeys = Object.keys(data)
      }
      for (let key of resetKeys) {
        this[key] = data[key]
      }
    },
  },
}
