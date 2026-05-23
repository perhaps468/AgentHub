import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'

import MsgContent from './msg_content .vue'

describe('MsgContent', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('shows quick actions in the context menu on right click', async () => {
    const wrapper = mount(MsgContent, {
      props: {
        right: false,
        msg: {
          id: 'msg-1',
          type: 'text',
          message: 'hello world',
        },
      },
      global: {
        stubs: {
          TextMsg: { template: '<div>text</div>' },
          EmojiMsg: { template: '<div>emoji</div>' },
          call_msg: { template: '<div>call</div>' },
          transition: false,
        },
      },
    })

    expect(wrapper.find('.ctx-menu').exists()).toBe(false)

    await wrapper.find('.msg-content').trigger('contextmenu', {
      clientX: 120,
      clientY: 80,
    })
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(document.querySelector('.ctx-menu')).not.toBeNull()
    expect(document.querySelectorAll('.ctx-menu-item')).toHaveLength(2)
  })
})
