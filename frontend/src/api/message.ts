import Http from '../utils/request'
import type { MessageResponse, RecordParams, SendMessageParams, SendMessageResponse } from '../types/message'

export const send = (param: SendMessageParams) => Http.post<SendMessageResponse>('/api/v1/message/send', param);

export const record = (param:any) => Http.post<MessageResponse>('/api/v1/message/record', param);//查询聊天记录

export const recall = (param: any) => Http.post('/api/v1/message/recall', param);//撤回消息


