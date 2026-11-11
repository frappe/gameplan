<template>
  <Dialog v-model:open="open" title="Invite people">
    <div class="space-y-4">
      <EmailListInput
        ref="emailInput"
        v-model="emails"
        label="Invite by email"
        :disabled="inviteByEmail.loading"
      />
      <div>
        <Select label="Role" :options="roleOptions" v-model="role" />
        <p class="mt-1.5 text-p-sm text-ink-gray-5">{{ roleDescriptions[role] }}</p>
      </div>

      <!-- One call can end three ways per email, so the result is grouped instead of
           summarized: the admin needs to see which address landed in which bucket. -->
      <div v-if="resultGroups.length" class="rounded-4 bg-surface-gray-2 p-3">
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
          Skipped emails already have access, have a pending invite, or belong to a disabled
          account.
        </p>
      </div>

      <div v-if="pendingInvitations.data?.length">
        <div class="border-b py-2 text-base text-ink-gray-5">Pending invites</div>
        <ul class="divide-y">
          <li
            class="flex items-center justify-between py-2"
            v-for="invitation in pendingInvitations.data"
            :key="invitation.name"
          >
            <div class="w-4/5 text-base">
              <span class="text-ink-gray-8">{{ invitation.email }}</span>
              <span class="text-ink-gray-5"> ({{ roleLabel(invitation.role) }})</span>
            </div>
            <Tooltip text="Delete invitation">
              <div class="flex">
                <Button
                  v-if="pendingToDelete !== invitation.name"
                  icon="lucide-x"
                  @click="pendingToDelete = invitation.name"
                />
                <Button
                  v-else
                  @click="pendingInvitations.delete.submit({ name: invitation.name })"
                  :loading="pendingInvitations.delete.isLoading(invitation.name)"
                >
                  <span class="text-ink-red-7">Delete?</span>
                </Button>
              </div>
            </Tooltip>
          </li>
        </ul>
      </div>
    </div>

    <template #actions="{ close }">
      <div class="flex items-center justify-end gap-2">
        <ErrorMessage
          v-if="inviteByEmail.error"
          class="mr-auto"
          role="alert"
          :message="errorText(inviteByEmail.error, 'Could not send the invitations. Try again.')"
        />
        <Button :label="result ? 'Done' : 'Cancel'" @click="close" />
        <Button
          variant="solid"
          label="Invite"
          :disabled="!parsed.emails.length"
          :loading="inviteByEmail.loading"
          @click="invite"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, useTemplateRef, watch } from 'vue'
import { Button, Dialog, ErrorMessage, Select, Tooltip, useCall, useList } from 'frappe-ui'
import EmailListInput, { parseEmailList } from '@/components/EmailListInput.vue'
import type { GPInvitation } from '@/types/doctypes'
import { users } from '@/data/users'
import { errorText } from '@/utils'

type Role = 'Gameplan Admin' | 'Gameplan Member'

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

const open = defineModel<boolean>('open', { required: true })

const roleOptions: { label: string; value: Role }[] = [
  { label: 'Admin', value: 'Gameplan Admin' },
  { label: 'User', value: 'Gameplan Member' },
]
const roleDescriptions: Record<Role, string> = {
  'Gameplan Admin':
    'Can create communities and spaces, invite admins and users, browse and create discussions.',
  'Gameplan Member': 'Can join communities, create spaces, browse and create discussions.',
}

const role = ref<Role>('Gameplan Member')
const emails = ref('')
const pendingToDelete = ref<string | null>(null)
const result = ref<InviteResult | null>(null)
const emailInput = useTemplateRef('emailInput')
const parsed = computed(() => parseEmailList(emails.value))

const pendingInvitations = useList<GPInvitation>({
  doctype: 'GP Invitation',
  fields: ['name', 'email', 'role'],
  filters: { status: 'Pending' },
})

const inviteByEmail = useCall<InviteResult, { emails: string; role: Role; projects: null }>({
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

// The last result and error describe addresses that are no longer in the box.
watch(emails, (text) => {
  if (!text) return
  result.value = null
  inviteByEmail.reset()
})

function invite() {
  if (!emailInput.value?.validate()) return
  inviteByEmail
    .submit({ emails: parsed.value.emails.join(','), role: role.value, projects: null })
    .catch(() => {})
}

function roleLabel(role: string) {
  return roleOptions.find((option) => option.value === role)?.label ?? role.replace('Gameplan ', '')
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

function plural(count: number, one: string, many: string) {
  return `${count} ${count === 1 ? one : many}`
}
</script>
