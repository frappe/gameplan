import { gemoji } from 'gemoji'
import { getRandomNumber } from '@/utils'

/**
 * A reaction value is either a unicode emoji (e.g. "👍") or a custom emoji
 * stored as an uploaded image URL. Custom emoji values are file paths, so they
 * start with "/" or "http".
 */
export function isImageEmoji(value: string): boolean {
  return /^(https?:\/\/|\/)/.test(value)
}

/** Any unicode emoji, picked at random. Custom emoji are never returned. */
export function randomEmoji(): string {
  return gemoji[getRandomNumber(0, gemoji.length - 1)].emoji
}
