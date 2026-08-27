<template>
  <div class="flex min-h-0 flex-col">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <h2 class="text-3xl-semibold leading-none text-ink-gray-9">Invite People</h2>
      </div>
    </div>
    <div class="mt-4 space-y-4">
      <FormControl
        type="textarea"
        label="Invite by email"
        placeholder="user1@example.com, user2@example.com, ..."
        @input="emails = $event.target.value"
        :debounce="100"
        :disabled="inviteByEmail.loading"
      />
      <template v-if="emails">
        <div>
          <Select
            label="Role"
            :options="[
              { label: 'Admin', value: 'Gameplan Admin' },
              { label: 'User', value: 'Gameplan Member' },
            ]"
            v-model="role"
          />
          <p class="mt-2 text-base text-ink-gray-8">{{ description }}</p>
        </div>
        <ErrorMessage :message="inviteByEmail.error" />
        <Button
          variant="solid"
          @click="
            inviteByEmail.submit({
              emails,
              role,
              projects: null,
            })
          "
          :loading="inviteByEmail.loading"
        >
          Invite
        </Button>
      </template>
    </div>

    <!-- One call can end three ways per email, so the result is grouped instead of
         summarized: the admin needs to see which address landed in which bucket.
         It sits next to Pending Invites so all invite feedback is in one place. -->
    <div v-if="resultGroups.length && !emails" class="mt-4 rounded-4 bg-surface-gray-2 p-3">
      <div class="space-y-2">
        <div v-for="group in resultGroups" :key="group.label" class="flex gap-2">
          <span
            :class="group.icon"
            class="mt-0.5 size-4 shrink-0 text-ink-gray-5"
            aria-hidden="true"
          />
          <div class="min-w-0">
            <div class="text-base text-ink-gray-8">{{ group.label }}</div>
            <div class="break-words text-p-base text-ink-gray-5">
              {{ group.emails.join(', ') }}
            </div>
          </div>
        </div>
      </div>
      <p v-if="result?.skipped.length" class="mt-3 text-p-sm text-ink-gray-5">
        Skipped emails already have access, have a pending invite, or belong to a disabled account.
      </p>
    </div>

    <template v-if="pendingInvitations.data?.length && !emails">
      <div class="mt-4 flex items-center justify-between border-b py-2 text-base text-ink-gray-5">
        <div class="w-4/5">Pending Invites</div>
      </div>
      <ul class="divide-y">
        <li
          class="flex items-center justify-between py-2"
          v-for="invitation in pendingInvitations.data"
          :key="invitation.name"
        >
          <div class="w-4/5 text-base">
            <span class="text-ink-gray-8">
              {{ invitation.email }}
            </span>
            <span class="text-ink-gray-5"> ({{ getRoleLabel(invitation.role) }}) </span>
          </div>
          <div>
            <Tooltip text="Delete Invitation">
              <div class="flex">
                <Button
                  v-if="!pendingToDelete || pendingToDelete != invitation.name"
                  icon="lucide-x"
                  @click="pendingToDelete = invitation.name"
                />
                <Button
                  v-else
                  @click="() => pendingInvitations.delete.submit({ name: invitation.name })"
                  :loading="
                    pendingInvitations.delete.loading &&
                    pendingInvitations.delete.params.name === invitation.name
                  "
                >
                  <span class="text-ink-red-7"> Delete? </span>
                </Button>
              </div>
            </Tooltip>
          </div>
        </li>
      </ul>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Select, Tooltip } from 'frappe-ui'
import { useCall, useList } from 'frappe-ui'
import { GPInvitation } from '@/types/doctypes'
import { users } from '@/data/users'

type Role = 'Gameplan Admin' | 'Gameplan Member'

const role = ref<Role>('Gameplan Member')
const emails = ref('')
const pendingToDelete = ref<string | null>(null)

const description = computed((): string => {
  const descriptions: Record<Role, string> = {
    'Gameplan Admin':
      'Can create communities and spaces, invite admins and users, browse and create discussions.',
    'Gameplan Member': 'Can join communities, create spaces, browse and create discussions.',
  }
  return descriptions[role.value]
})

function getRoleLabel(role: string) {
  return role === 'Gameplan Member' ? 'User' : role.replace('Gameplan ', '')
}

const pendingInvitations = useList<GPInvitation>({
  doctype: 'GP Invitation',
  fields: ['name', 'email', 'role'],
  filters: { status: 'Pending' },
})

/**
 * One call can end three ways per email, so the dialog reports all three.
 * `granted` already had an account here and now hold the role; `invited` were mailed
 * an invitation link; `skipped` needed nothing or could take nothing (already in
 * Gameplan, already invited, or a disabled account).
 */
interface InviteResult {
  granted: string[]
  invited: string[]
  skipped: string[]
}

const result = ref<InviteResult | null>(null)

function plural(count: number, one: string, many: string) {
  return `${count} ${count === 1 ? one : many}`
}

const resultGroups = computed(() => {
  if (!result.value) return []
  const { granted, invited, skipped } = result.value
  const groups: { icon: string; label: string; emails: string[] }[] = []
  if (granted.length) {
    groups.push({
      icon: 'lucide-check',
      label: `${plural(granted.length, 'person', 'people')} given access`,
      emails: granted,
    })
  }
  if (invited.length) {
    groups.push({
      icon: 'lucide-mail',
      label: `${plural(invited.length, 'invitation', 'invitations')} sent`,
      emails: invited,
    })
  }
  if (skipped.length) {
    groups.push({ icon: 'lucide-minus', label: `${skipped.length} skipped`, emails: skipped })
  }
  return groups
})

const inviteByEmail = useCall<
  InviteResult,
  {
    emails: string
    role: string
    projects: string[] | null
  }
>({
  url: '/api/v2/method/gameplan.api.invite_by_email',
  method: 'POST',
  immediate: false,
  onSuccess: (data) => {
    result.value = data
    role.value = 'Gameplan Member'
    emails.value = ''
    pendingInvitations.reload()
    // Someone granted access holds a role now, so they belong in the members list
    // behind this dialog. Reloading is safe here: the app gates on the `usersReady`
    // latch, not on `users.isFinished`, which goes false during any refetch.
    if (data.granted.length) {
      users.reload()
    }
  },
})
</script>
