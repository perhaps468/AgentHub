import Http from "../utils/request";
import type{ LoginResponse, RegisterResponese ,LoginData} from '../types/login';
type BasicResponse = { code: number; msg: string; data?: unknown }
export const login = (data: any) => Http.post<LoginResponse>('/api/v1/user/login', data);
export const register = (data: any) => Http.post<RegisterResponese>('/api/v1/user/register', data);

export const logout = () => Http.post<BasicResponse>('/api/v1/user/logout');

//获取验证码接口
export const reqCode  = 
    (phone:string) =>
        Http.get<any>('/hosp/hospital/department/' + phone);
//用户登录接口
export const reqUserLogin = 
    (data:LoginData) => 
    Http.post<LoginResponse>('/user/login',data);
    
