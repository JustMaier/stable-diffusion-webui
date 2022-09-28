import asyncio
import json
import websockets

class WebsocketServer:
    def __init__(self, operations: dict):
        self.clients = set()
        self.server = None
        self.operations = operations

    async def new_client(self, client):
        self.clients.add(client)
        try:
            message = {'type': 'message', 'payload': f"Hey all, a new Client {client.id} has joined us"}
            websockets.broadcast(self.clients, to_json(message))
        finally:
            self.clients.remove(client)
            print(f"Client({client.id}) disconnected")

    async def message_received(self, client, message):
        print(f"Client({client.id}) said: {message[:200]} ({len(message)})")

        data = json.loads(message)
        if data['type'] == 'operation':
            operation = data['payload']
            if operation in self.operations:
                processed_images, gen_info, info = await self.operations[operation](client, **data['data'])
            else:
                print(f"Client({client.id}) requested unknown operation: {operation}")
                await client.send(to_json({'type': 'error', 'payload': f"Unknown operation: {operation}"}))

    async def handler(self, client):
        self.new_client(client)
        async for message in client:
            await self.message_received(client, message)

    def start(self, port, host):
        self.server = websockets.serve(self.handler, host, port)
        asyncio.get_event_loop().run_until_complete(self.server)
        asyncio.get_event_loop().run_forever()

#region Helpers
def to_json(content):
    return json.dumps(content, default=vars)
#endregion