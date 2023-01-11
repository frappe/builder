import { defineStore } from 'pinia'

export const useStore = defineStore('store', {
  state: () => ({
    page_name: 'test-879',
    route: 'pages/hello',
    pages: {
      'test-136': {
        page_name: 'test-136',
        route: 'pages/hello',
        options: [
          {
            element: 'span',
            attributes: {
              class:
                'flex items-center cursor-pointer justify-center overflow-auto group-hover:border-2 group-hover:border-blue-200 relative component',
            },
            skipped_attributes: {"draggable": "true", "contenteditable": "true"},
            styles:
              'height: 50px; color: black; background: none; border: none; box-shadow: none; min-width: 50px; width: auto;',
            innerText: 'This is it!',
          },
        ],
      },
      'test-879': {
        page_name: 'test-879',
        route: 'pages/hello-world',
        options: [
          {
            element: 'span',
            attributes: {
              class:
                'flex items-center cursor-pointer justify-center overflow-auto group-hover:border-2 group-hover:border-blue-200 relative component',
            },
            skipped_attributes: {"draggable": "true", "contenteditable": "true"},
            styles:
              'height: 50px; color: black; background: none; border: none; box-shadow: none; min-width: 50px; width: auto;',
            innerText: 'Text',
          },
        ],
      },
    },
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
