// 用户徽章类型
export type UserBadge = 'clover' | 'diamond'

// 用户类型
export type UserType = 'user' | 'bot'

// 单个用户信息
export interface UserMapItem {
    id: string
    name: string
    avatar: string | null
    type: UserType
    badge: UserBadge[] | null
}

// 用户映射表
export interface UserMap {
    [key: string]: UserMapItem
}

// 用户列表响应
export interface UserMapResponse {
    code: number
    msg: string
    data: UserMap
}
