import Http from '../utils/request'

export default {
  list() {
    return Http.get('/api/v1/user/list')
  },
  onlineWeb() {
    return Http.get('/api/v1/user/online/web')
  },
  update(param: Record<string, unknown>) {
    return Http.post('/api/v1/user/update', param)
  },

}
export  const listMap=()=> Http.get('/api/v1/user/list/map')
