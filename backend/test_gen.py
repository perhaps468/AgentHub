import asyncio

class FixedAgentResponder:
    def __init__(self):
        pass

    async def stream_events(self):
        yield 1

r = FixedAgentResponder()
gen = r.stream_events()
print('iscoroutine:', asyncio.iscoroutine(gen))
print('type:', type(gen).__name__)
print('iscoroutinefunction:', asyncio.iscoroutinefunction(r.stream_events))
