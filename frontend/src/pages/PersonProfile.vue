<template>
  <div v-if="profile">
    <div>
      <CoverImage
        :imageUrl="profile.cover_image"
        :imagePosition="profile.cover_image_position"
        :editable="$isSessionUser(profile.user)"
        @change="
          ({ imageUrl, imagePosition }) => {
            $resources.profile.setValue.submit({
              cover_image: imageUrl,
              cover_image_position: imagePosition,
            })
          }
        "
      />
    </div>
    <div class="-mt-16 inline-flex translate-y-0 px-6">
      <ImagePreview
        v-model:show="imagePreview.show"
        :imageUrl="imagePreview.imageUrl"
      />
      <button
        v-if="currentUser.user_image"
        @click="
          () => {
            imagePreview.imageUrl = currentUser.user_image
            imagePreview.show = true
          }
        "
        class="rounded-full bg-white outline-none focus:ring"
        :class="{
          'hover:opacity-80': $isSessionUser(profile.user),
        }"
      >
        <UserImage
          class="h-32 w-32 rounded-full border-4 border-white object-cover"
          :user="currentUser.name"
        />
      </button>
      <button
        v-else
        @click="editDialog.show = true"
        class="h-32 w-32 rounded-full border-4 border-white bg-gray-200 text-sm text-gray-600"
        :class="{ 'hover:bg-gray-300': $isSessionUser(profile.user) }"
        :disabled="!$isSessionUser(profile.user)"
      >
        <span v-if="$isSessionUser(profile.user)"> Upload Image </span>
      </button>
    </div>
    <div class="sticky top-0 z-10 border-b bg-white px-4 sm:px-6">
      <div class="flex items-center justify-between pt-2">
        <div class="items-baseline sm:flex">
          <h2 class="text-3xl font-bold leading-none text-gray-900">
            {{ user ? user.full_name : profile.full_name }}
          </h2>
          <span class="hidden px-1 text-gray-600 sm:inline">&middot;</span>
          <p v-if="profile.bio" class="mt-2 text-lg sm:mt-0">
            {{ profile.bio }}
          </p>
        </div>
        <Button
          v-if="$isSessionUser(profile.user)"
          @click="editDialog.show = true"
          appearance="minimal"
          class="whitespace-nowrap"
        >
          Edit Profile
        </Button>
      </div>
      <Tabs class="border-none" :tabs="tabs" />
    </div>
    <div class="mx-auto max-w-4xl sm:px-5">
      <router-view :profile="$resources.profile" />
    </div>
    <Dialog
      v-if="$isSessionUser(profile.user)"
      :options="{ title: 'Edit Profile' }"
      v-model="editDialog.show"
      @after-leave="discard"
    >
      <template #body-content>
        <div class="space-y-4">
          <ProfileImageEditor
            :profile="$resources.profile"
            v-if="editDialog.editingProfilePhoto"
          />
          <template v-else>
            <div class="flex items-center gap-4">
              <UserAvatar size="lg" :user="profile.user" />
              <Button @click="editDialog.editingProfilePhoto = true">
                Edit Profile Photo
              </Button>
            </div>
            <Input label="First Name" v-model="user.first_name" />
            <Input label="Last Name" v-model="user.last_name" />
            <Input
              label="Bio"
              v-model="profile.bio"
              type="textarea"
              maxlength="280"
            />
          </template>
        </div>
      </template>
      <template #actions>
        <Button
          appearance="primary"
          @click="save"
          :loading="
            $resources.user.setValue.loading ||
            $resources.profile.setValue.loading
          "
        >
          Save
        </Button>
        <Button @click="editDialog.show = false"> Discard </Button>
      </template>
    </Dialog>
  </div>
</template>
<script>
import { Dialog, FileUploader } from 'frappe-ui'
import CoverImage from '@/components/CoverImage.vue'
import Tabs from '@/components/Tabs.vue'
import ImagePreview from '../components/ImagePreview.vue'
import ColorPicker from '@/components/ColorPicker.vue'
import ProfileImageEditor from '@/components/ProfileImageEditor.vue'
import UserImage from '@/components/UserImage.vue'

export default {
  name: 'PersonProfile',
  props: ['personId'],
  components: {
    CoverImage,
    Dialog,
    FileUploader,
    Tabs,
    ImagePreview,
    ColorPicker,
    ProfileImageEditor,
    UserImage,
  },
  data() {
    return {
      editing: false,
      editDialog: { show: false, editingProfilePhoto: false },
      profilePhotoDialog: { show: false },
      imagePreview: { show: false, imageUrl: null },
    }
  },
  resources: {
    profile() {
      return {
        type: 'document',
        doctype: 'GP User Profile',
        name: this.personId,
        realtime: true,
        whitelistedMethods: {
          setImage: 'set_image',
          removeImageBackground: 'remove_image_background',
          revertImageBackground: 'revert_image_background',
        },
      }
    },
    user() {
      if (!this.profile || !this.$isSessionUser(this.profile.user)) return
      return {
        type: 'document',
        doctype: 'User',
        name: this.profile.user,
        realtime: true,
      }
    },
  },
  computed: {
    profile() {
      return this.$resources.profile.doc
    },
    user() {
      return this.$resources.user?.doc
    },
    currentUser() {
      return this.$user(this.profile.user)
    },
    tabs() {
      return [
        {
          name: 'About me',
          route: {
            name: 'PersonProfileAboutMe',
            params: { personId: this.personId },
          },
          isActive: this.$route.name == 'PersonProfileAboutMe',
        },
        {
          name: 'Posts',
          route: {
            name: 'PersonProfilePosts',
            params: { personId: this.personId },
          },
          isActive: this.$route.name == 'PersonProfilePosts',
        },
      ]
    },
  },
  methods: {
    save() {
      this.$resources.user.setValue
        .submit({
          first_name: this.user.first_name,
          last_name: this.user.last_name,
        })
        .then(() => {
          this.$resources.profile.setValue.submit({
            bio: this.profile.bio,
          })
          this.editDialog.show = false
        })
    },
    discard() {
      this.$resources.user.reload()
      this.$resources.profile.reload()
      this.editDialog = this.$options.data().editDialog
    },
    setUserImage(url) {
      this.$resources.user.setValue.submit({ user_image: url })
      this.currentUser.user_image = url
    },
  },
  pageMeta() {
    return {
      title: [this.profile?.full_name || '', 'Profile'].join(' - '),
      emoji: '👨‍👩‍👧‍👦',
    }
  },
}
</script>
