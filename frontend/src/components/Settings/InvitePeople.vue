<template>
  <div class="flex min-h-0 flex-col">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <h2 class="text-xl font-semibold leading-none">Invite People</h2>
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
          <FormControl
            label="Role"
            type="select"
            :options="[
              { label: 'Admin', value: 'Gameplan Admin' },
              { label: 'Member', value: 'Gameplan Member' },
              { label: 'Guest', value: 'Gameplan Guest' },
            ]"
            v-model="role"
          />
          <p class="mt-2 text-base text-ink-gray-8">{{ description }}</p>
        </div>
        <div v-if="role === 'Gameplan Guest'">
          <label class="text-sm leading-4 text-ink-gray-6"> Invite Guest to Spaces </label>
          <div class="mt-2">
            <MultiSelect
              :options="groupedSpaceOptions"
              v-model="selectedProjects"
              placeholder="Select spaces"
              label="Spaces"
              selection-text="spaces"
            />

            {{ selectedProjects }}
          </div>
        </div>
        <ErrorMessage :message="inviteByEmail.error" />
        <Button
          variant="solid"
          @click="
            inviteByEmail.submit({
              emails,
              role,
              projects: selectedProjects.length ? selectedProjects : null,
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
      <ul class="divide-y overflow-auto">
        <li
          class="flex items-center justify-between py-2"
          v-for="invitation in pendingInvitations.data"
          :key="invitation.name"
        >
          <div class="w-4/5 text-base">
            <span class="text-ink-gray-8">
              {{ invitation.email }}
            </span>
            <span class="text-ink-gray-5"> ({{ invitation.role.replace('Gameplan ', '') }}) </span>
          </div>
          <div>
            <Tooltip text="Delete Invitation">
              <div class="flex">
                <Button
                  v-if="!pendingToDelete || pendingToDelete != invitation.name"
                  @click="pendingToDelete = invitation.name"
                >
                  <template #icon>
                    <LucideX class="w-4" />
                  </template>
                </Button>
                <Button
                  v-else
                  @click="() => pendingInvitations.delete.submit({ name: invitation.name })"
                  :loading="
                    pendingInvitations.delete.loading &&
                    pendingInvitations.delete.params.name === invitation.name
                  "
                >
                  <span class="text-ink-red-4"> Delete? </span>
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
import { Tooltip } from 'frappe-ui'
import { useCall, useList } from 'frappe-ui/src/data-fetching'
import { useGroupedSpaceOptions } from '@/data/groupedSpaces'
import MultiSelect from '@/components/MultiSelect.vue'
import { GPInvitation } from '@/types/doctypes'

type Role = 'Gameplan Admin' | 'Gameplan Member' | 'Gameplan Guest'

const role = ref<Role>('Gameplan Member')
const emails = ref('')
const selectedProjects = ref<string[]>([])
const pendingToDelete = ref<string | null>(null)

const groupedSpaceOptions = useGroupedSpaceOptions({ filterFn: (space) => !space.archived_at })

const description = computed((): string => {
  const descriptions: Record<Role, string> = {
    'Gameplan Admin':
      'Can create new teams and projects, invite admins and members, browse and create discussions.',
    'Gameplan Member': 'Can create projects, invite members, browse and create discussions.',
    'Gameplan Guest': 'Can browse and participate in invited teams or projects.',
  }
  return descriptions[role.value]
})

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
    selectedProjects.value = []
    pendingInvitations.reload()
  },
})
</script>
