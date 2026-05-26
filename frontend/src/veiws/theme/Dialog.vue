<template>
  <Modal v-model:is-open="isOpen">
    <div class="w-screen h-screen flex justify-center items-center">
      <div class="custom-dialog">
        <div class="flex justify-between items-center mb-[10px]">
          <div class="font-[600] text-[20px]">{{ props.title }}</div>
        </div>
        <div class="flex-1">
          <div>{{ props.content }}</div>
        </div>
        <div class="flex justify-end">
          <Button type="minor" style="width: 80px" @click="onCancel">取 消</Button>
          <Button style="width: 80px; margin-left: 10px" @click="onOk">确 定</Button>
        </div>
      </div>
    </div>
  </Modal>
</template>
<script setup>
import Modal from './Modal.vue'
import Button from './Button.vue'

const props = defineProps({
  title: {
    default: '',
  },
  content: {
    default: '',
  },
})

const emit = defineEmits(['cancel', 'ok'])
const isOpen = defineModel('isOpen')

const onCancel = () => {
  emit('cancel')
}

const onOk = () => {
  emit('ok')
}
</script>

<style lang="less" scoped>
.custom-dialog {
  width: 400px;
  background-color: rgb(var(--surface-color));
  border-radius: var(--radius-md);
  padding: 24px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);

  .close-icon {
    background-color: transparent;
    transition: all 0.15s ease;

    &:hover {
      color: rgb(var(--danger-color));
      background: rgba(239, 68, 68, 0.08);
    }
  }

  @media screen and (max-width: 500px) {
    width: 90%;
  }
}
</style>
