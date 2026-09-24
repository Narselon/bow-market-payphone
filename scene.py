class Scene:
    def __init__(self, id: str, text: str, connections=None, hidden_options=None, items_granted=None, items_required=None):
        self.id = id
        self.text = text
        self.connections = connections if connections is not None else []
        self.hidden_options = hidden_options if hidden_options is not None else {}
        self.items_granted = items_granted if items_granted is not None else []
        self.items_required = items_required if items_required is not None else []
    def add_connection(self, scene_id):
        self.connections.append(scene_id)
