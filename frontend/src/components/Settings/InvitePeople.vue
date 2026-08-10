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
          Send invitation
        </Button>
      </template>
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

const inviteByEmail = useCall<
  undefined,
  {
    emails: string
    role: string
    projects: string[] | null
  }
>({
  url: '/api/v2/method/gameplan.api.invite_by_email',
  method: 'POST',
  immediate: false,
  onSuccess: () => {
    role.value = 'Gameplan Member'
    emails.value = ''
    pendingInvitations.reload()
  },
})
</script>
