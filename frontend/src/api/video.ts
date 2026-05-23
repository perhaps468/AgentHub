import Http from '../utils/request'
export const offer=(param:any)=>Http.post(`/api/v1/call/offer`, param)
export const answer=(param:any)=>Http.post(`/api/v1/call/answer`, param)
export const candidate=(param:any)=>Http.post(`/api/v1/call/candidate`, param)
export const hangup=(param:any)=>Http.post(`/api/v1/call/hangup`, param)
export const invite=(param:any)=>Http.post(`/api/v1/call/invite`, param)
export const accept=(param:any)=>Http.post(`/api/v1/call/accept`, param)