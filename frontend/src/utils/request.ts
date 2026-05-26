import axios, {
  type AxiosProgressEvent,
  type AxiosRequestConfig,
  type AxiosResponse,
  type ResponseType,
} from 'axios'
import { useGlobalStore } from '../store/module/useGlobalStore'

const SERVICE_URL = (import.meta.env.VITE_HTTP_URL as string | undefined) || ''
export { SERVICE_URL }

type RequestParams = Record<string, unknown>

type RequestConfig = AxiosRequestConfig & {
  headers?: Record<string, string>
}

// request 请求之前
axios.interceptors.request.use((config) => {
  config.headers = config.headers ?? {}
  config.headers['x-token'] = localStorage.getItem('x-token') ?? ''
  return config
})

// http response 拦截器
axios.interceptors.response.use(
  (response) => {
    const globalStore = useGlobalStore()
    if (response.data.code === 401) {
      globalStore.setGlobalDialog(true, '认证失效', '您的登录过期，请重新登录')
    }
    if (response.data.code === 403) {
      globalStore.setGlobalDialog(true, '请求失败', '您的账号已在其它地方登录，请重新登录')
    }
    return Promise.resolve(response)
  },
  (error) => {
    if (error.response && error.response.data) {
      return Promise.reject(error.response.data)
    }
    return Promise.reject(error.message)
  },
)

export default class Http {
  static send<T = unknown>(config: RequestConfig, loading?: unknown, isBlob = false): Promise<T | AxiosResponse<T>> {
    void loading
    const configs: RequestConfig = Object.assign(
      {
        timeout: 30000,
      },
      config,
    )
    return axios(configs)
      .then((res: AxiosResponse<T>) => {
        if (isBlob) {
          return res
        }
        return res.data
      })
      .catch((error) => {
        throw error
      })
  }

  static post<T = unknown>(url: string, params: RequestParams = {}, loading?: unknown) {
    const config: RequestConfig = {
      method: 'post',
      url: SERVICE_URL + url,
      data: params,
    }
    return Http.send<T>(config, loading)
  }

  static formData<T = unknown>(url: string, params: RequestParams = {}, loading?: unknown) {
    const config: RequestConfig = {
      method: 'post',
      url: SERVICE_URL + url,
      data: params,
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }
    return Http.send<T>(config, loading)
  }

  static delete<T = unknown>(url: string, params: RequestParams = {}, loading?: unknown) {
    const config: RequestConfig = {
      method: 'delete',
      url: SERVICE_URL + url,
      data: params,
    }
    return Http.send<T>(config, loading)
  }

  static put<T = unknown>(url: string, params: RequestParams = {}, loading?: unknown) {
    const config: RequestConfig = {
      method: 'put',
      url: SERVICE_URL + url,
      data: params,
    }
    return Http.send<T>(config, loading)
  }

  static download(url: string, params: RequestParams = {}, loading?: unknown) {
    const config: RequestConfig = {
      responseType: 'blob' as ResponseType,
      method: 'post',
      url: SERVICE_URL + url,
      data: params,
    }
    return Http.send(config, loading, true)
  }

  static get<T = unknown>(url: string, params: RequestParams = {}, loading?: unknown) {
    const urlParams = Object.keys(params).map((key) => `${key}=${encodeURIComponent(String(params[key]))}`)
    const requestUrl = urlParams.length ? `${SERVICE_URL + url}?${urlParams.join('&')}` : SERVICE_URL + url
    const config: RequestConfig = {
      url: requestUrl,
      params: {
        randomTime: new Date().getTime(),
      },
    }
    return Http.send<T>(config, loading)
  }

  static get2<T = unknown>(url: string, params: RequestParams = {}, loading?: unknown) {
    const config: RequestConfig = {
      method: 'post',
      url: SERVICE_URL + url,
      data: params,
      params: {
        randomTime: new Date().getTime(),
      },
    }
    return Http.send<T>(config, loading)
  }

  static post2<T = unknown>(url: string, params: RequestParams = {}, loading?: unknown) {
    const config: RequestConfig = {
      method: 'post',
      url: SERVICE_URL + url,
      headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8' },
      data: params,
    }
    return Http.send<T>(config, loading)
  }

  static upload<T = unknown>(
    url: string,
    formData: FormData,
    loading?: unknown,
    onProgress?: (progressEvent: AxiosProgressEvent) => void,
  ) {
    const config: RequestConfig = {
      method: 'post',
      url: SERVICE_URL + url,
      data: formData,
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: onProgress,
    }
    return Http.send<T>(config, loading)
  }
}

