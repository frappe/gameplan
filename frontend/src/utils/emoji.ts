/**
 * A reaction value is either a unicode emoji (e.g. "👍") or a custom emoji
 * stored as an uploaded image URL. Custom emoji values are file paths, so they
 * start with "/" or "http".
 */
export function isImageEmoji(value: string): boolean {
  return /^(https?:\/\/|\/)/.test(value)
}
