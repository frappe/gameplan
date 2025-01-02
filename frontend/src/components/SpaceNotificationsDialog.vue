<template>
  <Dialog :options="{ title: 'Space notifications' }" v-model="show">
    <template #body-content>
      <div class="mt-3 space-y-4" v-if="space">
        <Switch
          v-model="notifyNewPosts"
          label="Notify about new posts"
          description="Get notified when someone creates a new post in this space"
        />
        <Switch
          v-model="notifyNewComments"
          label="Notify about new comments"
          description="Get notified when someone comments on any post in this space"
        />
      </div>
      <div class="mt-4">
        <ErrorMessage :message="spaces.runDocMethod.error" />
      </div>
    </template>
    <template #actions>
      <div class="flex items-center justify-end">
        <Button
          variant="solid"
          @click="submit"
          :loading="spaces.runDocMethod.isLoading(spaceId, 'update_notification_settings')"
        >
          Save
        </Button>
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watchEffect } from 'vue'
import { Dialog, ErrorMessage, Switch, Button } from 'frappe-ui'
import { useSpace } from '@/data/spaces'
import { useDoctype } from 'frappe-ui/src/data-fetching'
import { GPProject } from '@/types/doctypes'
import { useSessionUser } from '@/data/users'

const props = defineProps<{ spaceId: string }>()
const show = defineModel<boolean>()

const space = useSpace(() => props.spaceId)
const spaces = useDoctype<GPProject>('GP Project')

const sessionUser = useSessionUser()
const notifyNewPosts = ref(false)
const notifyNewComments = ref(false)

watchEffect(() => {
  if (space.value) {
    const member = space.value.members.find((member) => member.user === sessionUser.name)
    if (member) {
      notifyNewPosts.value = Boolean(member.notify_new_posts)
      notifyNewComments.value = Boolean(member.notify_new_comments)
    }
  }
})

function submit() {
  spaces.runDocMethod
    .submit({
      name: props.spaceId,
      method: 'update_notification_settings',
      params: {
        notify_new_posts: notifyNewPosts.value,
        notify_new_comments: notifyNewComments.value,
      },
    })
    .then(() => {
      show.value = false
    })
}
</script>
