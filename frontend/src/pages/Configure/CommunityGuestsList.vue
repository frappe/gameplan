<template>
  <div v-if="communityGuests.length">
    <div class="mb-4">
      <h2 class="text-lg-medium text-ink-gray-9">Guests</h2>
      <p class="mt-1 text-base text-ink-gray-5">
        Guests are invited to specific spaces and do not become community members.
      </p>
    </div>

    <List
      :columns="{
        base: ['1.25rem', 'minmax(0,1fr)', '2rem'],
        md: ['1.25rem', 'minmax(12rem,1fr)', 'minmax(12rem,1fr)', '8rem', '3rem'],
      }"
    >
      <ListHeader class="max-md:hidden">
        <ListHeaderCell class="col-span-2">Guest</ListHeaderCell>
        <ListHeaderCell>Email</ListHeaderCell>
        <ListHeaderCell>Spaces</ListHeaderCell>
        <ListHeaderCell />
      </ListHeader>
      <ListRow v-for="guest in communityGuests" :key="guest.key" class="h-10">
        <ListCell>
          <UserAvatar :user="guest.user" size="sm" class="shrink-0" />
        </ListCell>

        <ListCell>
          <div class="min-w-0">
            <div class="truncate text-base-medium text-ink-gray-7">
              {{ guest.fullName }}
            </div>
            <div class="mt-1 flex flex-wrap gap-x-2 gap-y-1 text-base text-ink-gray-5 md:hidden">
              <span>{{ guest.email }}</span>
              <span>{{ guest.spacesLabel }}</span>
            </div>
          </div>
        </ListCell>

        <ListCell class="max-md:hidden">
          <div class="w-full truncate text-base text-ink-gray-5">{{ guest.email }}</div>
        </ListCell>
        <ListCell class="max-md:hidden">
          <div class="w-full truncate text-base text-ink-gray-5">{{ guest.spacesLabel }}</div>
        </ListCell>
        <ListCell class="justify-end">
          <Button
            v-if="canManage"
            variant="ghost"
            size="xs"
            icon="lucide-x"
            :label="guest.pending ? 'Delete invite' : 'Remove guest'"
            @click="removeGuest(guest)"
          />
        </ListCell>
      </ListRow>
    </List>
    <ErrorMessage class="mt-2" :message="teams.runDocMethod.error" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, dialog, ErrorMessage, useDoctype, useList } from 'frappe-ui'
import { List, ListCell, ListHeader, ListHeaderCell, ListRow } from 'frappe-ui/list'
import UserAvatar from '@/components/UserAvatar.vue'
import type { Community } from '@/data/communities'
import { getSpace, spaces } from '@/data/spaces'
import { useUser } from '@/data/users'
import type { GPGuestAccess, GPInvitation, GPTeam } from '@/types/doctypes'

const props = defineProps<{
  community: Community
  canManage: boolean
}>()

const teams = useDoctype<GPTeam>('GP Team')
const communitySpaceNames = computed(() => {
  return new Set(
    (spaces.data || [])
      .filter((space) => space.team === props.community.name)
      .map((space) => space.name),
  )
})

const guestAccess = useList<GPGuestAccess>({
  doctype: 'GP Guest Access',
  fields: ['name', 'user', 'project', 'team'],
  filters: () => {
    const projectNames = Array.from(communitySpaceNames.value)
    return projectNames.length ? { project: ['in', projectNames] } : { project: '__no-space__' }
  },
})

const pendingGuestInvitations = useList<GPInvitation>({
  doctype: 'GP Invitation',
  fields: ['name', 'email', 'projects', 'role', 'status'],
  filters: {
    role: 'Gameplan Guest',
    status: 'Pending',
  },
})

const communityGuests = computed(() => {
  const guests = new Map<string, GuestSummary>()

  for (const access of guestAccess.data || []) {
    addGuestSummary(guests, {
      key: access.user,
      user: access.user,
      fullName: useUser(access.user).full_name,
      email: useUser(access.user).email,
      projectNames: [access.project],
      pending: false,
      invitationNames: [],
    })
  }

  for (const invitation of pendingGuestInvitations.data || []) {
    const projectNames = parseProjectNames(invitation.projects).filter((project) =>
      communitySpaceNames.value.has(project),
    )
    if (!projectNames.length) continue

    addGuestSummary(guests, {
      key: `pending:${invitation.email}`,
      user: invitation.email,
      fullName: invitation.email,
      email: invitation.email,
      projectNames,
      pending: true,
      invitationNames: [invitation.name],
    })
  }

  return Array.from(guests.values())
    .map((guest) => ({
      ...guest,
      spacesLabel: formatSpacesLabel(guest.projectNames),
    }))
    .sort((a, b) => a.fullName.localeCompare(b.fullName))
})

type GuestSummary = {
  key: string
  user: string
  fullName: string
  email: string
  projectNames: string[]
  pending: boolean
  invitationNames: string[]
}

function addGuestSummary(guests: Map<string, GuestSummary>, guest: GuestSummary) {
  const existingGuest = guests.get(guest.key)
  if (!existingGuest) {
    guests.set(guest.key, {
      ...guest,
      projectNames: uniqueProjectNames(guest.projectNames),
    })
    return
  }

  existingGuest.projectNames = uniqueProjectNames([
    ...existingGuest.projectNames,
    ...guest.projectNames,
  ])
  existingGuest.invitationNames = uniqueProjectNames([
    ...existingGuest.invitationNames,
    ...guest.invitationNames,
  ])
}

function removeGuest(guest: GuestSummary) {
  if (!props.canManage) return

  if (guest.pending) {
    deletePendingInvitation(guest)
    return
  }

  dialog.confirm({
    title: 'Remove guest',
    message: `${guest.fullName} will lose access to spaces in this community.`,
    confirmLabel: 'Remove',
    onConfirm: async () => {
      await teams.runDocMethod.submit({
        name: props.community.name,
        method: 'remove_guest_access',
        params: { user: guest.user },
      })
      await guestAccess.reload()
    },
  })
}

function deletePendingInvitation(guest: GuestSummary) {
  dialog.confirm({
    title: 'Delete invitation',
    message: `${guest.email} will no longer be able to accept this guest invitation.`,
    confirmLabel: 'Delete',
    onConfirm: async () => {
      await Promise.all(
        guest.invitationNames.map((invitation) =>
          teams.runDocMethod.submit({
            name: props.community.name,
            method: 'remove_guest_invitation',
            params: { invitation },
          }),
        ),
      )
      await pendingGuestInvitations.reload()
    },
  })
}

function parseProjectNames(projects?: string) {
  if (!projects) return []

  try {
    const value = JSON.parse(projects)
    return Array.isArray(value) ? value.map(String) : []
  } catch {
    return []
  }
}

function formatSpacesLabel(projectNames: string[]) {
  return projectNames
    .map((project) => getSpace(project)?.title || project)
    .sort((a, b) => a.localeCompare(b))
    .join(', ')
}

function uniqueProjectNames(projectNames: string[]) {
  return Array.from(new Set(projectNames.filter(Boolean)))
}
</script>
