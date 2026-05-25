import { createApp } from 'vue'
import './style.css'
import './style/reset.scss'
import App from './App.vue'
import router from './router';
import { createPinia } from 'pinia';
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
const app = createApp(App);
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
  }
const pinia = createPinia();
pinia.use(piniaPluginPersistedstate)
app.use(ElementPlus)
app.use(router);
app.use(pinia);
app.mount('#app');
