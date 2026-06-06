import { agenthubRequest } from '@/api/client'

export default {
  list() {
    return agenthubRequest.get('/v1/user/list')
  },
  onlineWeb() {
    return agenthubRequest.get('/v1/user/online/web')
  },
  update(param: Record<string, unknown>) {
    return agenthubRequest.post('/v1/user/update', param)
  },

}
export const listMap = () => agenthubRequest.get('/v1/user/list/map')
