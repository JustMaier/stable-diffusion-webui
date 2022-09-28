import asyncio
import json
import websockets
import base64
from PIL import Image
from io import BytesIO

default_args = {
    "txt2img": {
        "prompt": "",
        "negative_prompt": "",
        "prompt_style": "",
        "prompt_style2": "",
        "steps": 30,
        "sampler_index": 0,
        "restore_faces": False,
        "tiling": False,
        "n_iter": 1,
        "batch_size": 1,
        "cfg_scale": 7.5,
        "seed": -1,
        "subseed": -1,
        "subseed_strength": 0,
        "seed_resize_from_h": 0,
        "seed_resize_from_w": 0,
        "seed_enable_extras": False,
        "height": 512,
        "width": 512,
        "enable_hr": False,
        "scale_latent": False,
        "denoising_strength": 0
    }
}

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
        if data['type'] == 'request':
            operation = data['payload']['operation']
            if operation in self.operations:
                # TODO: improve arg handling (e.g. support b64 image conversion and arbitrary arg mapping)
                # TODO: test img2img, extras, and png info
                # TODO: handle sending progress updates
                args = default_args[operation].copy()
                args.update(data['payload']['args'])
                images, gen_info, info = self.operations[operation](*args.values(), 0)
                await client.send(to_json({'type': 'result', 'payload': {'images': [image_to_b64(i) for i in images[1:]], 'gen_info': gen_info, 'info': info}}))
            else:
                print(f"Client({client.id}) requested unknown operation: {operation}")
                await client.send(to_json({'type': 'error', 'payload': f"Unknown operation: {operation}"}))

    async def handler(self, client):
        await self.new_client(client)
        async for message in client:
            await self.message_received(client, message)

    async def start(self, port, host):
        async with websockets.serve(self.handler, "", port) as self.server:
            print(f"Websocket server listening at ws://{host}:{port}")
            await asyncio.Future()  # run forever

#region Helpers
def to_json(content):
    return json.dumps(content, default=vars)

def b64_to_image(b64str: str):
  b64str=b64str.split('base64,')[1]
  img_bytes = base64.urlsafe_b64decode(b64str)
  return Image.open(BytesIO(img_bytes))

def image_to_b64(img) -> str:
  buffered=BytesIO()
  img.save(buffered, format="jpeg")
  img_str=(bytes("data:image/jpeg;base64,", encoding='utf-8') + base64.b64encode(buffered.getvalue())).decode('utf-8')

  return img_str
#endregion