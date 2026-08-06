import { useFileUpload, type UploadOptions, type UploadedFile } from 'frappe-ui'

/**
 * Every kind of image Gameplan uploads, and how it should be stored.
 *
 * There is no default. A new upload site has to name its kind, because the two
 * upload primitives disagree about what happens when you say nothing: frappe-ui's
 * `FileUploader` uploads private, `useFileUpload()` uploads public. Leaving that
 * to the call site is how the same avatar ended up private on one screen and
 * public on another.
 *
 * `private: true` does not mean "only the uploader can see it". A private File is
 * readable by anyone who can read the document it is attached to, so for those
 * kinds the attachment is the thing that matters and each one below names the
 * document it attaches to.
 *
 * A kind is only public when something has to fetch it with **no session at all**,
 * which today means an image rendered in an email. Attachment cannot help there,
 * because there is nobody to delegate the permission to.
 */
export const IMAGE_UPLOAD_KINDS = {
  /**
   * Profile photo.
   *
   * Public on purpose. Do not flip this back thinking it is an oversight: an
   * avatar is fetched by readers with no session. Every digest email renders it
   * as `<img src>` (gameplan/templates/emails/email_digest.html), and a mail
   * client sends no cookie, so a private file 403s and the reader gets a broken
   * image rather than the initials fallback. The planned anonymous read tier
   * needs the same thing.
   */
  avatar: { private: false, optimize: true, extensions: ['png', 'jpg', 'jpeg'] },
  /**
   * Profile or space cover. Private: nothing renders a cover without a session.
   * Readable because the File is attached to GP User Profile when it saves.
   */
  cover: { private: true, optimize: true, extensions: ['png', 'jpg', 'jpeg'] },
  /**
   * Bento card image. Private: only rendered on a profile page, behind login.
   * Readable because `attach_bento_card_images` attaches it to GP User Profile.
   */
  bentoCard: { private: true, optimize: true, extensions: ['png', 'jpg', 'jpeg'] },
  /**
   * Community image.
   *
   * Public for the same reason as the avatar: digest emails group unread
   * discussions by community and render this image with no session
   * (`email_digest.format_discussion_groups`).
   */
  communityImage: { private: false, optimize: true, extensions: ['png', 'jpg', 'jpeg'] },
  /**
   * Custom emoji. Private: emails report reactions as a count ("3 reactions"),
   * never as images, so nothing fetches one without a session. Readable because
   * the File attaches to GP Custom Emoji on insert. Never optimized: the whole
   * point of a party parrot is that it is still animated afterwards.
   */
  customEmoji: {
    private: true,
    optimize: false,
    extensions: ['png', 'jpg', 'jpeg', 'gif', 'webp'],
  },
} as const satisfies Record<string, ImageUploadSpec>

interface ImageUploadSpec {
  private: boolean
  optimize: boolean
  extensions: string[]
}

export type ImageUploadKind = keyof typeof IMAGE_UPLOAD_KINDS

const MIME_TYPES: Record<string, string> = {
  png: 'image/png',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  gif: 'image/gif',
  webp: 'image/webp',
}

/** Upload options for a kind, in the shape `FileUploader`'s `uploadArgs` expects. */
export function imageUploadArgs(kind: ImageUploadKind): UploadOptions {
  const spec = IMAGE_UPLOAD_KINDS[kind]
  return { private: spec.private, optimize: spec.optimize }
}

/** `accept` values for a kind, deduped so `jpg` and `jpeg` do not both appear. */
export function imageFileTypes(kind: ImageUploadKind): string[] {
  return [...new Set(IMAGE_UPLOAD_KINDS[kind].extensions.map((ext) => MIME_TYPES[ext]))]
}

/**
 * Reject a file the server would reject anyway, but before it is uploaded, so the
 * error lands next to the button instead of arriving as a failed request.
 */
export function validateImageFile(kind: ImageUploadKind, file: File): string | undefined {
  const extensions = IMAGE_UPLOAD_KINDS[kind].extensions
  const extension = file.name.split('.').pop()?.toLowerCase()
  if (!extension || !extensions.includes(extension)) {
    return `Only ${formatExtensionList(extensions)} images are allowed`
  }
}

function formatExtensionList(extensions: readonly string[]) {
  // "jpg" and "jpeg" are one choice to a reader, even though both are accepted.
  const labels = [...new Set(extensions.map((ext) => (ext === 'jpeg' ? 'jpg' : ext)))].map((ext) =>
    ext.toUpperCase(),
  )
  if (labels.length === 1) return labels[0]
  return `${labels.slice(0, -1).join(', ')} and ${labels[labels.length - 1]}`
}

/**
 * Upload an image without a file picker, for the screens that already hold a File
 * (the avatar cropper hands over a re-encoded blob). The component equivalent is
 * `ImageUploader.vue`; both read the same table above.
 */
export function useImageUpload() {
  const upload = useFileUpload()

  return {
    ...upload,
    upload: (file: File, kind: ImageUploadKind): Promise<UploadedFile> =>
      upload.upload(file, imageUploadArgs(kind)),
  }
}
