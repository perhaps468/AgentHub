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
        if (this.events.has(event)) {
            this.events.get(event)!.forEach(handler => handler(...args));
        }
    }

    clear() {
        this.events.clear();
    }
}

const eventBus = new EventBus();
export default eventBus;