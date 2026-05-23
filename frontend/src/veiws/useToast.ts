import { inject, type InjectionKey } from 'vue'

export type ShowToast = (message: string, error?: boolean, duration?: number) => void

export const ToastSymbol: InjectionKey<ShowToast> = Symbol('toast')

export const useToast = (): ShowToast => {
  return inject(ToastSymbol, () => {})
}
