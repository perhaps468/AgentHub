import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'

import ChatInputArea from './Chat-input-area.vue'

describe('ChatInputArea', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders a wechat-like composer with two tools and a disabled send button by default', async () => {
    const wrapper = mount(ChatInputArea, {
      props: {
        sessionId: '2',
      },
      global: {
        stubs: {
          Input: {
            props: ['value'],
            emits: ['update:value', 'send'],
            template:
              '<textarea data-testid="composer-editor" :value="value" @input="$emit(\'update:value\', $event.target.value)" />',
          },
        },
      },
    })

    expect(wrapper.find('.composer-toolbar').exists()).toBe(true)
    expect(wrapper.findAll('.tool-btn')).toHaveLength(4)
    expect(wrapper.find('.send-btn').attributes('disabled')).toBeDefined()

    await wrapper.find('[data-testid="composer-editor"]').setValue('hello')

    expect(wrapper.find('.send-btn').attributes('disabled')).toBeUndefined()
  })
})
