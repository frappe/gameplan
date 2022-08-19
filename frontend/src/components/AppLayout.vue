<template>
  <div class="relative flex flex-col" v-if="$users.data.length">
    <div class="sticky top-0 z-10 bg-white border-b">
      <div class="container">
        <slot name="navbar" />
      </div>
    </div>
    <div class="container flex-1 h-full">
      <div class="flex h-full">
        <div class="flex-shrink-0 w-64 min-h-0 pb-40">
          <slot name="sidebar" />
        </div>
        <div class="w-16 h-full shrink-0"></div>
        <div class="w-full">
          <slot name="main" />
        </div>
      </div>
    </div>
  </div>
</template>
<script>
export default {
  name: 'AppLayout',
}
</script>
