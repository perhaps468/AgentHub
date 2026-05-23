import { defineStore } from "pinia";
export const useGlobalStore=defineStore ('global',{
    state:()=>({
          isOpenGlobalDialog: false,
            dialogTitle: '',
            dialogContent: '',
    }),
    actions: {
    setGlobalDialog(isOpen: boolean, title: string, content: string) {
      this.isOpenGlobalDialog = isOpen
      this.dialogTitle = title
      this.dialogContent = content
    },
    closeGlobalDialog() {
      this.isOpenGlobalDialog = false
    },
  },
})