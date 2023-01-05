import { createApp } from 'vue'
import { FrappeUI, Button } from 'frappe-ui'
import router from './router'
import App from './App.vue'
import './index.css'

import GridLayout from 'vue3-drr-grid-layout'
import 'vue3-drr-grid-layout/dist/style.css'

let app = createApp(App)
app.use(router)
app.use(FrappeUI)
app.use(GridLayout)
app.component('Button', Button)
app.mount('#app')
