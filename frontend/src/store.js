import { defineStore } from 'pinia'

export const useStore = defineStore('store', {
  state: () => ({
    page_name: 'test-879',
    route: 'pages/hello',
    pages: {},
    active_breakpoint: 'desktop',
    blocks: [],
    device_breakpoints: {
      desktop: {
        icon: 'monitor',
        device: 'desktop',
        width: 1024,
      },
      tablet: {
        icon: 'tablet',
        device: 'tablet',
        width: 640,
      },
      mobile: {
        icon: 'smartphone',
        device: 'mobile',
        width: 320,
      },
    },
  }),
  actions: {
    get_active_breakpoint() {
      return this.device_breakpoints[this.active_breakpoint].width
    },
  },
})
