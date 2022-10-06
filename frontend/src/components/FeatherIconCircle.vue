<template>
  <div
    class="grid h-8 w-8 place-items-center shrink-0 rounded-full"
    :class="circleClasses"
  >
    <FeatherIcon :name="name" class="h-4 w-4" :class="iconClasses" />
  </div>
</template>
<script>
export default {
  name: 'FeatherIconCircle',
  props: {
    name: {
      type: String,
      required: true,
    },
    color: {
      type: String,
      default: 'gray',
    },
  },
  computed: {
    circleClasses() {
      return {
        gray: 'bg-gray-100',
        green: 'bg-green-100',
      }[this.color]
    },
    iconClasses() {
      return {
        gray: 'text-gray-600',
        green: 'text-green-600',
      }[this.color]
    },
  },
}
</script>
