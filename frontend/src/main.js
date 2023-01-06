import { createApp } from 'vue'
import { FrappeUI, Button, FeatherIcon } from 'frappe-ui'
import { createPinia } from 'pinia';
import router from './router'
import App from './App.vue'
import './index.css'

import GridLayout from 'vue3-drr-grid-layout'
import 'vue3-drr-grid-layout/dist/style.css'

const app = createApp(App)
const pinia = createPinia()

app.use(router)
app.use(FrappeUI)
app.use(GridLayout)
app.use(pinia)

app.component('Button', Button)
app.component('FeatherIcon', FeatherIcon)
app.mount('#app')
