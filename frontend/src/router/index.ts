import { createRouter, createWebHashHistory } from "vue-router";

const router = createRouter({
    history: createWebHashHistory(),
    routes: [
        {
            path: '/login',
            alias: ['/Login'],
            component: () => import('../components/Login.vue'),
        },
        {
            path: '/zhu',
            component: () => import('../components/zhu.vue'),
        },
        {
            path: '/',
            redirect: '/zhu',
        },
    ],
    scrollBehavior() {
        return {
            left: 0,
            top: 0,
        }
    },
})

// 路由守卫：未登录则跳转到登录页
router.beforeEach((to) => {
    if (to.path !== '/login' && !localStorage.getItem('x-token')) {
        return '/login'
    }
})

export default router
