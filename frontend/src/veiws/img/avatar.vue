<template>
    <div class="avatar" :style="{ backgroundColor, width: size, height: size }">
        <img v-if="info?.avatar && !hasError" :src="info?.avatar" alt="" @error="hasError = true" class="avatar-image"/>
         <template v-else>
                  {{  displayCharacter }}
         </template>
    </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const hasError = ref(false)

const props = defineProps({
  info: Object,
  size: {
    type: String,
    default: '50px',
  },
  color: {
    type: Number,
    default: -1,
  },
})

watch(
  () => props.info?.avatar,
  () => {
    hasError.value = false
  },
)

// 定义背景颜色列表
 const colors = [
        '#1E90FF', // 蓝色
        '#32CD32', // 绿色
        '#FF4500', // 橙色
        '#FF69B4', // 粉色
        '#9370DB', // 紫色
        '#20B2AA', // 青色
        '#FFD700', // 金色
        '#FF6347', // 珊瑚色
        '#4169E1', // 皇家蓝
        '#8B008B', // 深紫色
    ]

const displayCharacter = computed(() => {
  if (!props.info?.name) return ''
  const firstChar = props.info.name.trim().charAt(0)
  // 如果是英文字符，则转换为大写
  return /^[a-zA-Z]$/.test(firstChar) ? firstChar.toUpperCase() : firstChar
})

const backgroundColor = computed(() => {
  if (props.color >= 0) return colors[props.color % colors.length]
  if (!props.info?.name) return colors[0]
  const firstChar = props.info?.name.trim().charAt(0)
  const charCode = firstChar.charCodeAt(0)
  return colors[charCode % colors.length]
})
</script>

<style scoped lang="scss">
.avatar {
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    color: white;
    font-weight: 500;
    text-align: center;
    user-select: none;
    margin: 0;
    overflow: hidden;
    flex-shrink: 0;

    .avatar-image {
      width: 100%;
      height: 100%;
      object-fit: cover;
      border-radius: 50%;
    }
}
</style>
