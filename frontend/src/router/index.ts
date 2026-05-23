import { createRouter,createWebHashHistory } from "vue-router";
export default createRouter({
    history:createWebHashHistory(),
    routes:[
        {
            path:'/login',
            alias: ['/Login'],
            component:()=>import('../components/Login.vue')
        },{
            path:'/zhu',
            component:()=>import('../components/zhu.vue')
        }, {
            path: '/',
            redirect:'/zhu'
           
    },
    ],
      scrollBehavior(){
        return{
            left:0,
            top:0
        }
    }

})
