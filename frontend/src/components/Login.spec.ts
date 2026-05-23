import { createPinia, setActivePinia } from 'pinia'
import { shallowMount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import Login from './Login.vue'

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}))

vi.mock('../api/login', () => ({
  getCode: vi.fn(),
  login: vi.fn(),
  register: vi.fn(),
}))

vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

describe('Login', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders the unified auth shell with the login card visible by default', () => {
    const wrapper = shallowMount(Login, {
      global: {
        stubs: {
          ElButton: {
            template: '<button><slot /></button>',
          },
        },
      },
    })

    expect(wrapper.find('[data-testid="auth-shell"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="auth-card-login"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="auth-switch-register"]').exists()).toBe(true)
  })
})
