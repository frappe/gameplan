<template>
  <router-link
    :to="{ name: 'NewDiscussion' }"
    class="flex w-full items-center gap-3 rounded-lg bg-gray-100 px-3 py-2 text-base text-gray-600 hover:bg-gray-200"
  >
    <UserAvatar :user="$user().name" size="2xl" />
    <span> Start a discussion... </span>
    <Button class="ml-auto" disabled>Publish</Button>
  </router-link>
</template>
<script></script>
