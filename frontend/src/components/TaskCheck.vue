<template>
  <button
    class="block mr-2"
    :aria-label="checked ? 'Mark as incomplete' : 'Mark as complete'"
    @click="change"
  >
    <FeatherIcon
      :name="checked ? 'check' : 'circle'"
      class="w-4 transition-colors"
      :class="{
        'text-gray-500 hover:text-gray-700': checked,
        'text-gray-400 hover:text-gray-600': !checked,
      }"
    />
  </button>
</template>
<script>
export default {
  name: 'TaskCheck',
  props: ['checked'],
  emits: ['change'],
  methods: {
    change() {
      this.$emit('change', this.checked ? 0 : 1)
    },
  },
}
</script>
