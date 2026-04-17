import json
from channels.generic.websocket import AsyncWebsocketConsumer

class AlertConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = 'system_alerts'
        
        # Join room group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    # Receive message from room group
    async def send_alert(self, event):
        alert_data = event['alert']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'new_alert',
            'data': alert_data
        }))
