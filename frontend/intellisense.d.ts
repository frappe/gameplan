import dayjs from 'dayjs'

declare module 'vue' {
  interface ComponentCustomProperties {
    $dayjs: typeof dayjs
  }
}
