# own
from data import Offsets


class ReadManager:

    def __init__(self, pm, base_address):
        self.pm = pm
        self.base_address = base_address
        self.champion_list = Offsets.champion_list
        self.minion_list = Offsets.minion_list
        self.name = Offsets.obj_name
        self.team = Offsets.obj_team

    def is_valid_pointer(self, pointer, champions, team):
        # Get 5 pointers only.
        try:
            pointer_name = self.pm.read_string(pointer + self.name).lower()
            pointer_team = self.pm.read_int(pointer + self.team)
            if pointer_name in champions and pointer_team != team:
                return pointer
        except:
            return None

        # If there's a custom target in practice mode.
        try:
            pointer_name = self.pm.read_string(self.pm.read_longlong(pointer + self.name)).lower()
            pointer_team = self.pm.read_int(pointer + self.team)
            if pointer_name.startswith('practicetool') and pointer_team != team:
                return pointer
        except:
            return None

    def is_valid_minion_pointer(self, pointer, minions, team):
        try:
            pointer_name = self.pm.read_string(self.pm.read_longlong(pointer + self.name))
            pointer_team = self.pm.read_int(pointer + self.team)
            if pointer_name in minions and pointer_team != team:
                return pointer
        except:
            return None

    def is_valid_jungle_pointer(self, pointer, entities):
        try:
            return self.pm.read_string(self.pm.read_longlong(pointer + self.name)).lower() in entities
        except:
            try:
                return self.pm.read_string(pointer + self.name).lower() in entities
            except:
                return False

    def get_pointers(self, champions, team):
        champion_manager = self.pm.read_ulonglong(self.base_address + self.champion_list)
        pointers = self.pm.read_bytes(self.pm.read_ulonglong(champion_manager + 0x8), 100)
        pointers = [int.from_bytes(pointers[i:i + 8], byteorder='little') for i in range(0, len(pointers), 8)]
        return {pointer for pointer in pointers if self.is_valid_pointer(pointer, champions, team)}

    def get_minion_pointers(self, minions, team):
        minion_manager = self.pm.read_ulonglong(self.base_address + self.minion_list)
        pointers = self.pm.read_bytes(self.pm.read_ulonglong(minion_manager + 0x8), 100)
        pointers = [int.from_bytes(pointers[i:i + 8], byteorder='little') for i in range(0, len(pointers), 8)]
        return [pointer for pointer in pointers if self.is_valid_minion_pointer(pointer, minions, team)]

    def get_jungle_pointers(self, entities):
        minion_manager = self.pm.read_ulonglong(self.base_address + self.minion_list)
        pointers = self.pm.read_bytes(self.pm.read_ulonglong(minion_manager + 0x8), 100)
        pointers = [int.from_bytes(pointers[i:i + 8], byteorder='little') for i in range(0, len(pointers), 8)]
        return [pointer for pointer in pointers if self.is_valid_jungle_pointer(pointer, entities)]
