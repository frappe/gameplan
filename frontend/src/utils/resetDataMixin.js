export default {
  methods: {
    $resetData(resetKeys) {
      let data = this.$options.data()
      if (!resetKeys) {
        resetKeys = Object.keys(data)
      }
      for (let key of resetKeys) {
        this[key] = data[key]
      }
    },
  },
}
