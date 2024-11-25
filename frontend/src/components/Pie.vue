<template>
  <svg
    v-bind="$attrs"
    :class="['-rotate-90 rounded-[50%] bg-surface-gray-2', $attrs.class]"
    viewBox="0 0 32 32"
  >
    <circle
      r="16"
      cx="16"
      cy="16"
      stroke="currentColor"
      stroke-width="32"
      :stroke-dasharray="`${value} 100`"
      class="text-blue-200"
    />
  </svg>
</template>
<script>
export default {
  name: 'Pie',
  props: ['value'],
}
</script>
<style scoped>
@keyframes fillup {
  to {
    stroke-dasharray: v-bind(value) 100;
  }
}

circle {
  fill: theme('colors.gray.100');
  stroke-dasharray: 0 100;
  animation: fillup 0.2s linear forwards;
}
</style>
