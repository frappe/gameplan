<template>
  <div class="flex flex-col h-screen overflow-hidden" v-if="$users.data.length">
    <div class="border-b">
      <div class="container">
        <slot name="navbar" />
      </div>
    </div>
    <div class="container flex-1 h-full min-h-0">
      <div class="flex h-full">
        <div class="flex-shrink-0 w-64 min-h-0 pb-40 overflow-auto">
          <slot name="sidebar" />
        </div>
        <div class="w-full min-h-0 pl-10 overflow-y-auto">
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
