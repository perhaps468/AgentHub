<template>
  <span v-if="isArrayContents" class="text-msg">
    <template v-for="item in contents" :key="item.id">
      <span v-if="item.type === TextContentType.At" class="text-msg-at" >
        {{ `@${getUserInfo(item.content).name}` }}
      </span>
      <span v-if="item.type === TextContentType.Text">
        {{ item.content }}
      </span>
    </template>
  </span>
  <div v-else>
    {{ props.msg.message }}
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { TextContentType } from '../../types/textContentType'
const props = defineProps({ msg: Object, right: Boolean })
const contents = ref()
const nodeList =ref()
/*
watch(
  () => props.msg,
  () => {
    try {
      contents.value = JSON.parse(props.msg?.message).map((item) => {
       
        console.log('item.content',item.content);
       
        console.log('item',item);
        if (item.content) {
          try {
            item.content = JSON.parse(item.content);
          } catch {
          }
        }
        return item;
      });
    } catch {
      contents.value = props.msg?.message;
      
    }
  },
  { immediate: true },
)*/
watch(
  () => props.msg,
  () => {
    try {
      contents.value = JSON.parse(props.msg?.message).map((item) => {
        // 如果item.content是字符串，尝试解析
        if (typeof item.content === 'string') {
          try {
            item.content = JSON.parse(item.content);
          } catch {
            // 解析失败，保持原样
          }
        }
        return item;
      });
    } catch {
      contents.value = props.msg?.message;
    }
  },
  { immediate: true },
);


console.log('contents',contents.value);
const isArrayContents = computed(() => Array.isArray(contents.value))
console.log('isArrayContents', isArrayContents);
console.log('msg5', props.msg);
const getUserInfo = (content) => {
  try {
    if (typeof content === 'object') {
      console.log('co',content);
      
      return content;
    }
    return JSON.parse(content);
  } catch {
    console.log('no content',content);
    
    return content;
  }
}
 
</script>

<style lang="less" scoped>
.text-msg {
  .text-msg-at {
    color:aqua;
    font-style: italic;
    margin: 0 2px;
    cursor: pointer;
    font-weight: 600;
    display: inline-block;

    &.right {
      color: white;
    }
  }
}
</style>