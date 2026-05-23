/*import { ref ,watch} from 'vue'

type EventHandler = (...args: any[]) => void;

class EventBus {
    private events: Map<string, Set<EventHandler>> = new Map();

    on(event: string, handler: EventHandler) {
        if (!this.events.has(event)) {
            this.events.set(event, new Set());
        }
        this.events.get(event)!.add(handler);
    }

    off(event: string, handler: EventHandler) {
        if (this.events.has(event)) {
            this.events.get(event)!.delete(handler);
        }
    }

    emit(event: string, ...args: any[]) {
        console.log(`EventBus: 触发事件 "${event}"`, args);
        if (this.events.has(event)) {
            this.events.get(event)!.forEach(handler => handler(...args));
        }
    }

    clear() {
        this.events.clear();
    }

}
export const currentTargetEventBus = {
  target: ref(null),
  setTarget(target: any) {
    this.target.value = target
  },
  subscribe(callback: (target: any) => void) {
    const stop = watch(this.target, callback, { deep: true });
    return stop; // 返回停止监听的函数
  }
}
const eventBus = new EventBus();
export default eventBus;*/
import mitt from 'mitt'
import { ref ,watch} from 'vue'
const eventBus = mitt()
export default eventBus
export const currentTargetEventBus = {
  target: ref(null),
  setTarget(target: any) {
    this.target.value = target
  },
  subscribe(callback: (target: any) => void) {
    const stop = watch(this.target, callback, { deep: true });
    return stop; // 返回停止监听的函数
  }
}
