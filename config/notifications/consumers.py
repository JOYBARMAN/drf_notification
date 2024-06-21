from channels.consumer import SyncConsumer
from channels.exceptions import StopConsumer


class EchoConsumer(SyncConsumer):

    def websocket_connect(self, event):
        print("connected", event)
        self.send(
            {
                "type": "websocket.accept",
            }
        )

    def websocket_receive(self, event):
        print("received", event)
        self.send(
            {
                "type": "websocket.send",
                "text": event["text"],
            }
        )

    def websocket_disconnect(self, event):
        print("disconnected", event)
        raise StopConsumer()
