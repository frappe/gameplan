<template>
  <div class="flex h-full flex-col" v-if="$resources.team.doc">
    <router-view :team="$resources.team" />
  </div>
  <div
    class="grid h-full place-items-center px-4 py-20 text-center text-lg text-ink-gray-5"
    v-else-if="$resources.team.get.error"
  >
    <div class="space-y-2">
      <div>Invalid team or not permitted to access</div>
      <Button :route="{ name: 'Home' }">
        <template #prefix><LucideHome class="w-4" /></template>
        Home
      </Button>
    </div>
  </div>
</template>
<script>
export default {
  name: 'Team',
  props: ['teamId'],
  resources: {
    team() {
      return {
        type: 'document',
        doctype: 'GP Team',
        name: this.teamId,
        realtime: true,
        whitelistedMethods: {
          addMembers: 'add_members',
          removeMember: 'remove_member',
          archive: 'archive',
          unarchive: 'unarchive',
        },
      }
    },
  },
  pageMeta() {
    if (!this.$resources.team.doc) return
    return {
      title: this.$resources.team.doc.title,
    }
  },
}
</script>
